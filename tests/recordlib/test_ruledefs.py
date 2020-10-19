from RecordLib.analysis import ruledefs
from RecordLib.analysis.ruledefs.simple_sealing_rules import (
    not_felony1,
    fines_and_costs_paid,
    is_misdemeanor_or_ungraded,
    no_danger_to_person_offense,
    cannot_autoseal_m1_or_f,
)
from RecordLib.analysis.ruledefs.filter_rules import is_traffic_case
from RecordLib.crecord import Sentence, SentenceLength
from RecordLib.crecord import Case
from RecordLib.utilities.serializers import to_serializable
from RecordLib.petitions import Expungement
from datetime import date
import pytest
import types
import copy


def test_rule_expunge_over_70(example_crecord):
    example_crecord.person.date_of_birth = date(1920, 1, 1)
    example_crecord.cases[0].arrest_date = date(1970, 1, 1)
    example_crecord.cases[0].charges[0].sentences = [
        Sentence(
            sentence_date=date.today(),
            sentence_type="Confinement",
            sentence_period="90 days",
            sentence_length=SentenceLength.from_tuples(("90", "day"), ("90", "day")),
        )
    ]
    remaining_recordord, analysis = ruledefs.expunge_over_70(example_crecord)
    assert analysis.value == []
    assert [bool(d) for d in analysis.reasoning] == [True, True, False]
    assert len(remaining_recordord.cases) == len(example_crecord.cases)

    example_crecord.cases[0].charges[0].sentences[0] = Sentence(
        sentence_date=date(1980, 1, 1),
        sentence_type="Confinement",
        sentence_period="90 days",
        sentence_length=SentenceLength.from_tuples(("90", "day"), ("90", "day")),
    )
    remaining_recordord, analysis = ruledefs.expunge_over_70(example_crecord)
    assert isinstance(analysis.value[0], Expungement)
    # The modified record has removed the cases this rule wants to expunge.
    assert len(remaining_recordord.cases) < len(example_crecord.cases)


def test_expunge_deceased(example_crecord):
    example_crecord.person.date_of_death = None
    mod_rec, analysis = ruledefs.expunge_deceased(example_crecord)
    assert analysis.value == []

    example_crecord.person.date_of_death = date(2000, 1, 1)
    mod_rec, analysis = ruledefs.expunge_deceased(example_crecord)
    assert len(analysis.value) == len(example_crecord.cases)


def test_expunge_summary_convictions(example_crecord, example_charge):
    # Old summary convictions are expungeable
    example_crecord.cases[0].charges[0].grade = "S"
    example_crecord.cases[0].arrest_date = date(2000, 1, 1)
    example_crecord.cases[0].disposition_date = date(2001, 1, 1)
    mod_rec, analysis = ruledefs.expunge_summary_convictions(example_crecord)
    assert len(analysis.value) == len(example_crecord.cases)

    # no expunged summary convictions if there was a recent arrest.
    example_crecord.cases[0].arrest_date = date(2019, 1, 1)
    mod_rec, analysis = ruledefs.expunge_summary_convictions(example_crecord)
    assert len(analysis.value) == 0

    # Only summary convictions, not other grades, can be expunged.
    new_charge = copy.deepcopy(example_charge)
    new_charge.grade = "M2"
    example_crecord.cases[0].arrest_date = date(2000, 1, 1)
    example_crecord.cases[0].charges.append(new_charge)
    assert len(example_crecord.cases[0].charges) == 2

    mod_rec, analysis = ruledefs.expunge_summary_convictions(example_crecord)
    assert len(analysis.value) == 1
    assert len(mod_rec.cases) == 1


@pytest.mark.parametrize(
    "disp", [(""), ("Nolle Prossed"), ("Withdrawn"), ("Not Guilty")]
)
def test_expunge_nonconvictions(example_crecord, example_charge, disp):
    example_crecord.cases[0].charges[0].disposition = disp
    mod_rec, analysis = ruledefs.expunge_nonconvictions(example_crecord)
    if disp != "":
        assert len(analysis.value) == len(example_crecord.cases)
        assert len(mod_rec.cases) == 0
    else:
        # Disposition that's blank is assumed not expungeable (because still active, perhaps)
        assert analysis.value == []


@pytest.mark.parametrize(
    "statute,grade,value", [("18 § 2709", "S", True), ("18 § 2709", "", False)]
)  # TRUE means a statute should _not_ be considered an arb b offense
# FALSE means the statue IS an art. b offense, so excluded from sealing.
def test_art_b_danger_to_person_offenses(example_charge, statute, grade, value):
    """
    Check the decisionmaking about whether a statute is an article B offense-to-person offense.
    
    Notes. 
      Only Art. B offenses with possible terms of imprisonment longer than two years.
      18 s. 9122.1(b) 
    """
    example_charge.statute = statute
    example_charge.grade = grade
    res = no_danger_to_person_offense(example_charge, 10, 20, 1)
    assert res.value == value


@pytest.mark.parametrize(
    "grade,value,less_or_more",
    [
        ("F", False, "more"),
        ("M1", False, "more",),
        ("M2", True, "less"),
        ("M3", True, "less"),
        ("M", True, "less"),
        ("S", True, "less"),
        (None, False, "missing"),
    ],
)
def test_cannot_autoseal_m1_or_f(example_charge, grade, value, less_or_more):
    example_charge.grade = grade
    example_charge.disposition = "Guilty"
    result = cannot_autoseal_m1_or_f(example_charge)
    assert result.value == value
    assert less_or_more in result.reasoning


def test_traffic_filter(example_case):
    example_case.docket_number = "CP-1234"
    dec = is_traffic_case(example_case)
    assert bool(dec) == False

    example_case.docket_number = "MD-TR-1234"
    dec = is_traffic_case(example_case)
    assert bool(dec) == True
