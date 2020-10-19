from RecordLib.crecord.common import *
from dataclasses import asdict
from datetime import date, timedelta
import pytest
from RecordLib.utilities.serializers import to_serializable


def test_sentence():
    st = Sentence(
        sentence_date=date(2010, 1, 1),
        sentence_type="Probation",
        sentence_period="90 days",
        sentence_length=SentenceLength.from_tuples(
            min_time=("90", "Day"), max_time=("90", "Day")
        ),
    )
    assert st.sentence_complete_date() == date(2010, 1, 1) + timedelta(days=90)


def test_calculate_days():
    assert SentenceLength.calculate_days("40", "Day(s)").days == 40
    assert SentenceLength.calculate_days("3 ", "Month(s)").days == 91
    assert SentenceLength.calculate_days(" 1", "Year(s)").days == 365
    assert SentenceLength.calculate_days(" Other", "Values") is None


def test_SentenceLength():
    lng = SentenceLength.from_tuples(
        min_time=("30", " Day(s)"), max_time=("1", "Year(s)")
    )
    assert lng.max_time.days == 365
    assert lng.min_time.days == 30


def test_charge():
    char = Charge(
        sequence=1,
        offense="Eating w/ mouth open",
        grade="M2",
        statute="24 &sect; 102",
        disposition="Guilty Plea",
        disposition_date=date(2010, 1, 1),
        sentences=[],
    )
    assert char.offense == "Eating w/ mouth open"
    assert char.grade == "M2"
    assert char.disposition == "Guilty Plea"


def test_charge_merge_reduce():
    charges = [
        Charge(
            sequence="1",
            offense="Eating w/ mouth open",
            grade="M2",
            statute="24 &sect; 102",
            disposition="Held for Court (Lower Court)",
            disposition_date=None,
            sentences=[],
        ),
        Charge(
            sequence="1",
            offense="Eating w/ mouth open",
            grade=None,
            statute="24 &sect; 102",
            disposition="Guilty Plea",
            disposition_date=date(2010, 1, 1),
            sentences=[],
        ),
        Charge(
            sequence="2",
            offense="Shoveling snow too exuberantly",
            grade="F1",
            statute="24 &sect; 202",
            disposition="Guilty Plea",
            disposition_date=date(2010, 1, 1),
            sentences=[],
        ),
    ]
    reduced_charges = Charge.reduce_merge(charges)
    assert len(reduced_charges) == 2


@pytest.mark.parametrize(
    "disposition, is_a_conviction",
    (
        ("Guilty", True),
        ("Not Guilty", False),
        ("Nolle Prossed", False),
        ("Withdrawn", False),
        ("", False),
    ),
)
def test_charge_is_conviction(example_charge, disposition, is_a_conviction):
    example_charge.disposition = disposition
    assert example_charge.is_conviction() == is_a_conviction


def test_charge_get_section(example_charge):
    example_charge.statute = "18 § 1234"
    assert example_charge.get_statute_section() == 1234
    example_charge.statute = "18 § 4815.1"
    assert example_charge.get_statute_section() == 4815.1


def test_charge_get_chapter(example_charge):
    example_charge.statute = "18 § 1234"
    assert example_charge.get_statute_chapter() == 18


def test_charge_get_statute_subsections(example_charge):
    example_charge.statute = "75 § 3802 §§ A1*"
    assert example_charge.get_statute_subsections() == "A1*"


def test_charge_gte(example_charge):
    example_charge.grade = "M1"
    assert Charge.grade_GTE(example_charge.grade, "M3") == True
    assert Charge.grade_GTE(example_charge.grade, "") == True
    assert Charge.grade_GTE(example_charge.grade, "F2") == False
    example_charge.grade = "F2"
    assert Charge.grade_GTE(example_charge.grade, "M3") == True
