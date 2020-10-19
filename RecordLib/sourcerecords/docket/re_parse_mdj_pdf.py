from typing import Union, BinaryIO, Tuple, Callable, List, Optional
import re
import logging
from RecordLib.crecord import Person, Case, Charge
from RecordLib.sourcerecords.parsingutilities import get_text_from_pdf


logger = logging.getLogger(__name__)


class PATTERNS:
    mdj_district_number = re.compile(r"Magisterial District Judge\s(.*)", re.I)
    mdj_county_and_disposition = re.compile(
        r"County:\s+(.*)\s+Disposition Date:\s+(.*)", re.I
    )
    docket_number = re.compile(
        r"Docket Number:\s+(MJ\-\d{5}\-(\D{2})\-\d*\-\d{4})", re.I
    )
    otn = re.compile(r"OTN:\s+(\D(\s)?\d+(\-\d)?)", re.I)
    dc_number = re.compile(r"District Control Number\s+(\d+)", re.I)
    arrest_agency_and_date = re.compile(
        r"Arresting Agency:\s+(.*)\s+Arrest Date:\s*(\d{1,2}\/\d{1,2}\/\d{4})?", re.I
    )
    complaint_date = re.compile(r"Issue Date:\s+(\d{1,2}\/\d{1,2}\/\d{4})", re.I)
    affiant = re.compile(r"^\s*Arresting Officer (\D+)\s*$", re.I)
    judge_assigned = re.compile(
        r"Judge Assigned:\s+(.*)\s+(Date Filed|Issue Date):", re.I
    )
    judge_assigned_overflow = re.compile(r"^\s+(\w+\s*\w*)\s*$", re.I)
    judge = re.compile(r"Final Issuing Authority:\s+(.*)", re.I)
    dob = re.compile(r"Date Of Birth:?\s+(\d{1,2}\/\d{1,2}\/\d{4})", re.I)
    name = re.compile(r"^Defendant\s+(.*), (.*)", re.I)
    alias_names_start = re.compile(r"Alias Name", re.I)
    alias_names_end = re.compile(r"CASE PARTICIPANTS", re.I)
    end_of_page = re.compile(r"(CPCMS|AOPC)\s\d{4}", re.I)
    charges = re.compile(
        r"^\s*(?P<sequence_num>\d)\s+((\w|\d|\s(?!\s)|\-|\u00A7|\*)+)\s{2,}(\w{0,2})\s{2,}([\d|\D]+)\s{2,}(\d{1,2}\/\d{1,2}\/\d{4})\s{2,}(\D{2,})",
        re.U,
    )
    charges_search_overflow = re.compile(r"^\s+(\w+\s*\w*)\s*$", re.I)
    bail = re.compile(
        r"Bail.+\\$([\d\,]+\.\d{2})\s+-?\\$([\d\,]+\.\d{2})\s+-?\\$([\d\,]+\.\d{2})\s+-?\\$([\d\,]+\.\d{2})\s+-?\\$([\d\,]+\.\d{2})",
        re.I,
    )
    costs = re.compile(
        r"Totals:\s+\\$([\d\,]+\.\d{2})\s+-?\(?\\$([\d\,]+\.\d{2})\)?\s+-?\(?\\$([\d\,]+\.\d{2})\)?\s+-?\(?\\$([\d\,]+\.\d{2})\)?\s+-?\(?\\$([\d\,]+\.\d{2})\)?",
        re.I,
    )


