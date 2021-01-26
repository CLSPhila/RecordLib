"""
Regex parsing functions for Common Pleas pdf dockets.
"""

import logging
import re
from typing import Union, BinaryIO, Tuple, List, Optional, Dict
from RecordLib.crecord import Charge, Person, Case, Address
from RecordLib.sourcerecords.parsingutilities import (
    get_text_from_pdf,
    date_or_none,
    money_or_none,
    word_starting_near,
    map_line,
    find_pattern,
    find_index_for_pattern,
)

logger = logging.getLogger(__name__)

section_headers = [
    "CASE INFORMATION",
    "RELATED CASES",
    "STATUS INFORMATION",
    "CONFINEMENT INFORMATION",
    "DEFENDANT INFORMATION",
    "CASE PARTICIPANTS",
    "BAIL INFORMATION",
    "CHARGES",
    "DISPOSITION SENTENCING/PENALTIES",
    "COMMONWEALTH INFORMATION",
    "ENTRIES",
    "PAYMENT PLAN SUMMARY",
    "CASE FINANCIAL INFORMATION",
    "PETITIONER INFORMATION",
]


def parse_person(txt: str) -> Tuple[Person, List[str]]:
    """
    Extract a Person from the text of a CP docket.
    """
    person = Person(first_name=None, last_name=None, date_of_birth=None)
    errs = []
    defendant_name, d_errs = find_pattern(
        "defendant_name",
        r"^Defendant\s+(?P<last_name>.*), (?P<first_name>.*)",
        txt,
        re.M,
    )
    if defendant_name is not None:
        person.first_name = defendant_name.group("first_name")
        person.last_name = defendant_name.group("last_name")
    else:
        errs.extend(d_errs)

    defendant_dob, dob_errs = find_pattern(
        "date_of_birth",
        r"Date Of Birth:?\s+(?P<date_of_birth>\d{1,2}\/\d{1,2}\/\d{4})",
        txt,
    )
    if defendant_dob is not None:
        person.date_of_birth = date_or_none(defendant_dob.group("date_of_birth"))
    else:
        errs.extend(dob_errs)

    defendant_info_section, d_section_errs = find_pattern(
        "defendant_info",
        r"DEFENDANT INFORMATION(?P<defendant_info>.*)\s+CASE PARTICIPANTS",
        txt,
        re.DOTALL,
    )
    if defendant_info_section is not None:
        defendant_info_text = defendant_info_section.group("defendant_info")
        alias_search, a_errs = find_pattern(
            "aliases", r"Alias Name\s*\n+(?P<aliases>(.+\s*\n*)*)", defendant_info_text
        )
        if alias_search is not None:
            person.aliases = [
                a.strip()
                for a in alias_search.group("aliases").split("\n")
                if len(a) > 0
            ]
        else:
            errs.extend(a_errs)

        addr_search, addr_errs = find_pattern(
            "address", r"City/State/Zip:\s*(?P<addr>.*)\s*", defendant_info_text
        )
        if addr_search is not None:
            person.address = Address(addr_search.group("addr"), "")
        else:
            errs.extend(addr_errs)
    else:
        errs.extend(d_section_errs)

    return person, errs


def parse_charges(txt: str) -> Tuple[Optional[List[Charge]], List[str]]:
    """
    Find the charges in the text of a docket.
    

    Returns:
        Tuple[0] is either None or a list of Charges.
        Tuple[1] is a list of strings describing errors encountered.
    """
    logger.info("      parsing charges")
    # First, parse the Charges section to get a list of the charges, type [Charge]
    charges, errs = parse_charges_section(txt)

    # Second, parse the Dispositions section to find any dispositions.
    charges_w_dispositions, more_errs = parse_disposition_section(txt)
    errs.extend(more_errs)
    # now update the Charges from the [Charge] list with dispositions from the list of dispositions.
    charges = update_charges_with_dispositions(charges, charges_w_dispositions)

    # return a list of charges, rather than the {sequence number: Charge} mapping.
    charges = [chrg for _, chrg in charges.items()]
    return charges, errs


def update_charges_with_dispositions(
    charges: Dict[int, Charge], charges_w_dispositions: Dict[int, Charge]
) -> Dict[int, Charge]:
    """
    Update a dictionary of Charges information with disposition information from the Disposition section.



    Args:
        charges (dict): A dictionary mapping sequence numbers to Charge objects
        charges_w_dispositions (dict): A dictionary mapping sequence numbers to Charge objects.
    """
    # need all the keys from both charges and charges_w_dispositions, in case there's a sequence either parser misses.
    all_sequences = set(
        k for k in list(charges.keys()) + list(charges_w_dispositions.keys())
    )
    all_charges = dict()
    for seq_num in all_sequences:
        all_charges[seq_num] = Charge.combine(
            charges.get(seq_num), charges_w_dispositions.get(seq_num)
        )
    # and need to update these keys with the most complete info from either dict.
    return all_charges


