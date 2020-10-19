import pytest
from RecordLib.analysis.ruledefs.petition_rules import *
from RecordLib.analysis.ruledefs.simple_sealing_rules import *
from RecordLib.crecord import CRecord, Charge
import json
from RecordLib.utilities.serializers import to_serializable
from datetime import date
from RecordLib.petitions import Sealing, Petition


def test_seal(example_crecord):
    example_crecord.cases[0].total_fines = 0
    example_crecord.cases[0].disposition_date = date(1990, 1, 1)
    example_crecord.cases[0].charges[0] = Charge(
        offense="Being silly",
        grade="M1",
        disposition="Guilty",
        statute="14 s 123",
        sentences=[],
    )
    mod_rec, analysis = seal_convictions(example_crecord)
    assert len(analysis.value) == 1
    assert isinstance(analysis.value[0], Sealing)
    assert len(mod_rec.cases) == 0


def test_partial_seal(example_crecord):
    example_crecord.cases[0].total_fines = 0
    example_crecord.cases[0].disposition_date = date(1990, 1, 1)
    example_crecord.cases[0].charges[0] = Charge(
        offense="Being silly",
        grade="M1",
        disposition="Guilty",
        disposition_date=date(2010, 1, 1),
        statute="14 s 123",
        sentences=[],
    )
    new_charge = Charge(
        offense="Overzealous puzzle-assembling, using a firearm",
        grade="S",
        disposition="Guilty",
        statute="18 § 6101",
        sentences=[],
    )
    example_crecord.cases[0].charges.append(new_charge)
    mod_rec, analysis = seal_convictions(example_crecord)
    assert "puzzle-assembling" in mod_rec.cases[0].charges[0].offense
    petition = analysis.value[0]
    assert isinstance(petition, Petition)

    assert "silly" in petition.cases[0].charges[0].offense


def test_no_danger_to_person_offense(example_crecord):
    example_crecord.cases[0].charges[0] = Charge(
        offense="Being silly",
        grade="M1",
        disposition="Guilty",
        statute="18 § 123",
        sentences=[],
    )
    decision = no_danger_to_person_offense(
        example_crecord, penalty_limit=7, conviction_limit=1, within_years=20
    )
    assert bool(decision.value) == True

    charge = Charge(
        offense="Being silly",
        grade="M1",
        disposition="Guilty",
        statute="18 § 2301",
        sentences=[],
    )

    decision = no_danger_to_person_offense(
        charge, penalty_limit=2, conviction_limit=1, within_years=20
    )
    assert bool(decision.value) == False


def test_not_felony1(example_charge):
    example_charge.grade = "F1"
    example_charge.disposition = "Guilty"
    decision = not_felony1(example_charge)
    assert decision.value is False

    example_charge.disposition = "Not Guilty"
    decision = not_felony1(example_charge)
    assert decision.value is True
    assert decision.reasoning == "The charge was F1, but the disposition was Not Guilty"

    example_charge.grade = "M2"
    decision = not_felony1(example_charge)
    assert decision.value is True

    example_charge.grade = ""
    decision = not_felony1(example_charge)
    assert decision.value == False
    assert (
        decision.reasoning
        == "The charge's grade is unknown, so we don't know its *not* an F1."
    )


def test_ten_years_since_last_conviction(example_crecord):
    example_crecord.cases[0].disposition_date = date(1990, 1, 1)
    example_crecord.cases[0].charges[0].disposition = "Guilty"
    d = ten_years_since_last_conviction_for_m_or_f(example_crecord)
    assert d.value == True

    example_crecord.cases[0].disposition_date = date.today()
    d = ten_years_since_last_conviction_for_m_or_f(example_crecord)
    assert d.value == False


def test_offenses_punishable_by_two_or_more_years(example_crecord):
    example_crecord.cases[0].disposition_date = date.today()
    c1 = Charge(
        offense="Being silly",
        grade="M1",
        disposition="Guilty",
        statute="18 § 2301",
        sentences=[],
    )
    c2 = Charge(
        offense="Being sleepy",
        grade="F2",
        disposition="Guilty",
        statute="18 § 0987",
        sentences=[],
    )
    c3 = Charge(
        offense="Being hungry",
        grade="M2",
        disposition="Guilty",
        statute="18 § 1111",
        sentences=[],
    )
    c4 = Charge(
        offense="Being funny",
        grade="M2",
        disposition="Guilty",
        statute="18 § 1111",
        sentences=[],
    )
    example_crecord.cases[0].charges = [c1, c2, c3, c4]
    assert (
        bool(
            offenses_punishable_by_two_or_more_years(
                example_crecord, conviction_limit=4, within_years=20
            )
        )
        == False
    )
    example_crecord.cases[0].disposition_date = date(1950, 1, 1)
    assert (
        bool(
            offenses_punishable_by_two_or_more_years(
                example_crecord, conviction_limit=4, within_years=20
            )
        )
        == True
    )


def test_no_offense_against_family(example_crecord):
    charge = Charge(
        offense="Being silly",
        grade="M1",
        disposition="Guilty",
        statute="18 § 4301",
        sentences=[],
    )
    example_crecord.cases[0].charges[0] = charge
    d = no_offense_against_family(
        example_crecord, penalty_limit=1, conviction_limit=1, within_years=50
    )
    assert bool(d) is False
    d = no_offense_against_family(
        example_crecord, penalty_limit=1, conviction_limit=3, within_years=50
    )
    assert bool(d) is True
    example_crecord.cases[0].charges = [charge, charge, charge, charge]
    d = no_offense_against_family(
        example_crecord, penalty_limit=1, conviction_limit=2, within_years=50
    )
    assert bool(d) is False


