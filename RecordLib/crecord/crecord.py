"""
Class that represents a Criminal Record in Pennsylvania.

Note - it looks like i can't use dataclasses throughout because
       dataclasses don't support nested dataclass without overriding init, so
       what's the point?
"""
from __future__ import annotations
from typing import List, Optional
import logging
import re
from dataclasses import asdict
from datetime import date
from dateutil.relativedelta import relativedelta
from .person import Person
from .case import Case
from .common import Charge


def years_between_convictions(crecord: CRecord, case: Case, charge: Charge) -> int:
    """
    How many years elapsed between the conviction `charge` in `case`, and the next conviction?
    """
    convictions_only = []
    for case in crecord.cases:
        append = False
        for charge2 in case.charges:
            if charge2.is_conviction():
                append = True
                break
        if append:
            convictions_only.append(case)

    convictions_sorted = sorted(convictions_only, key=Case.order_cases_by_last_action)
    start_date = charge.disposition_date or case.disposition_date
    subsequent_convictions = [
        c for c in convictions_sorted if case.last_action() > start_date
    ]
    if len(subsequent_convictions) == 0:
        # There are no convictions after the one we're interested in, so the answer is the
        # years between the start_date and now.
        return relativedelta(date.today(), start_date).years
    else:
        return relativedelta(subsequent_convictions[0].last_action(), start_date).years


def years_since_last_arrested_or_prosecuted(crecord: CRecord) -> int:
    """
    How many years since a person was last arrested or prosecuted?

    If we can't tell how many years, return 0.

    If they don't have any cases, then years-since-last is Infinite.
    """
    if crecord.cases is None:
        return float("Inf")
    if len(crecord.cases) == 0:
        return float("Inf")
    if any(
        "Active" in case.status for case in crecord.cases if case.status is not None
    ):
        return 0
    cases_ordered = sorted(crecord.cases, key=Case.order_cases_by_last_action)
    last_case = cases_ordered[-1]
    try:
        return relativedelta(date.today(), last_case.last_action()).years
    except (ValueError, TypeError):
        return 0


def years_since_final_release(crecord: CRecord) -> int:
    """
    How many years since a person's final release from confinement or
    supervision?

    If the record has no cases, the person was never confined, so return "infinity." If we cannot tell, because cases don't identify when confinement ended, return 0.
    """
    confinement_ends = [
        c.end_of_confinement() for c in crecord.cases if c.was_confined()
    ]
    if len(confinement_ends) == 0:
        return float("Inf")
    try:
        # nb. relativedelta(a, b) = c
        # if a is before b, then c is negative. if a is after b, c is positive.
        # relativedelta(today, yesterday) > 0
        # relativedelta(yesterday, today) < 0
        return max(relativedelta(date.today(), max(confinement_ends)).years, 0)
    except (ValueError, TypeError):
        return 0