def update_charges_with(line: str, col_dict: dict, charges: dict) -> dict:
    """
    Take a line from a Charges section.

    Using the col_dict, a dict of the indexes of the columns in the Charges table,
    map the pieces of the `line` to the right columns.

    If it is the first line of a charge, then add this charge to `charges`.

    If it is a continuation line, add the continuation line to the last charge added to charges.
    """
    mapped_line = map_line(line, col_dict)
    if mapped_line.get("sequence") in [None, ""]:
        last_charge_added = list(charges.keys())[-1]
        update_charge_dict(charges[last_charge_added], mapped_line)
    else:
        charges[mapped_line.get("sequence")] = mapped_line

    return charges


def update_charge_dict(
    charge_dict: Dict[int, Union[str, int]], update_dict: Dict[int, Union[str, int]]
) -> Dict[int, Union[str, int]]:
    """
    Update a dict describing a charge by appending any non-blank corresponding keys from update_dict.

    This only gets called when `sequence` is blank, indicating that the `update_dict` is describing
    a continuation of `charge_dict`, and not a separate charge.

    Args:
        charge_dict (dict): Dictionary mapping sequence numbers to info about a charge.
        update_dict (dict): Dictionary mapping sequence numbers to info about a charge.


    Returns:
        A dict that extends the string values of `charge_dict` with corresponding continuations in `update_dict`

    """
    updated = dict()
    for key, val in charge_dict.items():
        # If a corresponding key in `update_dict`
        if isinstance(val, str) and isinstance(update_dict[key], str):
            updated[key] = val + update_dict[key]
        else:
            updated[key] = val
    return updated


def parse_charges_section(txt: str) -> Tuple[dict, List[str]]:
    """
    Collect a list of the charges described in the Charges section of a docket. 

    Args:
        txt (str): Text that may contain a Charges section listing out
        criminal charges in a tabular format.

    Returns:
        A tuple. Item 0 is a dict with the columns of charges filled in, indexed by the
            sequence number of the charge. 
            Item 1 is a list of error messages. 
    """
    charges_section_searcher = re.compile(
        r"(?:.*\s+)CHARGES\s*\n((?P<charges_section>(?:.+\n)+?(?=[A-Z\/ ]+\n))+.*)"
    )  # TODO - grr - this still has the first line of the next section, like ATTORNEY INFORMATION ...
    errs = []
    charges_sections = charges_section_searcher.findall(txt)
    if len(charges_sections) == 0:
        errs.append("Could not find a CHARGES section.")
        return {}, errs
    charges = dict()  # storing charges as a dict, where keys are sequence numbers.
    for charges_section in charges_sections:
        # in case, because of page overflows, there are multiple charges sections
        lines = charges_section[0].split("\n")
        header_line = lines[0]
        col_dict = dict()
        col_dict["sequence"] = {
            "idx": find_index_for_pattern("Seq.", header_line),
            "fmt": str,
        }
        col_dict["grade"] = {
            "idx": find_index_for_pattern("Grade", header_line),
            "fmt": None,
        }
        col_dict["statute"] = {
            "idx": find_index_for_pattern("Statute", header_line),
            "fmt": None,
        }
        col_dict["offense"] = {
            "idx": find_index_for_pattern("Statute Description", header_line),
            "fmt": None,
        }
        col_dict["otn"] = {
            "idx": find_index_for_pattern("OTN", header_line),
            "fmt": None,
        }
        for line in lines[1 : len(lines) - 1]:
            # Need to trim `lines`. The first line is the header, "Seq.   Grade ...".
            #  The last line is the header of the next section, "ATTORNEY INFORMATION ...."
            charges = update_charges_with(line, col_dict, charges)

    charges = {key: Charge.from_dict(val) for key, val in charges.items()}
    return charges, errs


