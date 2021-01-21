"""
Automated clean slate screening.
"""
import logging
import tempfile
from typing import List, Dict, Tuple
import os
import re
import json
import shutil
import requests
from ujs_search.services.searchujs import search_by_name, search_by_docket
from RecordLib.sourcerecords.parsingutilities import get_text_from_pdf
from RecordLib.crecord import CRecord, Person
from RecordLib.sourcerecords import SourceRecord
from RecordLib.analysis import Analysis
from RecordLib.analysis import ruledefs as rd
from RecordLib.utilities.email_builder import EmailBuilder
from RecordLib.sourcerecords.docket.re_parse_cp_pdf import parse_cp_pdf_text
from RecordLib.sourcerecords.docket.re_parse_mdj_pdf import parse_mdj_pdf_text

from RecordLib.utilities.serializers import to_serializable

logger = logging.getLogger(__name__)


def communicate_results(
    sourcerecords: List[SourceRecord],
    analysis: Analysis,
    email_address,
    output_json_path: str,
    output_html_path: str,
) -> Tuple[Dict, str, Dict]:
    """
    Communicate the results of the record screening.


    Returns:
        Results - a dict describing the source records and analysis in detail
        html_message - html string summarizing results
        summary - dict summarizing analysis, which html_message uses.

    """
    sources = []
    for sr in to_serializable(sourcerecords):
        sr.pop("raw_source")
        sources.append(sr)
    results = {"sourcerecords": sources, "analysis": to_serializable(analysis)}
    message_builder = EmailBuilder(sources, analysis)
    if output_json_path is not None:
        with open(output_json_path, "w") as f:
            f.write(json.dumps(results, indent=4))
        logger.info(f"    Analysis written to {output_json_path}.")
    html_message = message_builder.html_summary()
    if output_html_path is not None:
        with open(output_html_path, "w") as f:
            f.write(html_message)
    if email_address is not None:
        message_builder.email(email_address)
    return results, html_message, message_builder.summary


def pick_pdf_parser(docket_num):
    if "CP" in docket_num or "MC" in docket_num:
        parser = parse_cp_pdf_text
    elif "MJ" in docket_num:
        parser = parse_mdj_pdf_text
    else:
        logger.error(f"   Cannot determine the right parser for: {docket_num}")
        parser = None
    return parser


def by_name(
    first_name,
    last_name,
    dob,
    email=None,
    output_dir=None,
    output_json=None,
    output_html=None,
):
    """
    Screen a person's public criminal record for charges that can be expunged or sealed.



    Returns:
        Results - a dict describing the source records and analysis in detail
        html_message - html string summarizing results
        summary - dict summarizing analysis, which html_message uses.


    """
    # Search UJS for the person's name to collect source records.
    if output_dir is not None and not os.path.exists(output_dir):
        raise (ValueError(f"Directory {output_dir} does not exist."))

    search_results, errs = search_by_name(first_name, last_name, dob)
    search_results = search_results["MDJ"] + search_results["CP"]
    logger.info(f"    Found {len(search_results)} cases in the Portal.")
    # Download the source records
    # and xtract text from the source records.
    with tempfile.TemporaryDirectory() as td:
        for case in search_results:
            for source_type in ["docket_sheet", "summary"]:
                try:
                    resp = requests.get(
                        case[f"{source_type}_url"],
                        headers={"User-Agent": "CleanSlateScreener"},
                    )
                except requests.exceptions.MissingSchema as e:
                    # the case search results is missing a url. this happens when
                    # a docket doesn't have a summary, and is fairly common.
                    case[f"{source_type}_text"] = ""
                    continue
                if resp.status_code != 200:
                    case[f"{source_type}_text"] = ""
                    continue
                filename = os.path.join(td, f"{case['docket_number']}_{source_type}")
                with open(filename, "wb") as fp:
                    fp.write(resp.content)
                case[f"{source_type}_text"] = get_text_from_pdf(filename)
        if output_dir is not None:
            for doc in os.listdir(td):
                shutil.copy(os.path.join(td, doc), os.path.join(output_dir, doc))

    logger.info("   Collected texts from cases.")
    # At this point, search_results looks like a list of search_result dicts,
    # where each dict also has a key containing the exported text of the docket and the summary.
    # [
    #       {
    #           "caption": "", "docket_number": "", "docket_sheet_text": "lots of \ntext",
    #           "summary_text": "lots of text" and other keys.
    #       }
    # ]

    # Next read through a Summary and find any docket numbers mentioned.
    # If any dockets are _not_ already found in the source_records,
    # collect them from ujs, download them, extract their text,
    docket_nums = set([case["docket_number"] for case in search_results])
    summary_docket_numbers = set()
    for case in search_results:
        summary_text = case["summary_text"]
        other_docket_nums_in_summary = set(
            re.findall(r"(?:MC|CP)\-\d{2}\-\D{2}\-\d*\-\d{4}", summary_text)
            + re.findall(r"MJ-\d{5}-\D{2}-\d+-\d{4}", summary_text)
        )
        summary_docket_numbers.update(other_docket_nums_in_summary)

    new_docket_numbers = summary_docket_numbers.difference(docket_nums)
    logger.info(
        f"    Searched summaries and found {len(new_docket_numbers)} cases not found through portal."
    )
    # Append the new-found docket numbers to the list of search results we need to collect and
    # add to the crecord we're building here.
    for dn in new_docket_numbers:
        cases = search_by_docket(dn)
        if len(cases) > 0:
            case = cases[0]
        else:
            logger.error(f"Did not find case for docket {dn}")
            continue
        search_results.append(case)
        with tempfile.TemporaryDirectory() as td:
            for source_type in ["docket_sheet"]:
                resp = requests.get(
                    case[f"{source_type}_url"],
                    headers={"User-Agent": "CleanSlateScreener"},
                )
                if resp.status_code != 200:
                    continue
                filename = os.path.join(td, case["docket_number"])
                with open(filename, "wb") as fp:
                    fp.write(resp.content)
                case[f"{source_type}_text"] = get_text_from_pdf(filename)
            if output_dir is not None:
                for doc in os.listdir(td):
                    shutil.copy(os.path.join(td, doc), os.path.join(output_dir, doc))

    # Read the source records and integrate them into a CRecord
    # representing the person't full criminal record.
    sourcerecords = list()
    crecord = CRecord(
        person=Person(first_name=first_name, last_name=last_name, date_of_birth=dob)
    )
    # building a crecord out of the docket sheets here.
    for case in search_results:
        parser = pick_pdf_parser(case["docket_number"])
        if parser is None:
            continue
        src = SourceRecord(case["docket_sheet_text"], parser)
        for parsed_case in src.cases:
            # Adding the docket sheet url back into the cases the sourcerecord parses out.
            # Here, this will will only be a single case.
            parsed_case.docket_url = case["docket_sheet_url"]
        sourcerecords.append(src)
        crecord.add_sourcerecord(src)

    logger.info("Built CRecord.")
    # Create and Analysis using the CRecord. This Analysis will explain
    # what charges and cases are expungeable, what will be automatically sealed,
    # what could be sealed by petition.

    analysis = (
        Analysis(crecord)
        .rule(rd.filter_traffic_cases)
        .rule(rd.expunge_deceased)
        .rule(rd.expunge_over_70)
        .rule(rd.expunge_nonconvictions)
        .rule(rd.expunge_summary_convictions)
        .rule(rd.seal_convictions)
    )

    # email the results.
    return communicate_results(sourcerecords, analysis, email, output_json, output_html)

