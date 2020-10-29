from __future__ import annotations
from dataclasses import dataclass


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
