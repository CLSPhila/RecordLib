import copy
from datetime import date
from dateutil.relativedelta import relativedelta
import pytest
from RecordLib.crecord import CRecord, Person, Case, Charge
from RecordLib.sourcerecords import SourceRecord
from RecordLib.utilities.serializers import to_serializable


def test_init():
    dob = date(2010, 1, 1)
    person = Person(**{"first_name": "Joe", "last_name": "Smith", "date_of_birth": dob})
    rec = CRecord(**{"person": person})
    assert rec.person.first_name == "Joe"
    rec = CRecord(
        person=Person(first_name="Joan", last_name="Smythe", date_of_birth=dob)
    )
    assert rec.person.last_name == "Smythe"


def test_add_summary(example_summary):
    rec = CRecord()
    rec.add_summary(example_summary)
    assert rec.person.first_name == example_summary.get_defendant().first_name
    assert (len(rec.cases) == len(example_summary.get_cases())) and (len(rec.cases) > 0)


def test_add_summary_doesnt_add_duplicates(example_summary):
    summary2 = copy.deepcopy(example_summary)
    rec = CRecord(Person("Dummy", "Name", None))
    rec.add_summary(example_summary)
    rec.add_summary(summary2)
    assert len(rec.cases) == len(example_summary.get_cases())


def test_add_summary_merge_strategies(example_summary):
    summary2 = copy.deepcopy(example_summary)
    summary2.get_cases()[0].otn = "a_different_otn"
    # default merge_strategy is to ignore new duplicates or
    # new Person
    rec = CRecord(Person("Dummy", "Name", None))
    rec.add_summary(example_summary)
    rec.add_summary(summary2)
    assert rec.cases[0].otn == example_summary.get_cases()[0].otn
    assert rec.person.first_name == "Dummy"

    # alternate merge strategy overwrites duplicates w/ new case
    # but doesn't touch the Person
    rec = CRecord(Person("Dummy", "Name", None))
    rec.add_summary(example_summary)
    rec.add_summary(summary2, case_merge_strategy="overwrite_old")
    assert rec.cases[0].otn == summary2.get_cases()[0].otn
    assert rec.person.first_name == "Dummy"

    # override_person param provides for overwriting the Person with the new summary's
    # Person
    rec = CRecord(Person("Dummy", "Name", None))
    rec.add_summary(example_summary)
    rec.add_summary(summary2, override_person=True)
    assert rec.cases[0].otn != summary2.get_cases()[0].otn
    assert rec.person.first_name == summary2.get_defendant().first_name


def test_add_sourcerecord(example_sourcerecord):
    rec = CRecord(Person("dummy", "name", None))
    rec.add_sourcerecord(example_sourcerecord, override_person=True)
    assert len(rec.cases) == len(example_sourcerecord.cases)
    assert rec.person.first_name != "dummy"


def test_add_empty_sourcerecord():
    rec = CRecord(Person("dummy", "name", None))
    sr = SourceRecord("anysource", parser=None)
    rec.add_sourcerecord(sr, override_person=True)
    assert len(rec.cases) == 0
    assert rec.person.first_name == "dummy"


def test_add_docket(example_docket):
    rec = CRecord(Person("dummy", "name", None))
    rec.add_docket(example_docket)
    assert len(rec.cases) == 1
    assert rec.person.first_name != "dummy"


def test_years_since_last_arrested_or_prosecuted(example_crecord):
    example_crecord.cases[0].arrest_date = date(2010, 1, 1)
    example_crecord.cases[0].disposition_date = date(2010, 1, 1)
    assert example_crecord.years_since_last_arrested_or_prosecuted() > 5


def test_years_since_final_release(example_crecord):
    example_crecord.years_since_final_release()


def test_init_empty():
    try:
        rec = CRecord()
    except:
        pytest.fail("Should be able to create an empty CRecord.")


def test_invalid_schema():
    with pytest.raises(TypeError):
        CRecord(**{"persons": {"first_name": "Blank"}})


def test_from_dict(example_crecord):
    serialized = to_serializable(example_crecord)
    crec2 = CRecord.from_dict(serialized)
    assert example_crecord.person.last_name == crec2.person.last_name


def test_add_case_held_for_court(example_person):
    record = CRecord(example_person, cases=[])
    subordinated_case = Case(
        status="Closed",
        county="Philadelphia",
        docket_number="CP-1234",
        otn="12345",
        dc="54321",
        charges=[],
    )
    held_for_court = Charge(
        "Silliness", "M1", statute="example", disposition="Held for Court"
    )
    subordinated_case.charges.append(held_for_court)

    main_case = Case(
        status="Closed",
        county="Philadelphia",
        docket_number="CP-5678",
        otn="12345",
        dc="xxxx",
        charges=[],
    )
    final_status = Charge("Silliness", "M1", statute="example", disposition="Guilty")

    record.add_case(subordinated_case)
    assert len(record.cases) == 1
    record.add_case(main_case)

    assert len(record.cases) == 1

    assert record.cases[0].disposition == "Guilty"