def parse_mdj_pdf_text(txt: str) -> Tuple[Person, List[Case], List[str]]:
    """
    Parse MDJ docket, given the formatted text of the pdf.
    This function uses the original Expungement Generator's technique: regexes and nested loops, 
    iterating over the lines of the docket.

    see https://github.com/NateV/Expungement-Generator/blob/master/Expungement-Generator/Record.php:64

    """
    already_searched_aliases = False

    case_info = dict()
    case_info["charges"] = []
    person_info = dict()
    person_info["aliases"] = []

    lines = txt.split("\n")
    for idx, line in enumerate(lines):
        m = PATTERNS.mdj_district_number.search(line)
        if m:
            # what's the mdj district number for?
            case_info["mdj_district_number"] = m.group(1)

        m = PATTERNS.mdj_county_and_disposition.search(line)
        if m:
            case_info["county"] = m.group(1)
            case_info["disposition_date"] = m.group(2)

        m = PATTERNS.docket_number.search(line)
        if m:
            case_info["docket_number"] = m.group(1)

        m = PATTERNS.otn.search(line)
        if m:
            case_info["otn"] = m.group(1)

        m = PATTERNS.dc_number.search(line)
        if m:
            case_info["dc_num"] = m.group(1)

        m = PATTERNS.arrest_agency_and_date.search(line)
        if m:
            case_info["arresting_agency"] = m.group(1)
            try:
                case_info["arrest_date"] = m.group(2)
            except:
                pass

        m = PATTERNS.complaint_date.search(line)
        if m:
            case_info["complaint_date"] = m.group(1)

        m = PATTERNS.affiant.search(line)
        if m:
            # TODO - mdj docket parse should reverse order of names of affiant
            case_info["affiant"] = m.group(1)

        # MHollander said:
        #  the judge name can appear in multiple places.  Start by checking to see if the
        # judge's name appears in the Judge Assigned field.  If it does, then set it.
        # Later on, we'll check in the "Final Issuing Authority" field.  If it appears there
        # and doesn't show up as "migrated," we'll reassign the judge name.
        m = PATTERNS.judge_assigned.search(line)
        if m:
            judge = m.group(1).strip()
            next_line = lines[idx + 1]
            overflow_match = PATTERNS.judge_assigned_overflow.search(next_line)
            if overflow_match:
                judge = f"{judge} {overflow_match.group(1).strip()}"

            if "igrated" not in judge:
                case_info["judge"] = judge

        m = PATTERNS.judge.search(line)
        if m:
            if len(m.group(1)) > 0 and "igrated" not in m.group(1):
                case_info["judge"] = m.group(1)

        m = PATTERNS.dob.search(line)
        if m:
            person_info["date_of_birth"] = m.group(1)

        m = PATTERNS.name.search(line)
        if m:
            person_info["first_name"] = m.group(2)
            person_info["last_name"] = m.group(1)
            person_info["aliases"].append(f"{m.group(1)}, {m.group(2)}")

        m = PATTERNS.alias_names_start.search(line)
        if already_searched_aliases is False and m:
            idx2 = idx + 1
            end_of_aliases = False
            while not end_of_aliases:
                if PATTERNS.end_of_page.search(lines[idx2]):
                    continue
                if re.search(r"\w", lines[idx2]):
                    person_info["aliases"].append(lines[idx2].strip())
                idx2 += 1

                end_of_aliases = PATTERNS.alias_names_end.search(lines[idx2])
                if end_of_aliases:
                    already_searched_aliases = True

        m = PATTERNS.charges.search(line)  # Arrest.php;595
        if m:
            charge_info = dict()
            charge_info["sequence"] = m.group("sequence_num")
            charge_info["statute"] = m.group(2)
            charge_info["grade"] = m.group(4)
            charge_info["offense"] = m.group(5)
            charge_info["disposition"] = m.group(6)
            m2 = PATTERNS.charges_search_overflow.search(lines[idx + 1])
            if m2:
                charge_info[
                    "offense"
                ] = f"{charge_info['offense'].strip()} {m2.group(1).strip()}"

            ## disposition date is on the next line
            if "disposition_date" in case_info.keys():
                charge_info["disposition_date"] = case_info["disposition_date"]

            case_info["charges"].append(charge_info)

        m = PATTERNS.bail.search(line)
        if m:
            # TODO charges won't use the detailed bail info yet.
            case_info["bail_charged"] = m.group(1)
            case_info["bail_paid"] = m.group(2)
            case_info["bail_adjusted"] = m.group(3)
            case_info["bail_total"] = m.group(5)

        m = PATTERNS.costs.search(line)
        if m:
            case_info["total_fines"] = m.group(1)
            case_info["fines_paid"] = m.group(2)
            case_info["costs_adjusted"] = m.group(3)
            case_info["costs_total"] = m.group(5)
    case_info = {
        k: (v.strip() if isinstance(v, str) else v) for k, v in case_info.items()
    }
    person_info = {
        k: (v.strip() if isinstance(v, str) else v) for k, v in person_info.items()
    }
    person = Person.from_dict(person_info)
    case = Case.from_dict(case_info)
    case.charges = Charge.reduce_merge(case.charges)
    logger.info("Finished parsing MDJ docket")

    return person, [case], []


def parse_mdj_pdf(path: str) -> Tuple[Person, List[Case], List[str]]:
    """
    Parse an mdj docket, given the path to the docket pdf.

    This function uses the original Expungement Generator's technique: regexes and nested loops.

    See https://github.com/NateV/Expungement-Generator/blob/master/Expungement-Generator/Record.php:64
    """
    # a list of strings
    errors = []
    # pdf to raw text
    txt = get_text_from_pdf(path)
    if txt == "":
        return None, None, ["could not extract text from pdf"]
    return parse_mdj_pdf_text(txt)
