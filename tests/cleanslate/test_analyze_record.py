from RecordLib.utilities.serializers import to_serializable
from RecordLib.petitions import Petition
import json


def test_analyze(admin_client, example_crecord):
    resp = admin_client.post(
        "/api/record/analysis/",
        data=to_serializable(example_crecord),
        content_type="application/json",
    )
    assert resp.status_code == 200
    analysis = resp.json()
    assert all(
        key in ["record", "remaining_record", "decisions"] for key in analysis.keys()
    )
    decisions = analysis["decisions"]
    petitions = [p for d in decisions for p in d["value"]]
    assert all("petition_type" in p.keys() for p in petitions)
