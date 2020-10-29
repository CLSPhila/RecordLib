"""
Common, simple dataclasses live here.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Optional
from datetime import date, timedelta
import re
import logging

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
