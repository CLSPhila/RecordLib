from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from datetime import date
import logging
from dateutil.relativedelta import relativedelta
from RecordLib.crecord import Address
from RecordLib.crecord.helpers import convert_datestring

logger = logging.getLogger(__name__)


@dataclass
class Person:
    """
    Track information about a person.
    """

    first_name: str
    last_name: str
    date_of_birth: date
    aliases: List[str] = None
    date_of_death: Optional[date] = None
    ssn: Optional[str] = None
    address: Optional[Address] = None

    @staticmethod
    def from_dict(dct: dict) -> Person:
        """ Create a Person from a dict describing one. """
        if dct is not None:
            return Person(
                first_name=dct.get("first_name"),
                last_name=dct.get("last_name"),
                date_of_birth=convert_datestring(dct.get("date_of_birth")),
                date_of_death=convert_datestring(dct.get("date_of_death")),
                aliases=[val for val in dct.get("aliases") if val is not None]
                if dct.get("aliases") is not None
                else [],
                ssn=dct.get("ssn"),
                address=Address.from_dict(dct.get("address")),
            )

    def age(self) -> int:
        """ Age in years """
        if self.date_of_birth is None:
            return 0
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def years_dead(self) -> float:
        """Return number of years dead a person is. Or -Infinity, if alive.
        """
        if self.date_of_death:
            return relativedelta(date.today(), self.date_of_death).years
        else:
            return float("-Inf")

    def full_name(self) -> str:
        return " ".join([self.first_name, self.last_name])