def parse_disposition_section(
    txt: str,
) -> Tuple[Optional[Dict[str, Charge]], List[str]]:
    """
    Parse the disposition section of a docket.

    This will return a dict. The keys are sequence numbers of the charges found in that section, and 
    the values are the last events to happen to the charge with each sequence number
    (i.e., the final disposition, if any).
    """
    disposition_section_searcher = re.compile(
        r"(?:.*\s+)DISPOSITION SENTENCING/PENALTIES\s*\n(?P<disposition_section>(.+\n+(?=[A-Z ]+))+.*)"
    )
    errs = []
    disposition_sections = disposition_section_searcher.findall(txt)
    if disposition_section_searcher == []:
        errs.append("Could not find the disposition/sentencing section.")
        return {}, errs
    charges = []
    charges_pattern = r"(?P<sequence>[\d,]+)\s+\/\s+(?P<offense>.+)\s{12,}(?P<disposition>\w.+?)(?=\s\s)\s{12,}(?P<grade>\w{0,2})\s+(?P<statute>\w{1,2}\s?\u00A7\s?\d+(\-|\u00A7|\w+)*)"
    # there may be multiple disposition sections
    for disposition_section in disposition_sections:
        section_text = disposition_section[0]
        section_lines = section_text.split("\n")
        for idx, ln in enumerate(section_lines):
            # Need to use a copy of the index, to advance if we find a charge overflow line, so that
            # when we reach forward for the disposition date, we compensate if we've also found a charge overflow line.
            idx_copy = idx
            # not using the find_pattern function here because we're doing repeated searches on every line,
            # and failing to match is not an error, in that case.
            charge_line_search = re.search(charges_pattern, ln)
            if charge_line_search is not None:
                offense = charge_line_search.group("offense").strip()
                charge_overflow_search = re.search(
                    r"^\s+(?P<offense_overflow>\w+\s*\w*)\s*$",
                    section_lines[idx + 1],
                    re.I,
                )
                if charge_overflow_search is not None:
                    offense += (
                        " " + charge_overflow_search.group("offense_overflow").strip()
                    )
                    idx_copy += 1
                try:
                    sequence = charge_line_search.group("sequence").strip()
                except Exception:
                    sequence = None
                charge = Charge(
                    sequence=sequence,
                    offense=offense,
                    grade=charge_line_search.group("grade"),
                    statute=charge_line_search.group("statute"),
                    disposition=charge_line_search.group("disposition"),
                    sentences=[],  # TODO: re_parse_cp_pdf parser does not collect Sentences yet.
                )

                disp_date_search_pattern = (
                    r"(?m)^\s*(\S+\s)+\s+(?P<disposition_date>\d\d/\d\d/\d\d\d\d).*$"
                )
                # disp_date_search_pattern = r"(.*)\s(?P<disposition_date>\d{1,2}\/\d{1,2}\/\d{4})"
                # sometimes a single charge may have multiple successive disposition dates. We need the last one.
                next_line_index = idx_copy + 1
                disp_date_search = re.search(
                    disp_date_search_pattern, section_lines[next_line_index],
                )
                next_line_index += 1
                while re.search(
                    disp_date_search_pattern, section_lines[next_line_index],
                ):
                    disp_date_search = re.search(
                        disp_date_search_pattern, section_lines[next_line_index],
                    )
                    next_line_index += 1

                #
                # disposition_date_line = section_lines[idx_copy + 1]
                # disp_date_search = re.search(r"(.*)\s(?P<disposition_date>\d{1,2}\/\d{1,2}\/\d{4})",disposition_date_line)
                if disp_date_search is not None:
                    charge.disposition_date = date_or_none(
                        disp_date_search.group("disposition_date")
                    )
                    if charge.disposition_date is None:
                        errs.append(
                            f"For the offense, {charge.sequence}/ {offense}, we found, but could not parse, the disposition date: {disp_date_search.group('disposition_date')}"
                        )
                charges.append(charge)
    # A docket tracks multiple charges through a history of changes. We take the list of charges, and then reduce it down to a list of the last events that
    # happened to each charge.
    # We also convert this list of charges to a mapping of sequence number -> Charge.
    charges = {c.sequence: c for c in Charge.reduce_merge(charges)}
    missing_disposition_dates = [
        f"Could not find disposition date for {c.sequence} / {c.offense} with disposition {c.disposition}"
        for _, c in charges.items()
        if c.disposition_date is None
    ]
    errs += missing_disposition_dates
    return charges, errs


