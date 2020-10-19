import os
import logging
import pytest
from RecordLib.sourcerecords import Docket, SourceRecord
from RecordLib.crecord import Person
from RecordLib.crecord import Case
from RecordLib.sourcerecords.docket.re_parse_mdj_pdf import parse_mdj_pdf
from RecordLib.sourcerecords.docket.re_parse_cp_pdf import (
    parse_cp_pdf as re_parse_cp_pdf,
)


def test_pdf_factory_one():
    """
    We can create a Docket using a factory method, 'from_pdf'.
    """
    try:
        filename = os.listdir("tests/data/dockets")[0]
        dkt, _ = Docket.from_pdf(os.path.join("tests/data/dockets", filename))
    except Exception:
        pytest.fail("Cannot create Docket object")
    assert isinstance(dkt._case, Case)
    assert isinstance(dkt._defendant, Person)
    assert dkt._case.affiant is not None
    assert dkt._defendant.first_name is not None
    assert dkt._case.arresting_agency is not None


@pytest.mark.skip("There are parsing errors that are too complex for the moment")
def test_pdf_factory_bulk(caplog):
    """
    Test parsing a whole directory of dockets.

    N.B. This doesn't currently report a failure if a _section_ of a docket failed to parse. 

    Run w/ `pytest tests/test_docket.py -k bulk -v -o log_cli=true` to show logging, even when test
    doesn't fail. Useful because sections can fail w/out causing the test to fail.
    """
    caplog.set_level(logging.INFO)
    files = os.listdir("tests/data/dockets")
    total_dockets = len(files)
    successes = 0
    error_list = []
    for dkt in files:
        try:
            logging.info("Parsing %s", dkt)
            _, errs = Docket.from_pdf(os.path.join("tests/data/dockets", dkt))
            if len(errs) > 0:
                error_list = error_list + [(dkt, errs)]
            successes += 1
            logging.info("    %s parsed.", dkt)
        except Exception:
            logging.error("    %s failed to parse.", dkt)

    if len(error_list) > 0:
        logging.error(
            "%s of %s cases had non-fatal parsing errors.", len(error_list), len(files)
        )
        pytest.fail(
            "%s of %s cases had non-fatal parsing errors."
            % (len(error_list), len(files))
        )
    if successes < total_dockets:
        logging.error("Only %d/%d parsed.", successes, total_dockets)
        pytest.fail("Only %d/%d parsed.", successes, total_dockets)


def test_mdj_docket_pdf_parser():
    """
    A parser can parse MDJ Pdf files.
    """

    path = os.path.join("tests", "data", "dockets")
    files = os.listdir(path)
    mdj_dockets = list(filter(lambda f: "MJ" in f, files))
    if len(mdj_dockets) == 0:
        pytest.fail(
            "You need an MDJ docket named like MJ-........pdf for this test to pass."
        )
    for f in mdj_dockets:
        try:
            sr = SourceRecord(os.path.join(path, f), parser=parse_mdj_pdf)
        except Exception as e:
            pytest.fail(str(e))
        assert len(sr.cases) == 1


@pytest.mark.skip("There are parsing errors that are too complex for the moment")
def test_regex_cp_parser(caplog):
    """
    Test parsing a whole directory of dockets with the regex-based cp parser.


    Run w/ `pytest tests/test_docket.py -k bulk -v -o log_cli=true` to show logging, even when test
    doesn't fail.
    """
    caplog.set_level(logging.INFO)
    # don't try to parse MDJ dockets here.
    files = [f for f in os.listdir("tests/data/dockets") if "CP" in f]
    total_dockets = len(files)
    successes = 0
    error_list = []
    for dkt in files:
        try:
            logging.info("Parsing %s", dkt)
            _, __, errs = re_parse_cp_pdf(os.path.join("tests/data/dockets", dkt))
            logging.info(f"    {dkt} parsed with {len(errs)} errors reported..")
            if len(errs) > 0:
                error_list = error_list + [(dkt, errs)]
                logging.info(f"    First error: {errs[0]}.")
            successes += 1
        except Exception as err:
            pytest.fail(f"     {dkt} failed to parse. Stopping test.")
            logging.error(f"    {dkt} failed to parse.")
            logging.error(err)

    if len(error_list) > 0:
        logging.error(
            f"{len(error_list)} of {len(files)} cases had non-fatal parsing errors."
        )
        pytest.fail(
            f"{len(error_list)} of {len(files)} cases had non-fatal parsing errors."
        )
    if successes < total_dockets:
        logging.error(f"Only {successes}/{total_dockets} parsed.")
        pytest.fail(f"Only {successes}/{total_dockets} parsed.")


def test_mdj_docket_parse_sequence_numbers():
    path = os.path.join("tests", "data", "dockets")
    files = os.listdir(path)
    mdj_dockets = list(filter(lambda f: "MJ" in f, files))
    if len(mdj_dockets) == 0:
        pytest.fail(
            "You need MDJ dockets named like MJ-........pdf for this test to be able to execute."
        )
    for f in mdj_dockets:
        try:
            sr = SourceRecord(os.path.join(path, f), parser=parse_mdj_pdf)
            for case in sr.cases:
                for charge in case.charges:
                    assert charge.sequence is not None
        except Exception as e:
            pytest.fail(str(e))


def test_cp_docket_parse_sequence_numbers():
    path = os.path.join("tests", "data", "dockets")
    files = os.listdir(path)
    mdj_dockets = list(filter(lambda f: "CP" in f, files))
    if len(mdj_dockets) == 0:
        pytest.fail(
            "You need CP dockets named like CP-........pdf for this test to be able to execute."
        )
    for f in mdj_dockets:
        try:
            sr = SourceRecord(os.path.join(path, f), parser=re_parse_cp_pdf)
            for case in sr.cases:
                for charge in case.charges:
                    assert charge.sequence is not None
        except Exception as e:
            pytest.fail(str(e))

