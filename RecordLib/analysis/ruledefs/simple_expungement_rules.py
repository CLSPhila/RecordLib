"""
Simple Rule functions relating to Expungements.

18 Pa.C.S. 9122 deals with Expungements
https://www.legis.state.pa.us/cfdocs/legis/LI/consCheck.cfm?txtType=HTM&ttl=18&div=0&chpt=91


These rule functions take different inputs and return a Decision that explains whether the inputs meet some sort of condition. 


They return Decisions of the type:

Decision:
    name: str
    value: bool
    reasoning: [Decision] | str

The rules in this module all relate to expungemnts.

"""
from RecordLib.crecord import CRecord, Charge, Person
from RecordLib.analysis import Decision


def is_over_age(person: Person, age_limit: int) -> Decision:
    return Decision(
        name=f"Is {person.first_name} over {age_limit}?",
        value=person.age() > age_limit,
        reasoning=f"{person.first_name} is {person.age()}",
    )


def years_since_last_contact(crec: CRecord, year_min: int) -> Decision:
    return Decision(
        name=f"Has {crec.person.first_name} been free of arrest or prosecution for {year_min} years?",
        value=crec.years_since_last_arrested_or_prosecuted() >= 10,
        reasoning=f"It has been {crec.years_since_last_arrested_or_prosecuted()} years.",
    )


def years_since_final_release(crec: CRecord, year_min: int) -> Decision:
    return Decision(
        name=f"Has it been at least {year_min} years since {crec.person.first_name}'s final release from custody?",
        value=crec.years_since_final_release() > year_min,
        reasoning=f"It has been {crec.years_since_final_release()}.",
    )


def arrest_free_for_n_years(crec: CRecord, year_min=5) -> Decision:
    return Decision(
        name=f"Has {crec.person.first_name} been arrest free and prosecution free for five years?",
        value=crec.years_since_last_arrested_or_prosecuted() > year_min,
        reasoning=f"It has been {crec.years_since_last_arrested_or_prosecuted()} since the last arrest or prosecection.",
    )


def is_summary(charge: Charge) -> Decision:
    return Decision(
        name=f"Is this charge for {charge.offense} a summary?",
        value=charge.grade.strip() == "S",
        reasoning=f"The charge's grade is {charge.grade.strip()}",
    )


def is_conviction(charge: Charge) -> Decision:

    if charge.disposition is None or charge.disposition.strip() == "":
        return Decision(
            name=f"Is this charge for {charge.offense} a conviction?",
            value=None,
            reasoning="The charge is missing a disposition, so this case may not be closed (it may have simply been transferred).",
        )
    return Decision(
        name=f"Is this charge for {charge.offense} a conviction?",
        value=charge.is_conviction(),
        reasoning=f"The charge's disposition {charge.disposition} indicates a conviction"
        if charge.is_conviction()
        else f"The charge's disposition {charge.disposition} indicates its not a conviction.",
    )


def is_summary_conviction(charge: Charge) -> Decision:
    charge_d = Decision(
        name=f"Is this charge for {charge.offense} a summary conviction?",
        reasoning=[is_summary(charge), is_conviction(charge)],
    )
    charge_d.value = all(charge_d.reasoning)
    return charge_d