def parse_case(txt: str) -> Tuple[Case, List[str]]:
    """
    Use regexes to extract case information from the text of a docket.

    Args:
        txt (str): The text of a CP or MC docket. 

    """

    errs = []
    case = Case(
        status=None, county=None, docket_number=None, otn=None, dc=None, charges=[]
    )

    docket_number_search, dn_errs = find_pattern(
        "docket_number",
        r"Docket Number:\s+(?P<docket_number>(MC|CP)\-\d{2}\-(\D{2})\-\d*\-\d{4})",
        txt,
    )
    if docket_number_search is not None:
        case.docket_number = docket_number_search.group("docket_number")
    else:
        errs.extend(dn_errs)

    otn_search, otn_errs = find_pattern(
        "otn", r"OTN:\s+(?P<otn>\D(\s)?\d+(\-\d)?)", txt
    )
    if otn_search is not None:
        case.otn = otn_search.group("otn")
    else:
        errs.extend(otn_errs)

    charges, charge_errs = parse_charges(txt)
    case.charges = charges
    errs.extend(charge_errs)

    costs_search, costs_errs = find_pattern(
        "costs",
        (
            r"Grand Totals:\s+\$(?P<charged>[\d\,]+\.\d{2})\s+"
            + r"-?\(?\$(?P<paid>[\d\,]+\.\d{2})\)?\s+-?\(?\$"
            + r"(?P<adjusted>[\d\,]+\.\d{2})\)?\s+-?\(?\$([\d\,]+"
            + r"\.\d{2})\)?\s+-?\(?\$(?P<total>[\d\,]+\.\d{2})\)?"
        ),
        txt,
    )
    if costs_search is not None:
        case.total_fines = money_or_none(costs_search.group("charged"))
        case.fines_paid = money_or_none(costs_search.group("paid"))
        if case.total_fines is None or case.fines_paid is None:
            errs.append("Found costs and fines, but could not convert to a number.")
    else:
        errs.extend(costs_errs)

    restitution_search, restitution_errs = find_pattern(
        "restitution",
        (
            r"Restitution Totals:\s+\$(?P<assessed>[\d\,]+\.\d{2})\s+"
            + r"-?\(?\$(?P<paid>[\d\,]+\.\d{2})\)?\s+-?\(?\$"
            + r"(?P<adjusted>[\d\,]+\.\d{2})\)?\s+-?\(?\$([\d\,]+"
            + r"\.\d{2})\)?\s+-?\(?\$(?P<remaining>[\d\,]+\.\d{2})\)?"
        ),
        txt,
    )
    if restitution_search is not None:
        case.restitution_assessed = money_or_none(restitution_search.group("assessed"))
        case.restitution_paid = money_or_none(restitution_search.group("paid"))
        case.restitution_remaining = money_or_none(
            restitution_search.group("remaining")
        )
    else:
        errs.extend(restitution_errs)

    status_search, status_search_errs = find_pattern(
        "status", r"case status:\s+(?P<status>(?:\w+\s)+)", txt, re.I
    )
    if status_search is not None:
        case.status = status_search.group("status")
    else:
        errs.extend(status_search_errs)

    cty_search, cty_errs = find_pattern(
        "county", r"\sof\s(?P<county>\w+)\sCOUNTY", txt, re.I
    )
    if cty_search is not None:
        case.county = cty_search.group("county")
    else:
        errs.extend(cty_errs)

    complaint_date_search, cd_errs = find_pattern(
        "complaint_date",
        r"Complaint Date:\s+(?P<complaint_date>\d{1,2}\/\d{1,2}\/\d{4})",
        txt,
    )
    if complaint_date_search is not None:
        complaint_date = date_or_none(complaint_date_search.group("complaint_date"))
        if complaint_date is not None:
            case.complaint_date = complaint_date
        else:
            errs.append(
                f"Found complaint date, but could not understand the date format: {complaint_date_search.group('complaint_date')}"
            )
    else:
        errs.extend(cd_errs)

    arrest_date_search, arrest_date_errs = find_pattern(
        "arrest_date", r"Arrest Date:\s+(?P<arrest_date>\d{1,2}\/\d{1,2}\/\d{4})", txt
    )
    if arrest_date_search is not None:
        arrest_date = date_or_none(arrest_date_search.group("arrest_date"))
        if arrest_date is not None:
            case.arrest_date = arrest_date
        else:
            errs.append(
                f"Found arrest date but could not understand the date format: {arrest_date_search.group('arrest_date')}"
            )
    else:
        errs.extend(arrest_date_errs)

    disp_date_search, _ = find_pattern(
        "disposition_date",
        r"(?:Plea|Status|Status of Restitution|Status - Community Court|"
        + r"Status Listing|Migrated Dispositional Event|Trial|Preliminary Hearing|"
        + r"Pre-Trial Conference)\s+(?P<disposition_date>\d{1,2}\/\d{1,2}\/\d{4})\s+"
        + r"Final Disposition",
        txt,
    )
    if disp_date_search is not None:
        disp_date = date_or_none(disp_date_search.group("disposition_date"))
        if disp_date is not None:
            case.disposition_date = disp_date
        else:
            errs.append(
                "Found disposition date, but could not understand date format: "
                + f"{disp_date_search.group('disposition_date')}"
            )
    # its not necessarily an error, to not find a disposition date this way.
    # There might not actually be a disposition date.
    # else:
    #    errs.extend(disp_date_errs)
    # judge_address = self.judge_address,

    # Notes from E.G.:
    #   the judge name can appear in multiple places.  Start by checking to see if the
    #   judge's name appears in the Judge Assigned field.  If it does, then set it.
    #   Later on, we'll check in the "Final Issuing Authority" field.  If it appears there
    #   and doesn't show up as "migrated," we'll reassign the judge name.
    judge_assignment_pattern = (
        r"Judge Assigned:\s+(?P<judge_assigned>.*)\s+(Date Filed|Issue Date):"
    )
    judge_assigned_search, judge_assigned_errs = find_pattern(
        "judge_assigned", judge_assignment_pattern, txt
    )
    if judge_assigned_search is not None:
        judge_assigned = judge_assigned_search.group("judge_assigned")
        judge_assigned.replace("Magisterial District Judge", "").strip()
        # the E.G., because it searched line by line, looked at the line following the line matching the judge search.
        # this parser doesn't look like by line, so I'm doing the same thing by concatenating the judge_assignment seach,
        # a new_line, and the overflow pattern.

        # N.B. the EG only searches for overflow if "Magisterial District Judge" was in the assigned judge name. is that necessary?
        judge_overflow_search, _ = find_pattern(
            "judge_overflow_info",
            judge_assignment_pattern + "\n" + r"^\s+(?P<judge_overflow>\w+\s*\w*)\s*$",
            txt,
        )
        if judge_overflow_search is not None:
            judge_assigned += (
                " " + judge_overflow_search.group("judge_overflow").strip()
            )
        if re.search("migrated", judge_assigned, re.I):
            judge_assigned = None
        case.judge = judge_assigned
    else:
        errs.extend(judge_assigned_errs)

    # sometimes the judge is identified as the Final Issuing Authority.
    final_issue_auth_search, _ = find_pattern(
        "final_issuing_authority", r"Final Issuing Authority:\s+(?P<judge_name>.*)", txt
    )
    if final_issue_auth_search is not None:
        judge_name = final_issue_auth_search.group("judge_name").strip()
        if not re.search("migrated", judge_name, re.I):
            case.judge = judge_name

    dc_search, _ = find_pattern("dc", r"District Control Number\s+(?P<dc>\d+)", txt)
    if dc_search is not None:
        case.dc = dc_search.group("dc")
    # The District Control Number actually seems pretty rare,
    # so not finding shouldn't be recorded as an error.
    # else:
    # errs.extend(dc_errs)

    arresting_agency_search, arresting_agency_errs = find_pattern(
        "arresting_agency and officer",
        r"Arresting Agency:\s+(?P<agency>.*)\s+Arresting Officer: (?P<officer>\D+)",
        txt,
    )
    if arresting_agency_search is not None:
        case.affiant = arresting_agency_search.group("officer")
        if case.affiant.strip() == "" or re.search("Affiant", case.affiant):
            case.affiant = "Unknown Officer"
        case.arresting_agency = arresting_agency_search.group("agency")
    else:
        errs.extend(arresting_agency_errs)

    # arresting_agency_address = self.arresting_agency_address,
    return case, errs


def parse_cp_pdf_text(txt: str) -> Tuple[Person, List[Case], List[str]]:
    """
    Regex-based parser for dockets from the Court of Common Pleas,
     including both Common Pleas and Municpal Court dockets.

    This function takes the text of the docket, extracted from a pdf.
    """
    person, person_errs = parse_person(txt)
    case, case_errs = parse_case(txt)
    return person, [case], person_errs + case_errs


def parse_cp_pdf(pdf: Union[BinaryIO, str]) -> Tuple[Person, List[Case], List[str]]:
    """
    Regex-based parser for CP dockets, including MC and CP.

    This parser is essentially a Python re-implementation of the original
    Expungement Generator's parsing methods. 
    The only differences are that this function only handles CP/MC dockets (not MDJ dockets);
    it only parses, it doesn't include any of Arrest.php's logic
    related to generating petitions; it abstracts its components into smaller functions; and it
    reports errors that came up during the parsing process.

    This function takes the pdf file as a binary or a path, and extracts the text.
    It sends the text to a more
    specialized function that does the actual parsing.

    """
    # pdf to raw text
    txt = get_text_from_pdf(pdf)
    if txt == "":
        return None, None, ["could not extract text from pdf"]
    return parse_cp_pdf_text(txt)

