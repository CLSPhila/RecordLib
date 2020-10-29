import pytest
from RecordLib.crecord import Case
from RecordLib.crecord import Person
from RecordLib.crecord import Charge, Sentence, SentenceLength, Address
from RecordLib.crecord import CRecord
from RecordLib.crecord import Attorney
from RecordLib.petitions import Expungement
from RecordLib.sourcerecords import Docket, Summary, SourceRecord
from RecordLib.sourcerecords.summary.parse_pdf import parse_pdf as summary_parser
from datetime import date
from RecordLib.utilities.redis_helper import RedisHelper
import os

# from django.test import Client
from rest_framework.test import APIClient


@pytest.fixture
def example_address():
    return Address(line_one="1234 Main St.", city_state_zip="Philadelphia, PA 19103")


@pytest.fixture
def example_attorney_address():
    return Address(line_one="1234 Main St.", city_state_zip="Big City, NY 10002")


@pytest.fixture
def example_attorney(example_attorney_address):
    return Attorney(
        organization="Community Legal",
        full_name="John Smith",
        address=example_attorney_address,
        organization_phone="555-555-5555",
        bar_id="123456",
    )


@pytest.fixture
def example_summary():
    summary, _ = Summary.from_pdf(pdf="tests/data/CourtSummaryReport.pdf")
    return summary


@pytest.fixture
def example_sourcerecord():
    return SourceRecord("tests/data/CourtSummaryReport.pdf", parser=summary_parser)


@pytest.fixture
def example_docket():
    docket_path = os.listdir("tests/data/dockets")[0]
    d, errs = Docket.from_pdf(os.path.join("tests", "data", "dockets", docket_path))
    return d


@pytest.fixture
def example_person(example_address):
    return Person(
        first_name="Jane",
        last_name="Smorp",
        aliases=["JSmo", "SmorpyJJ"],
        address=example_address,
        date_of_birth=date(2010, 1, 1),
        ssn="999-99-9999",
    )


@pytest.fixture
def example_sentencelength():
    return SentenceLength.from_tuples(min_time=("10", "Year"), max_time=("25", "Year"))


@pytest.fixture
def example_sentence(example_sentencelength):
    return Sentence(
        sentence_date=date(2000, 1, 1),
        sentence_type="Confinement",
        sentence_period="180 days",
        sentence_length=example_sentencelength,
    )


@pytest.fixture
def example_charge(example_sentence):
    return Charge(
        offense="Eating w/ mouth open",
        grade="M2",
        statute="14 section 23",
        disposition="Guilty Plea",
        sequence="1",
        disposition_date=date(2010, 1, 1),
        sentences=[example_sentence],
    )


@pytest.fixture
def example_case(example_charge):
    return Case(
        status="Open",
        county="Erie",
        docket_number="12-MC-01",
        otn="112000111",
        dc="11222",
        charges=[example_charge],
        total_fines=200,
        fines_paid=100,
        arrest_date=None,
        complaint_date=None,
        disposition_date=None,
        judge="Judge Jimmy Hendrix",
        judge_address="1234 Judge St.,",
        affiant="Officer Bland",
        arresting_agency_address="1234 Grey St.",
        arresting_agency="Monochrome County PD.",
    )


@pytest.fixture
def example_crecord(example_person, example_case):
    return CRecord(person=example_person, cases=[example_case])


@pytest.fixture
def example_expungement(example_crecord, example_attorney):
    return Expungement(
        expungement_type=Expungement.ExpungementTypes.FULL_EXPUNGEMENT,
        attorney=example_attorney,
        cases=example_crecord.cases,
        client=example_crecord.person,
        ifp_message="IFP Message",
        service_agencies=["Police Academy I"],
        include_crim_hist_report=True,
    )


@pytest.fixture
def redis_helper():
    """ A redis client.

    N.B. I don't know a way for this fixture to yield r and the rollback whatever a test does with the database. So tests using this fixture need to roll themselves back.
    """
    redis_helper = RedisHelper(
        host="localhost", port=6379, db=0, decode_responses=True, env="test"
    )
    yield redis_helper
    for key in redis_helper.r.scan_iter("test:*"):
        redis_helper.r.delete(key)


@pytest.fixture
def dclient():
    """ Django test client """
    return APIClient()
