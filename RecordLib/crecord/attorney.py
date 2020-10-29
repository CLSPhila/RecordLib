from dataclasses import dataclass
from RecordLib.crecord import Address


@dataclass
class Attorney:
    organization: str = ""
    full_name: str = ""
    address: Address = Address()
    organization_phone: str = ""
    bar_id: str = ""

    @staticmethod
    def from_dict(dct):
        dct["address"] = Address.from_dict(dct.get("address"))
        return Attorney(**dct)