class CRecord:
    """
    Track information about a criminal record
    """

    @staticmethod
    def from_dict(dct: dict) -> Optional[CRecord]:
        """
        Create a CRecord from a dict representation of one.
        """
        try:
            try:
                person = Person.from_dict(dct["person"])
            except:
                person = None
            try:
                cases = [Case.from_dict(c) for c in dct["cases"]]
            except:
                cases = []
            return CRecord(person=person, cases=cases)
        except:
            return None

    person: Person
    cases: List[Case]

    years_since_last_arrested_or_prosecuted = years_since_last_arrested_or_prosecuted

    years_since_final_release = years_since_final_release
    years_between_convictions = years_between_convictions

    def __init__(self, person: Person = None, cases: List[Case] = None):
        self.person = person
        if cases is None:
            self.cases = list()
        else:
            self.cases = cases

    def to_dict(self) -> dict:
        # TODO Delete
        return {
            "person": asdict(self.person),
            "cases": [c.to_dict() for c in self.cases],
        }

    def handle_transferred_cases(self):
        """
        Find any cases in this record that were transferred to some other case in the record. 

        If a charge is "Held for Court", try to find the same charge elsewhere in the record (matching by OTN)
        If found, remove the 'held-for-court' charge from its Case, and add the case's docket number to the 'prior_cases' list on the case with the real final disposition.
        """
        for case in self.cases:
            for ch_idx, charge in enumerate(case.charges):
                if charge.disposition and re.search(
                    "held for court", charge.disposition, re.I
                ):
                    # try to find another charge that matches this one, using the OTN.
                    other_cases = self.find_case_by_otn(
                        case.otn or charge.otn,
                        except_for_docket_numbers=[case.docket_number],
                    )
                    if len(other_cases) > 0:
                        other_case = other_cases[0]
                        # if we've found a case that matches, remove this charge from this case, and add this docket number to the matching cases's information.
                        other_case.related_cases.append(case.docket_number)
                        case.remove_charge_by_index(ch_idx)
                        # Also, if a case no longer has any charges, remove it from this crecord.
                        if len(case.charges) == 0:
                            self.remove_case_by_docket_number(case.docket_number)

    def find_case_by_otn(self, otn, except_for_docket_numbers=None) -> List[Case]:
        """
        Find cases in a record by OTN number. 
        """
        if except_for_docket_numbers is None:
            except_for_docket_numbers = []
        if otn is None:
            return []
        found_cases = []
        for case in self.cases:
            for charge in case.charges:
                otns_match = case.otn == otn or charge.otn == otn
                this_case_isnt_excluded = (
                    case.docket_number not in except_for_docket_numbers
                )
                if otns_match and this_case_isnt_excluded:
                    found_cases.append(case)
        return found_cases

    def remove_case_by_docket_number(self, docket_number):
        """
        Remove a case from this record that matches the docket_number.
        """
        self.cases = [
            case for case in self.cases if case.docket_number != docket_number
        ]

    def add_case(self, new_case):
        """
        Add a case to this record. Check to make sure that any subordinate cases (i.e. a case that was Held For Court, so that the 'real' final case is something else) are properly handled.
        """
        docket_nums = {c.docket_number: i for i, c in enumerate(self.cases)}
        if docket_nums.get(new_case.docket_number, None) is not None:
            self.cases[docket_nums.get(new_case.docket_number)].merge(new_case)
        else:
            self.cases.append(new_case)
        self.handle_transferred_cases()

    def add_summary(
        self,
        summary: "Summary",
        # case_merge_strategy: str = "ignore_new",
        override_person: bool = False,
    ) -> CRecord:
        """
        Add the information of a summary sheet to a CRecord.

        Depending on the `case_merge_strategy`, any cases in the summary sheet
        that have a docket number that matches any case already in this
        CRecord will not be added, or the new case will overwrite the old.

        Depending on `override_person`, if a new Summary's Get Defendant returns a person who appears to be a different person, then the new Person will or will not be overwritten in this Record. If the CRecord has no person attribute, then the Person from the Summary will be added to this record regardless of this param.

        Args:
            summary (Summary): A parsed summary sheet.
            case_merge_strategy (str): "ignore_new" or "overwrite_old", which indicate whether duplicate new cases should be dropped or should replace the old ones

        Returns:
            This updated CRecord object.
        """
        # Get D's name from the summary
        if override_person or self.person is None:
            self.person = summary.get_defendant()
        for new_case in summary.get_cases():
            logging.info(f"Adding {new_case.docket_number} to record.")
            self.add_case(new_case)

        return self

    def add_docket(self: CRecord, docket: "Docket") -> CRecord:
        """
        Add a docket to this criminal record and return the record.

        Args:
            docket (Docket): a Docket object, perhaps from a parsed pdf.

        Returns:
            This CRecord, with the information from `docket` incorporated into the record.
        """
        # TODO Person#merge(new_person) instead of dumbly overwriting Person in CRecord#add_docket
        self.person = docket._defendant
        self.add_case(docket._case)
        return self

    def add_sourcerecord(
        self,
        sourcerecord: "SourceRecord",
        # case_merge_strategy: str = "ignore_new",
        override_person: bool = False,
        docket_number: Optional[str] = None,
    ) -> CRecord:
        """
        Add the information from a SourceRecord to a CRecord.

        Depending on the `case_merge_strategy`, any cases in the source record 
        that have a docket number that matches any case already in this
        CRecord will not be added, or the new case will overwrite the old.

        Depending on `override_person`, if a new source record has a person who
        appears to be a different person, then the new Person will or will not be overwritten in this 
        Record. If the CRecord has no person attribute, then the Person from the source record will be
        added to this record regardless of this param.


        Args:
            sourcerecord (SourceRecord): A parsed sourcerecord
            case_merge_strategy (str): "ignore_new" or "overwrite_old", which indicate whether duplicate new cases should be 
                dropped or should replace the old ones
            override_person (bool): Should the source record's Person replace the crecord's current Person?
            docket_number (str or None): If provided, and if the sourcerecord only contains one case (i.e., its a Docket, 
                not a Summary), then give the case this docket number.

        Returns:
            This updated CRecord object.
        """
        # Get D's name from the sourcerecord
        if (override_person or self.person is None) and sourcerecord.person is not None:
            self.person = sourcerecord.person
        # Get the cases from the source record
        if sourcerecord.cases is None:
            # We're done. No modifications of self are necessary.
            return self

        for new_case in sourcerecord.cases:
            # If we're only adding one case, and have passed in a docket number, give the new case the docket number.
            if docket_number is not None and len(sourcerecord.cases) == 1:
                new_case.docket_number = docket_number
            self.add_case(new_case)
        return self

