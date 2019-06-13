from RecordLib.crecord import CRecord
from RecordLib.parse_pdf import parse_pdf
import pytest


def test_init():
    rec = CRecord({
        "person": {
            "first_name": "Joe",
            "last_name": "Smith"
        }
    })
    #pytest.set_trace()
    assert rec.person.first_name == "Joe"


def test_init_empty():
    try:
        rec = CRecord()
    except:
        pytest.fail("Should not have failed.")


def test_invalid_schema():
    with pytest.raises(AssertionError):
        CRecord({
            "persons": {
                "first_name": "Blank"
            }
        })


def test_create_from_pdf():
    with open("tests/data/CourtSummaryReport.pdf", "rb") as f:
        record = parse_pdf(f)
    assert record.person.first_name is not None