def test_no_paramilitary_training(example_crecord):
    example_crecord.cases[0].charges = [
        Charge(
            offense="Being silly",
            grade="M1",
            disposition="Guilty",
            statute="18 § 5515",
            sentences=[],
        )
    ]
    d = no_paramilitary_training(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is False
    example_crecord.cases[0].disposition_date = date(1950, 1, 1)
    d = no_paramilitary_training(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is True

    example_crecord.cases[0].disposition_date = date.today()
    example_crecord.cases[0].charges.append(
        Charge(
            offense="eating ice cream",
            grade="M1",
            disposition="Guilty Plea",
            statute="18 § 1",
            sentences=[],
        )
    )
    d = no_paramilitary_training(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is False


def test_no_abuse_of_corpse(example_crecord):
    example_crecord.cases[0].charges[0].statute = "18 § 5510"
    example_crecord.cases[0].disposition_date = date(2019, 1, 1)
    d = no_abuse_of_corpse(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is False
    example_crecord.cases[0].charges[0].statute = "18 § 5550"
    d = no_abuse_of_corpse(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is True


def test_no_weapons_of_escape(example_crecord):
    example_crecord.cases[0].charges[0].statute = "18 § 5122"
    example_crecord.cases[0].disposition_date = date(2019, 1, 1)
    d = no_weapons_of_escape(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is False

    example_crecord.cases[0].charges[0].statute = "18 § 122"
    d = no_weapons_of_escape(example_crecord, 1, 15)
    assert bool(d) is True


def test_no_failure_to_register(example_crecord):
    example_crecord.cases[0].charges[0].statute = "18 § 4915.1"
    example_crecord.cases[0].disposition_date = date(2019, 1, 1)
    d = no_failure_to_register(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is False

    example_crecord.cases[0].charges[0].statute = "18 § 122"
    d = no_failure_to_register(example_crecord, 1, 15)
    assert bool(d) is True


def test_no_intercourse_w_animal(example_crecord):
    example_crecord.cases[0].charges[0].statute = "18 § 3129"
    example_crecord.cases[0].disposition_date = date(2019, 1, 1)
    d = no_sexual_intercourse_w_animal(
        example_crecord, conviction_limit=1, within_years=15
    )
    assert bool(d) is False

    example_crecord.cases[0].charges[0].statute = "18 § 122"
    d = no_sexual_intercourse_w_animal(example_crecord, 1, 15)
    assert bool(d) is True


def test_no_indecent_exposure(example_crecord):
    example_crecord.cases[0].charges[0].statute = "18 § 3127"
    example_crecord.cases[0].charges[0].disposition_date = date(2019, 1, 1)
    d = no_indecent_exposure(example_crecord, conviction_limit=1, within_years=15)
    assert bool(d) is False

    example_crecord.cases[0].charges[0].statute = "18 § 122"
    d = no_indecent_exposure(example_crecord, 1, 15)
    assert bool(d) is True


def test_no_corruption_of_minors_offense(example_charge):
    example_charge.statute = "18 § 1201.1"
    d = no_corruption_of_minors_offense(
        example_charge, penalty_limit=20, conviction_limit=1, within_years=20
    )
    assert bool(d) is True


def test_no_sexual_offense(example_crecord, example_charge):
    example_crecord.cases[0].charges[0].statute = "18 § 2901(a.1)"
    example_crecord.cases[0].charges[0].disposition_date = date(2019, 1, 1)
    d = no_sexual_offense(
        example_crecord, penalty_limit=20, conviction_limit=1, within_years=20
    )
    assert bool(d) is False

    example_charge.statute = "18 § 1201.1"
    d = no_sexual_offense(
        example_charge, penalty_limit=20, conviction_limit=1, within_years=20
    )
    assert bool(d) is True


def test_no_firearms_offense(example_crecord, example_charge):
    example_crecord.cases[0].charges[0].statute = "18 § 6101"
    example_crecord.cases[0].charges[0].disposition_date = date(2019, 1, 1)
    d = no_firearms_offense(
        example_crecord, penalty_limit=20, conviction_limit=1, within_years=20
    )
    assert bool(d) is False

    example_charge.statute = "18 § 1201.1"
    d = no_firearms_offense(
        example_charge, penalty_limit=20, conviction_limit=1, within_years=20
    )
    assert bool(d) is True


def test_fines_and_costs_paid(example_case):
    example_case.total_fines = 100
    example_case.fines_paid = 0
    assert bool(fines_and_costs_paid(example_case)) is False
    example_case.total_fines = 0
    assert bool(fines_and_costs_paid(example_case)) is True
    example_case.total_fines = 100
    example_case.fines_paid = 100
    assert bool(fines_and_costs_paid(example_case)) is True


def test_is_misdemeanor_or_ungraded(example_charge):
    example_charge.grade = "M2"
    assert bool(is_misdemeanor_or_ungraded(example_charge)) is True
    example_charge.grade = ""
    assert bool(is_misdemeanor_or_ungraded(example_charge)) is True
    example_charge.grade = "F2"
    assert bool(is_misdemeanor_or_ungraded(example_charge)) is False


def test_is_felony_conviction(example_charge):
    example_charge.grade = "M2"
    example_charge.disposition = "Guilty"
    assert bool(is_felony_conviction(example_charge)) is False
    example_charge.grade = ""
    assert bool(is_felony_conviction(example_charge)) is False
    example_charge.grade = "F2"
    assert bool(is_felony_conviction(example_charge)) is True


@pytest.mark.skip("Not unit-tested. Shame on me.")
def test_more_than_x_convictions_y_grade_y_years(example_crecord):
    pass
