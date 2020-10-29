from __future__ import annotations
from typing import Optional, List
from dataclasses import dataclass, fields
from datetime import date
import logging
import functools
import re

from RecordLib.crecord import Sentence
from RecordLib.crecord.helpers import date_or_none

logger = logging.getLogger(__name__)


@dataclass
class Charge:
    """
    Track information about a charge
    """

    offense: str
    grade: str
    statute: str
    sequence: Optional[str] = None  # I think this really ought to be not optional
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None
    sentences: Optional[List[Sentence]] = None
    # TODO sequence should not be optional.
    otn: Optional[str] = None

    @staticmethod
    def grade_GTE(grade_a: str, grade_b: str) -> bool:
        """
        Greater-than-or-equal-to ordering for charge grades.

        Args:
            grade_a: A grade like "M1", "F2", "S", etc.
            grade_b: A grade like "M1", "F2", "S", etc.
        
        Returns: 
            True if grade_a is the same grade as or more serious than grade_b 
        
        Examples:
            grade_GTE("M1", "S") == True
            grade_GTE("S","") == False
        """
        grades = ["", "S", "M", "IC", "M3", "M2", "M1", "F", "F3", "F2", "F1"]
        try:
            i_a = grades.index(grade_a)
        except ValueError:
            logger.error(
                f"Couldn't understand the first grade, {grade_a}, so assuming it has low seriousness."
            )
            i_a = 0
        try:
            i_b = grades.index(grade_b)
        except:
            logger.error(
                f"Couldn't understand the second grade, {grade_b}, so assuming it has low seriousness."
            )
            i_b = 0
        return i_a >= i_b

    @staticmethod
    def from_dict(dct: dict) -> Charge:
        try:
            if dct.get("sentences"):
                dct["sentences"] = [Sentence.from_dict(s) for s in dct.get("sentences")]
            else:
                dct["sentences"] = []
            if dct.get("disposition_date"):
                dct["disposition_date"] = date_or_none(dct.get("disposition_date"))
            return Charge(**dct)
        except Exception as err:
            logger.error(str(err))
            return None

    @staticmethod
    def reduce_merge(charges: List[Charge]) -> List[Charge]:
        """
        Given a list of charges, reduce the list by merging charges with the same sequence number.

        In a Docket, there's often a number of records relating to a single charge. There records explain
        how a charge proceeded through the case. When we parse a docket, if we find lots of records of 
        charges, we need to reduce them into a list where each charge only appears once.
        """

        def reducer(accumulator, charge):
            """
            Add charge to accumulator, if the charge is new. Otherwise combine charge with its pre-existing charge.
            """
            if len(accumulator) == 0:
                return [charge]
            new_charges = []
            is_new = True
            for ch in accumulator:
                if (
                    isinstance(charge.sequence, str)
                    and charge.sequence == ch.sequence
                    and charge.sequence.strip() != ""
                ):
                    ch.combine_with(charge)
                    is_new = False
            if is_new:
                accumulator.append(charge)
            return accumulator

        reduced = functools.reduce(reducer, charges, [])
        return reduced

    @staticmethod
    def combine(ch1: Optional[Charge], ch2: Optional[Charge]) -> Charge:
        """
        Combine two charges, using the most complete information from both.
        """

        def pick_more_complete(thing1, thing2):
            if thing1 in [None, ""]:
                # this means that None in thing2 would override "" in thing1. Is that good?
                return thing2
            return thing1

        if ch1 is None:
            return ch2
        if ch2 is None:
            return ch1

        return Charge(
            **{
                field.name: pick_more_complete(
                    getattr(ch1, field.name), getattr(ch2, field.name)
                )
                for field in fields(ch1)
            }
        )

    def combine_with(self, charge) -> Charge:
        """
        Combine this Charge with another, filling in missing info, or updating certain fields.
        """
        for attr in self.__dict__.keys():
            if getattr(self, attr) is None and getattr(charge, attr) is not None:
                setattr(self, attr, getattr(charge, attr))
            elif (
                isinstance(getattr(self, attr), str)
                and getattr(self, attr).strip() == ""
            ) and (
                isinstance(getattr(charge, attr), str)
                and (getattr(charge, attr).strip() != "")
            ):
                setattr(self, attr, getattr(charge, attr))
            elif attr == "disposition":
                if re.search(r"nolle|guilt|dismiss|withdraw", charge.disposition, re.I):
                    # the new charge has a disposition that should be saved as the final disposition of this charge.
                    self.disposition = charge.disposition
                    self.disposition_date = getattr(charge, "disposition_date", None)

        return self

    def is_conviction(self) -> bool:
        """Is this charge a conviction?

        There are lots of different dispositions, and this helps identify if a disp. counts as a conviction or not.
        """
        if self.disposition is None:
            logger.warning("No disposition.")
            return False
        if re.match("^Guilty", self.disposition.strip()):
            return True
        else:
            return False

    def get_statute_chapter(self) -> Optional[float]:
        """ Get the Chapter in the PA Code that this charge is related to. 
        """
        patt = re.compile(r"^(?P<chapt>\d+)\s*§\s(?P<section>\d+).*")
        match = patt.match(self.statute)
        if match:
            return float(match.group("chapt"))
        else:
            return None

    def get_statute_section(self) -> Optional[float]:
        """ Get the Statute section of the PA code, to which this charge is related.
        """
        patt = re.compile(r"^(?P<chapt>\d+)\s*§\s(?P<section>\d+\.?\d*).*")
        match = patt.match(self.statute)
        if match:
            return float(match.group("section"))
        else:
            return None

    def get_statute_subsections(self) -> str:
        """ Get the subsection, if any, to which this charge relates
        """
        patt = re.compile(
            r"^(?P<chapt>\d+)\s*§\s(?P<section>\d+\.?\d*)\s*§§\s*(?P<subsections>[\(\)A-Za-z0-9\.\*]+)\s*.*"
        )
        match = patt.match(self.statute)
        if match:
            return match.group("subsections")
        else:
            return ""

