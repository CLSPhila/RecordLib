import pytest
import os
from cleanslate.models import SourceRecord
from RecordLib.crecord import CRecord
from cleanslate.serializers import SourceRecordSerializer
from cleanslate.serializers import CRecordSerializer
from django.core.files import File
from RecordLib.serializers import to_serializable

def test_anonymous_cannot_get_userprofileview(dclient):
    resp = dclient.get('/record/profile/', follow=True)
    assert resp.status_code == 403 

def test_loggedin_get_userprofileview(admin_client):
    resp = admin_client.get('/record/profile/', follow=True)
    assert resp.status_code == 200
    userdata = resp.data
    assert 'user' in userdata.keys()
    assert 'profile' in userdata.keys()

@pytest.mark.django_db
def test_integrate_sources_with_crecord(dclient, admin_user, example_crecord):
    dclient.force_authenticate(user=admin_user)
    docket = os.listdir("tests/data/dockets/")[0]
    with open(f"tests/data/dockets/{docket}", "rb") as d:
        doc_1 = SourceRecord.objects.create(
            caption = "Hello v. World",
            docket_num = "MC-1234",
            court = SourceRecord.Courts.CP,
            url = "https://abc.def",
            record_type = SourceRecord.RecTypes.DOCKET_PDF,
            file = File(d),
            owner = admin_user,
        )
    summary = os.listdir("tests/data/summaries")[0]
    with open(f"tests/data/summaries/{summary}", "rb") as s:
        doc_2 = SourceRecord.objects.create(
            caption = "Hello v. Goodbye",
            docket_num = "MC-1235",
            court = SourceRecord.Courts.MDJ,
            url = "https://def.ghi",
            record_type = SourceRecord.RecTypes.SUMMARY_PDF,
            file = File(s),
            owner = admin_user,
        )

    # when sent to api, serialized document data won't have a file included. 
    # The request is asking to do stuff using the file that is on the server.
    doc_1_data = SourceRecordSerializer(doc_1).data
    #doc_1_data.pop("file")

    doc_2_data = SourceRecordSerializer(doc_2).data
    #doc_2_data.pop("file") 
    data = {
        "crecord": CRecordSerializer(example_crecord).data, 
        "source_records": [doc_1_data, doc_2_data]
    }

    resp = dclient.put("/record/sources/", data = data)
    assert resp.status_code == 200
    assert "crecord" in resp.data
    try:
        CRecord.from_dict(resp.data["crecord"])
    except Exception as err:
        pytest.fail(err)


@pytest.mark.django_db
def test_download_ujs_docs(admin_client):
    """
    post a couple of documents with urls to the server. Server creates objects to store the downloaded files and then 
    returns uuids of the document objects in the database.
    """
    doc_1 = {
        "docket_num": "CP-12345",
        "court": "CP",
        "url": "https://ujsportal.pacourts.us/DocketSheets/CPReport.ashx?docketNumber=CP-25-CR-1234567-2010&dnh=12345",
        "caption": "Comm. v. SillyKitty",
        "record_type": SourceRecord.RecTypes.DOCKET_PDF,
    }
    doc_2 = {
        "docket_num": "CP-54321",
        "court": "CP",
        "url": "https://ujsportal.pacourts.us/DocketSheets/CourtSummaryReport.ashx?docketNumber=CP-25-CR-1234567-2010&dnh=12345",
        "caption": "Comm. v. SillyKitty",
        "record_type": SourceRecord.RecTypes.SUMMARY_PDF,
    }
    resp = admin_client.post(
        "/record/download/",
        data = {
            "source_records": [doc_1, doc_2]
        }, follow=True, content_type="application/json")
    assert resp.status_code == 200
    for rec in resp.data["source_records"]:
        try:
            rec['id']
        except:
            pytest.fail("rec in response didn't have an id")
 