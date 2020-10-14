from RecordLib.analysis.ruledefs import autosealing_rules as ar
from RecordLib.utilities.serializers import to_serializable


def test_autosealing(example_crecord):
    result = ar.autosealing_eligibility(example_crecord)
    breakpoint()
    assert True  # lets just make sure we can get here at all.

