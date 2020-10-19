"""
Common, simple dataclasses live here.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
from typing import List, Tuple, Optional
from datetime import date, timedelta
import re
import logging
from dateutil.relativedelta import relativedelta
import json
import functools

logger = logging.getLogger(__name__)


@dataclass
class SentenceLength:
    """
    Track info about the length of a sentence
    """

    min_time: timedelta
    max_time: timedelta

    @staticmethod
    def from_dict(dct: dict) -> SentenceLength:
        """
        Create a SentenceLength object from a dict.

        The dict will not have tuples as __init__ would expect, but rather four keys: 
        * min_unit
        * min_time
        * max_unit
        * max_time
        """
        if isinstance(dct.get("min_time"), timedelta) and isinstance(
            dct.get("max_time"), timedelta
        ):
            return SentenceLength(dct.get("min_time"), dct.get("max_time"))
        else:
            # Parse a sentencelength submitted as a pair of (time, units) tuples, like ("54", "days").
            slength = SentenceLength.from_tuples(
                (str(dct.get("min_time")), dct.get("min_unit")),
                (str(dct.get("max_time")), dct.get("max_unit")),
            )
            return slength

    @staticmethod
    def calculate_days(length: str, unit: str) -> Optional[timedelta]:
        """
        Calculate the number of days represented by the pair `length` and `unit`.

        Sentences are often given in terms like "90 days" or "100 months".
        This method attempts to calculate the number of days that these phrases describe.

        Args:
            length (str): A string that can be converted to an integer
            unit (str): A unit of time, Days, Months, or Years
        """
        if length == "" or str == "":
            return timedelta(days=0)
        if re.match("day", unit.strip(), re.IGNORECASE):
            try:
                return timedelta(days=float(length.strip()))
            except ValueError:
                logger.error(f"Could not parse { length } to int")
                return None
        if re.match("month", unit.strip(), re.IGNORECASE):
            try:
                return timedelta(days=30.42 * float(length.strip()))
            except ValueError:
                logger.error(f"Could not parse { length } to int")
                return None
        if re.match("year", unit.strip(), re.IGNORECASE):
            try:
                return timedelta(days=365 * float(length.strip()))
            except ValueError:
                logger.error(f"Could not parse { length } to int")
                return None
        if unit.strip() != "":
            logger.warning(f"Could not understand unit of time: { unit }")
        return None

    @classmethod
    def from_tuples(cls, min_time: Tuple[str, str], max_time: Tuple[str, str]):
        """
        With two tuples in the form (time-as-string, unit),
        create an object that represents a length of a sentence.
        """
        min_time = SentenceLength.calculate_days(*min_time)
        max_time = SentenceLength.calculate_days(*max_time)
        return cls(min_time=min_time, max_time=max_time)


@dataclass
class Sentence:
    """
    Track information about a sentence. A Charge has zero or more Sentences.
    """

    sentence_date: date
    sentence_type: str
    sentence_period: str
    sentence_length: SentenceLength

    @staticmethod
    def from_dict(dct: dict) -> Sentence:
        dct["sentence_length"] = SentenceLength.from_dict(dct.get("sentence_length"))
        return Sentence(**dct)

    def sentence_complete_date(self):
        try:
            return self.sentence_date + self.sentence_length.max_time
        except:
            return None


@dataclass
class Charge:
    """
    Track information about a charge
    """

    offense: str
    grade: str
    statute: str
    disposition: Optional[str] = None
    disposition_date: Optional[date] = None
    sentences: Optional[List[Sentence]] = None
    # TODO sequence should not be optional.
    sequence: Optional[
        int
    ] = None  # A charge on a docket gets a sequence number. Its like an ID for the charge, within the docket.
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
                if isinstance(charge.sequence, int) and charge.sequence == ch.sequence:
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
            logger.warn("No disposition.")
            return False
        if re.match("^Guilty", self.disposition.strip()):
            return True
        else:
            return False

    def get_statute_chapter(self) -> Optional[float]:
        """ Get the Chapter in the PA Code that this charge is related to. 
        """
        patt = re.compile("^(?P<chapt>\d+)\s*§\s(?P<section>\d+).*")
        match = patt.match(self.statute)
        if match:
            return float(match.group("chapt"))
        else:
            return None

    def get_statute_section(self) -> Optional[float]:
        """ Get the Statute section of the PA code, to which this charge is related.
        """
        patt = re.compile("^(?P<chapt>\d+)\s*§\s(?P<section>\d+\.?\d*).*")
        match = patt.match(self.statute)
        if match:
            return float(match.group("section"))
        else:
            return None

    def get_statute_subsections(self) -> str:
        """ Get the subsection, if any, to which this charge relates
        """
        patt = re.compile(
            "^(?P<chapt>\d+)\s*§\s(?P<section>\d+\.?\d*)\s*§§\s*(?P<subsections>[\(\)A-Za-z0-9\.\*]+)\s*.*"
        )
        match = patt.match(self.statute)
        if match:
            return match.group("subsections")
        else:
            return ""


@dataclass
class Address:

    line_one: str = ""
    city_state_zip: str = ""

    @staticmethod
    def from_dict(dct: dict) -> Address:
        try:
            return Address(**dct)
        except:
            return None

    def __str__(self):
        """ Readable printout of an address. """
        return f"{self.line_one}\n{self.city_state_zip}"
