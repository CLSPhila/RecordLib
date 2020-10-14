from RecordLib.analysis.ruledefs import autosealing_rules as ar


def test_autosealing(example_crecord):
    result = ar.autosealing_eligibility(example_crecord)
    assert True  # lets just make sure we can get here at all.

