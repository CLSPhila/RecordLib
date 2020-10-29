"""
Simple Rule functions relating to Petition-based sealing.

These rule functions take different inputs and return a Decision that explains whether the inputs meet some sort of condition. 


They return Decisions of the type:

Decision:
    name: str
    value: bool
    reasoning: [Decision] | str

The rules in this module all relate to petition-based sealing..

"""

from __future__ import annotations
from RecordLib.crecord import CRecord, Charge
from typing import Tuple, Union, List, Optional
import copy
import json
import re
from RecordLib.analysis import Decision
from RecordLib.petitions import Sealing
import math
from dateutil.relativedelta import relativedelta
from datetime import date


def no_danger_to_person_offense(
    item: Union[CRecord, Charge],
    within_years: Optional[int] = None,
    penalty_limit: Optional[int] = None,
    conviction_limit: Optional[int] = None,
) -> Decision:
    """
    Individual is not eligible for sealing if they have been convicted within 20 years of an offense
    punishable by imprisonment of seven or more years which is an offense under Article B of Part II.
    
    18 Pa.C.S. 9122.1(b)(2)(A)(I) 


    A charge is not eligible for sealing if it is a conviction for an Article B of Part II (danger to the person)

    The law doesn't include Art. B offenses if the maximum length of imprisonment is less than two years. This
    equates to an M1. So an Art. B offense less serious than an M1 doesn't count as an Offense Against the Person
    under this rule. 


    Args:
        item: A criminal record or a single Charge
        within_years: Person cannot have been convicted of the relevant offense within this number of years..
        penalty_limit: This rule applies to offenses with a sentence equal or greater than this limit.
        conviction_limit: The max number of times a peron can have this conviction before failing the rule.
    """
    # Suppose `item` is a whole Record.
    try:
        cases_within_years = [
            c
            for c in item.cases
            if c.arrest_date
            and relativedelta(date.today(), c.arrest_date).years
            < within_years  # not sure if this needs to be <=
        ]
        decision = Decision(
            name="No convictions in the record for article B offenses, felonies or punishable by more than 7 years, in the last 20 years.",
            reasoning=[
                no_danger_to_person_offense(
                    charge,
                    within_years=within_years,
                    penalty_limit=penalty_limit,
                    conviction_limit=conviction_limit,
                )
                for case in cases_within_years
                for charge in case.charges
            ],
        )
        decision.value = all(decision.reasoning)
    except AttributeError:
        # `item` is probably a charge.
        decision = Decision(
            name="Is this not a conviction for an Article B offense (M1 or more serious)?"
        )
        try:
            if (
                item.get_statute_chapter() == 18
                and item.get_statute_section() > 2300
                and item.get_statute_section() < 3300
                and item.is_conviction()
            ):
                if Charge.grade_GTE(item.grade, "M1"):
                    decision.value = False
                    decision.reasoning = f"Statute {item.statute} is an Article B conviction, with a grade of at least M1."
                elif item.grade.strip() == "":
                    # The grade is missing, and otherwise this is an excluded offense.
                    decision.value = False
                    decision.reasoning = f"Statute {item.statute} is an Article B conviction, but we do not know the grade. It may or may not be an excluded offense."
                else:
                    decison.value = True
                    decison.reasoning = f"Statute {item.statute} appears not to be an Article B conviction."

            else:
                decison.value = True
                decison.reasoning = (
                    f"Statute {item.statute} appears not to be an Article B conviction."
                )
        except:
            decision.value = True
            decision.reasoning = f"Couldn't read the statute {item.statute}, so its probably not Article B."

    return decision


def ten_years_between_convictions(charge, case, crecord, years=10) -> Decision:
    """
    True-valued decision if at least 10 years have passed since the disposition of `charge`, and 
    the next conviction.
    """
    decision = Decision(
        name=f"Has it been 10 years since a conviction for {charge.offense}?"
    )
    if not charge.is_conviction():
        decision.value = True
        decision.reasoning = "This charge was not a conviction."
        return decision
    years_between_convictions = crecord.years_between_convictions(case, charge)
    decision.value = years_between_convictions >= years
    decision.reasoning = f"{years_between_convictions} years elapsed after the conviction for {charge.offense} in {case.docket_number}"
    if bool(decision.value) is False:
        years_remaining = crecord.years_until_n_years_pass_since_last_conviction(10)
        decision.reasoning += f" It looks like enough time between convictions for sealing may pass after {years_remaining}."


def ten_years_since_last_conviction_for_m_or_f(crecord: CRecord) -> Decision:
    """
    Person is not eligible for sealing unless they have been "free from conviction
    for a period of 10 years" 18 Pa C.S. § 9122.1(a). Only convictions for misdemeanors or felonies
    count under this rule. 

    Args:
        crecord: A criminal record

    Returns:
        a Decision indicating if the record has a conviction that's more recent than 10 years.
    """
    decision = Decision(
        name="Has the person been free of conviction for at least 10 years?",
    )
    convictions = [
        case
        for case in crecord.cases
        for charge in case.charges
        if charge.is_conviction() and Charge.grade_GTE(charge.grade, "M3")
    ]
    if len(convictions) == 0:
        decision.value = True
        decision.reasoning = "The person appears to have no convictions."
        return decision

    convictions_with_disposition_dates = [
        c for c in convictions if getattr(c, "disposition_date", None) is not None
    ]

    if len(convictions_with_disposition_dates) == 0:
        decision.value = False
        decision.reasoning = "The disposition dates are missing, so to be safe, we assume it has not been 10 years since the last conviction."
        return decision

    last_conviction = max(
        convictions_with_disposition_dates, key=lambda c: c.disposition_date
    )
    # years_since_last_conviction = min([case.years_passed_disposition() for case in crecord.cases for charge in case.charges if charge.is_conviction()])
    years_since_last_conviction = relativedelta(
        date.today(), last_conviction.disposition_date
    ).years

    decision.reasoning = (
        f"It has been {years_since_last_conviction} years since the last conviction on "
        + f"{last_conviction.disposition_date} in {last_conviction.docket_number}."
    )
    if len(convictions) > len(convictions_with_disposition_dates):
        decision.reasoning += (
            f" But note that there were {len(convictions) - len(convictions_with_disposition_dates)}"
            + " convictions without disposition dates, so our estimate of the last conviction date may be wrong."
        )
    decision.value = years_since_last_conviction > 10

    if decision.value is False:
        decision.reasoning += f" Person may be eligible for sealing in {math.ceil(10 - years_since_last_conviction)} years, if there are no further convictions. "
    return decision


def no_cruelty_to_animals(charge: Charge) -> Decision:
    """
    True-valued decision if the charge is not a conviction for cruelty to animals.
    """
    decision = Decision(name="Is the charge not a conviction for cruelty to animals?")
    decision.value = (
        not charge.is_conviction()
    ) and charge.get_statute_section() != "5533"
    decision.reasoning = f"The charge has disposition of {charge.disposition}, for offense of {charge.statute}"
    return decision


def charge_is_not_excluded_from_sealing(charge: Charge) -> Decision:
    """
    Convictions for certain charges can't be sealed, although they don't disqualify the whole record.
    
    Returns:
        True-valued decision if this charge _is not_ excluded.
    """
    decision = Decision(
        name=f"Is the charge for {charge.offense} excluded from sealing?"
    )
    decision.reasoning = []
    decision.reasoning.append(no_danger_to_person_offense(charge))
    decision.reasoning.append(no_offense_against_family(charge))
    decision.reasoning.append(no_firearms_offense(charge))
    decision.reasoning.append(no_sexual_offense(charge))
    decision.reasoning.append(no_cruelty_to_animals(charge))
    decision.reasoning.append(no_corruption_of_minors_offense(charge))

    decision.value = all(decision.reasoning)
    return decision


def record_contains_no_convictions_excluded_from_sealing(crecord: CRecord) -> Decision:
    """
    True-valued decision if this record does NOT contain any convictions that exclude
    the whole record from sealing.
    
    This is the inverse of `record_contains_convictions_excluded_from_sealing`
    """
    dec = record_contains_convictions_excluded_from_sealing(crecord)
    dec.name = (
        "Is this record free of any convictions that exclude if from autosealing?"
    )
    dec.value = not dec.value
    return dec


def record_contains_convictions_excluded_from_sealing(crecord: CRecord) -> Decision:
    """
    Convictions for certain offenses exclude the entire record from eligibility for sealing.
    
    If decision.value is TRUE, that means the record _does_ contain
    at least one conviction for excluded offenses.
 
    """
    decision = Decision(
        name="Does this record include any convictions for an offense that would bar the whole record from automatic sealing?"
    )
    reasoning = []
    reasoning.append(any_felony_convictions_n_years(crecord, float("inf")))
    reasoning.append(
        more_than_x_convictions_y_grade_z_years(crecord, 2, "M1", float("inf"))
    )
    reasoning.append(
        more_than_x_convictions_y_grade_z_years(crecord, 4, "M", float("inf"))
    )
    reasoning.append(has_indecent_exposure(crecord))
    reasoning.append(has_sexual_intercourse_w_animal(crecord))
    reasoning.append(has_failure_to_register(crecord))
    reasoning.append(has_abuse_of_corpse(crecord))
    reasoning.append(has_paramilitary_training(crecord))

    decision.reasoning = reasoning
    decision.value = any(decision.reasoning)

    return decision


def all_fines_and_costs_paid(crecord: CRecord) -> Decision:
    """
    Explain if all the fines and costs on a list of cases are paid.
    """
    cases = crecord.cases
    decision = Decision(name=f"Are all fines and costs paid for these cases?",)
    decision.reasoning = [fines_and_costs_paid(case) for case in cases]
    decision.value = all(decision.reasoning)
    return decision


def fines_and_costs_paid(case: Case) -> Decision:
    """
    In individual is not eligible for sealing a specific case unless all fines and costs have been paid on that case.

    18 Pa. C.S. § 9122.1(a).

    Args:
        case: a single Case.

    Returns:
        a Decision indicating if all fines and costs have been paid on the case.
    """
    decision = Decision(
        name=f"Fines and costs are all paid on the case {case.docket_number}?",
        reasoning="",
    )
    if case.total_fines is None or case.fines_paid is None:
        if case.total_fines is None:
            decision.value = False
            decision.reasoning += (
                f"Total Fines is undefined, so we're not sure if this case has fines. "
            )

        if case.fines_paid is None:
            decision.value = False
            decision.reasoning += f"Fines paid is undefined, so we're not sure if this case has any fines paid."
        return decision

    decision.value = (case.total_fines - case.fines_paid) <= 0
    decision.reasoning = f"The case's total fines are {case.total_fines}, of which {case.fines_paid} has been paid."
    return decision


def not_felony1(charge: Charge) -> Decision:
    """
    Any F1 graded offense disqualifies a whole record from sealing. 18 PA Code 9122.1(b)(2)(i)

    Returns:
        a True decision if the charge was NOT a felony1 conviction.
    """
    decision = Decision(name="Is the charge an F1 conviction?")
    if charge.grade.strip() == "":
        decision.value = False
        decision.reasoning = (
            "The charge's grade is unknown, so we don't know its *not* an F1."
        )
    elif re.match("F1", charge.grade):
        if charge.is_conviction():
            decision.value = False
            decision.reasoning = "The charge is an F1 conviction"
        else:
            decision.value = True
            decision.reasoning = (
                f"The charge was F1, but the disposition was {charge.disposition}"
            )
    else:
        decision.value = True
        decision.reasoning = f"The charge is {charge.grade}, which is not F1"

    return decision


def not_murder(charge: Charge) -> Decision:
    """
    Checks if a charge was a conviction for murder. 
    
    Returns:
         true if the charge was NOT a murder conviction.

    TODO The Expungement Generator's test is for the statute 18 PaCS 1502. Does the implementation here even work? Need to find real murder convictions to see.
    """
    decision = Decision(name="Is the charge NOT a murder conviction?")
    if charge.is_conviction():
        if re.match("murder", charge.offense, re.IGNORECASE):
            decision.value = False
            decision.reasoning = "The charge was a murder conviction."
        else:
            decision.value = True
            decision.reasoning = "Conviction for something other than murder."
    else:
        decision.value = True
        decision.reasoning = "Not a conviction."
    return decision


def no_f1_convictions(crecord: CRecord) -> Decision:
    """
    Any conviction for Murder, any F1 conviction, or any conviction punishable by imprisonment of 
    more than 20 years disqualifies a record from sealing.

    18 Pa.C.S. 9122.1(b)(2)(i)

    This method only checks for F1 and murder convictions, 
    not for convictions punishable by more than 20 years which are not F1 or murder.

    Returns:
        True if the charge is not a disqualifying conviction.
    """
    decision = Decision(name="No F1 or murder convictions in the record?")
    decision.reasoning = [
        not_felony1(charge) and not_murder(charge)
        for case in crecord.cases
        for charge in case.charges
    ]
    decision.value = all(decision.reasoning)
    return decision


def is_felony_conviction(charge: Charge) -> Decision:
    """
    Was `charge` a felony conviction

    Args:
        charge: A Charge.

    Return:
        A Decision that is True if the charge is a felony conviction.
    """
    decision = Decision(
        name=f"Was the charge [{charge.offense}, {charge.grade}, {charge.disposition}] a felony conviction?"
    )
    decision.reasoning = [
        re.match("F", charge.grade, re.IGNORECASE),
        charge.is_conviction(),
    ]
    decision.value = all(decision.reasoning)
    return decision


def any_felony_convictions_n_years(crecord: CRecord, years: int) -> Decision:
    """
    Were there any felony convictions in the last `years` years?

    Implemented for triaging.

    Args:
        crecord: a Criminal Record.
        years: The threshold number of years to consider

    Return:
        A Decision that is True if there were felony convictions within `years` years.

    """
    decision = Decision(name=f"Were there any felony convictions within {years}")
    decision.reasoning = [
        is_felony_conviction(charge) and case.years_passed_disposition() > years
        for case in crecord.cases
        for charge in case.charges
    ]
    decision.value = all(decision.reasoning)
    return decision


def is_misdemeanor_or_ungraded(charge: Charge) -> Decision:
    """
    Sealing only available for 'qualifying misdemeanor or an ungraded offense which 
    carries a maximum penalty of no more than five years'. Pa.C.S. 9122.1(a).

    This only really checks if the offense was an M or ungraded. It doesn't know the maximum 
    penalty of an offense.

    Returns:
        True if the charge is not a disqualifying conviction.
    """
    decision = Decision(
        name="The offense is a misdemeanor or nongraded offense w/ a penalty of <= 5 years."
    )
    if re.match("^M", charge.grade):
        decision.reasoning = "Charge is a misdemeanor"
        decision.value = True
    elif charge.grade.strip() == "":
        decision.reasoning = "Charge is ungraded. But be careful - we don't know the maximum penalty for the offense."
        decision.value = True
    else:
        decision.reasoning = "Charge is neither a misdemeanor nor ungraded."
        decision.value = False
    return decision


def no_offense_against_family(
    item: Union[CRecord, Charge],
    penalty_limit: Optional[int] = None,
    conviction_limit: Optional[int] = None,
    within_years: Optional[int] = None,
) -> Decision:
    """
    Individuals are ineligible for sealing with certain offenses against the family. (Article D of Part II)

    Individual ineligible after 1 conviction within 20 years of an offense against the family 
    if a felony or if punishable by seven or more years.  18 Pa.C.S. 9122.1(b)(2)(A).

    Individuals ineligible after 2 convictions within 15 years of an offense against the family 
    if a felony or punishable by more than 2 years. 18 Pa.C.S. 9122.1(b)(3)(ii)(B)

    Returns:
        True if the charge was NOT a disqualifying offense, or if the record does NOT contain any 
        disqulifying offenses.
    """
    # Presume a Charge
    try:
        decision = Decision(
            name=f"Charge for {item.statute} is not an offense against the family.",
            reasoning=[
                item.is_conviction(),
                item.get_statute_chapter() == 18,
                item.get_statute_section() > 4300,
                item.get_statute_section() < 4500,
            ],
        )
        decision.value = not all(decision.reasoning)
    except TypeError:
        # `item`'s get_statute functions returned something that doesn't have < > defined, such as None.
        decision = Decision(
            name=f"Charge for {item.statute} is not an offense against the family.",
            reasoning="The statute doesn't appear to be one of the Article D offense statutes.",
            value=True,
        )
    except AttributeError:
        # `item` may be a whole record.
        decision = Decision(
            name=(
                f"Not convicted within {within_years} more than {conviction_limit} times "
                + f"of felony or offense punishable by {penalty_limit} years."
            ),
            # reasoning should be a list of charges w/in 20 years where no_offense_fam(charge) is False
            reasoning=[
                no_offense_against_family(
                    charge,
                    penalty_limit=penalty_limit,
                    conviction_limit=conviction_limit,
                    within_years=within_years,
                )
                for case in item.cases
                for charge in case.charges
                if case.years_passed_disposition() <= within_years
            ],
        )
        decision.value = (
            len(list(filter(lambda d: bool(d) is False, decision.reasoning)))
            < conviction_limit
        )
    return decision


def no_firearms_offense(
    item: Union[CRecord, Charge],
    penalty_limit: Optional[int] = None,
    conviction_limit: Optional[int] = None,
    within_years: Optional[int] = None,
) -> Decision:
    """
    No disqualifying convictions for firearms offenses. (Chapter 61 offenses) 
    
    No sealing conviction if punishable by more than two years for Chapter 61 (firearms) offenses. 
    18 Pa.C.S. 9122.1(b)(1)(iii)

    No sealing record if contains any conviction ithin 20 years for a felony or offense 
    punishable >= 7 years for Chapter 61 offenses. 18 Pa.C.S. 9122.1(b)(2)(ii)(A)(II)

    Returns:
        True if the charge was NOT a disqualifying offense, or if the record does NOT contain any 
        disqulifying offenses.
 
    """
    # assume item is a charge.
    try:
        decision = Decision(
            name=f"Charge for {item.statute} is not a firearms offense.",
            reasoning=[
                item.get_statute_chapter() == 18,
                item.get_statute_section() > 6100,
                item.get_statute_section() < 6200,
            ],
        )
        decision.value = not all(decision.reasoning)
    except TypeError:
        # `item`'s get_statute functions returned something that doesn't have < > defined, such as None.
        decision = Decision(
            name=f"Charge for {item.statute} is not a Chapter 61 firearms offense.",
            reasoning="The statute doesn't appear to be one of the Article D offense statutes.",
            value=True,
        )
    except AttributeError:
        # `item` may be a whole record.
        decision = Decision(
            name=(
                f"Not convicted within {within_years} more than {conviction_limit} times "
                + f"of felony or offense punishable by {penalty_limit} years."
            ),
            # reasoning should be a list of charges w/in 20 years where no_offense_fam(charge) is False
            reasoning=[
                no_firearms_offense(
                    charge,
                    penalty_limit=penalty_limit,
                    conviction_limit=conviction_limit,
                    within_years=within_years,
                )
                for case in item.cases
                for charge in case.charges
                if case.years_passed_disposition() <= within_years
            ],
        )
        decision.value = (
            len(list(filter(lambda d: bool(d) is False, decision.reasoning)))
            < conviction_limit
        )
    return decision


def no_sexual_offense(
    item: Union[CRecord, Charge],
    penalty_limit: Optional[int] = None,
    conviction_limit: Optional[int] = None,
    within_years: Optional[int] = None,
) -> Decision:
    """
    No disqualifying convictions for sexual offenses.

    No sealing a conviction if it was punishable by more than two years for offenses under 
    42 Pa.C.S. §§ 9799.14 (relating to sexual offenses and tier system) and 
    9799.55 (relating to registration). 18 Pa.C.S. 9122.1(b)(1)(iv)

    No sealing a record if it contains any conviction within 20 years for a felony or 
    offense punishable >= 7 years, for offenses under 42 Pa.C.S. §§ 9799.14 (relating to sexual 
    offenses and tier system) and 9799.55 (relating to registration). 18 PaCS 9122.1(b)(2)(ii)(A)(IV)

    Returns:
        True if the charge was NOT a disqualifying offense, or if the record does NOT contain any 
        disqulifying offenses.
    """
    # 18 Pa.C.S. 9799.14 and 9799.55 relate to quite a few other offenses.
    tiered_sex_offenses = [
        "2901a.1",
        "2902b",
        "2903b",
        "2904",
        "2910b",
        "3011b",
        "3121",
        "3122.1b",
        "3123",
        "3124.1",
        "3124.2a",
        "3124.2a.1",
        "3124.2a2",
        "3124.2a3",
        "3125",
        "3126a1",
        "3126a2",
        "3126a3",
        "3126a4",
        "3126a5",
        "3126a6",
        "3126a7",
        "3126a8",
        "4302b",
        "5902b",
        "5902b.1",
        "5903a3ii",
        "5903a4ii",
        "5903a5ii",
        "5903a6",
        "6301a1ii",
        "6312",
        "6318",
        "6320",
        "7507.1",
    ]
    # presume item is a Charge
    try:
        decision = Decision(
            name="This charge is not a disqualifying sexual or registration offense?"
        )
        patt = re.compile(
            r"^(?P<chapt>\d+)\s*§\s(?P<section>\d+\.?\d*)\s*(?P<subsections>[\(\)A-Za-z0-9\.]+).*"
        )
        matches = patt.match(item.statute)
        if not matches:
            decision.reasoning = (
                "This doesn't appear to be one of the tiered sex offense statutes."
            )
            decision.value = True
        else:
            this_offense = matches.group("section") + matches.group(
                "subsections"
            ).replace("(", "").replace(")", "")
            decision.reasoning = [
                item.is_conviction(),
                item.get_statute_chapter() == 18,
                this_offense in tiered_sex_offenses,
            ]
            decision.value = not all(decision.reasoning)
    except AttributeError:
        # item is a CRecord
        decision = Decision(
            name=(
                f"Not convicted more than {conviction_limit} times, within {within_years} years,"
                + f"of certain sexual or registration-related offenses punishable by {penalty_limit} years"
            ),
            reasoning=[
                no_sexual_offense(
                    charge,
                    penalty_limit=penalty_limit,
                    conviction_limit=conviction_limit,
                    within_years=within_years,
                )
                for case in item.cases
                for charge in case.charges
                if case.years_passed_disposition() <= within_years
            ],
        )
        decision.value = (
            len(list(filter(lambda d: bool(d) is False, decision.reasoning)))
            < conviction_limit
        )
    return decision


def no_corruption_of_minors_offense(
    charge: Charge,
    penalty_limit: Optional[int] = None,
    conviction_limit: Optional[int] = None,
    within_years: Optional[int] = None,
) -> Decision:
    """
    No disqualifying convictions for corruption of minors.

    No sealing a conviction if it was punishable by more than two years for offenses under 
    section 6301(a)(1), corruption of minors. 18 Pa.C.S. 9122.1(b)(1)(v)

    Returns:
        a True Decision if the charge was NOT a disqualifying offense. Otherwise a False Decision.
    """
    decision = Decision(
        name="This charge is not a disqualifying corruption of minors offense?"
    )
    patt = re.compile(
        r"^(?P<chapt>\d+)\s*§\s(?P<section>\d+\.?\d*)\s*(?P<subsections>[\(\)A-Za-z0-9\.]+).*"
    )
    matches = patt.match(charge.statute)
    if not matches:
        decision.reasoning = (
            "This doesn't appear to be one of the tiered sex offense statutes."
        )
        decision.value = True
    else:
        this_offense = matches.group("section") + matches.group("subsections").replace(
            "(", ""
        ).replace(")", "")
        decision.reasoning = [
            charge.is_conviction(),
            charge.get_statute_chapter() == 18,
            this_offense == "6301a1",
        ]
        decision.value = not all(decision.reasoning)
    return decision


def more_than_x_convictions_y_grade_z_years(
    crecord: CRecord, offense_limit: int, grade_limit: str, years: int
) -> Decision:
    """
    Does `crecord` contain equal or more than `offense_limit` convictions for `grade_limit` (or more serious) offenses in the last `years` years?

    The limits are inclusive.

    For example, `more_than_x_convictions_y_grade_z_years(rec, 2, M1, 15)` would return a Decision that explains whether `rec` contains 
    2 or more M1-or-greater convictions in the last 15 years.

    Args:
        crecord: A criminal record.
        offense_limit: Are there more convictions than this number in this record?
        grade_limit: The grade (i.e. M1) that triggers this rule
        years: Years since a conviction that will be counted.
    
    Returns:
        A decision that is True if `crecord` contains more than the `offense_limit` of `grade_limit` convictions in the last `years` years.
    """
    decision = Decision(
        name=f"Does {crecord.person.full_name()}'s record contain {offense_limit} or more convictions, graded {grade_limit} or higher, within the last {years} years?"
    )
    qualifying_charges = []
    for case in crecord.cases:
        for charge in case.charges:
            if (
                case.years_passed_disposition() >= years
                and charge.is_conviction()
                and Charge.grade_GTE(charge.grade, grade_limit)
            ):
                qualifying_charges.append(charge)
    decision.reasoning = qualifying_charges
    decision.value = len(qualifying_charges) >= offense_limit
    return decision


def offenses_punishable_by_two_or_more_years(
    crecord: CRecord, conviction_limit: int, within_years: int
) -> Decision:
    """
    Not too many convictions for offenses punishable by two or more years.
    
    No sealing a record if it has four or more offenses punishable by two or more years within 20 years. 
    18 PaCS 9122.1(b)(2)(ii)(B)
    
    No sealing a record if it has two or more offenses punishable by more than two years in prison within
    15 years.. 18 PaCS 9122.1(b)(2)(iii)(A)

    The Expungement Generator uses the charge grade as a proxy for this. See Charge.php:284.

    So will RecordLib.

    Returns:
        A Decision we'll call `d`. `bool(d)` is True if there were no offenses punishable by more than 
        two years in `crecord`.

    """
    # Grades that approximately the grades of offenses that also have penalty's of two or more years.
    proxy_grades = ["F1", "F2", "F3", "F", "M1", "M2"]
    decision = Decision(
        name=f"The record has no more than {conviction_limit} convictions for offenses punishable by two or more years in the last {within_years} years.",
        reasoning=[
            charge
            for case in crecord.cases
            for charge in case.charges
            if (
                charge.is_conviction()
                and (charge.grade in proxy_grades)
                and case.years_passed_disposition() < within_years
            )
        ],
    )
    decision.value = len(decision.reasoning) < conviction_limit

    return decision


def has_indecent_exposure(crecord) -> Decision:
    """
    Decision that is true-valued if a crecord has any conviction for indecent exposure.
    """
    dec = no_indecent_exposure(crecord, conviction_limit=1)
    dec.name = "Does this record have any convictions for indecent exposure?"
    dec.value = not dec.value
    return dec.value


def no_indecent_exposure(
    crecord, conviction_limit: int, within_years: int = 15
) -> Decision:
    """
    Cannot seal if record contains conviction for indecent exposure within 15 years.
    18 PaCS 9122.1(b)(2)(iii)(B)(I)
    
    Returns:
        A Decision we'll call `d`. `bool(d)` is True if there were no indecent exposure 
        offenses in `crecord`.

    """
    decision = Decision(
        name="No indecent exposure convictions in this record.",
        reasoning=[
            charge
            for case in crecord.cases
            for charge in case.charges
            if (
                case.years_passed_disposition() < within_years
                and charge.is_conviction()
                and charge.get_statute_chapter() == 18
                and charge.get_statute_section() == 3127
            )
        ],
    )
    decision.value = True if len(decision.reasoning) < conviction_limit else False
    return decision


def has_sexual_intercourse_w_animal(crecord):
    """
    True-valued decision if crecord has any convictions for violation of 
    18 Pa CS 3129.
    """
    dec = no_sexual_intercourse_w_animal(crecord, 1, float("inf"))
    dec.name = "Does the record have any conviction for intercourse with an animal?"
    dec.value = not dec.value
    return dec


def no_sexual_intercourse_w_animal(
    crecord: CRecord, conviction_limit: int, within_years: int = 15
) -> Decision:
    """
    Cannot seal if record contains conviction for intercourse w/ animal within 15 years.

    18 PA.C.S. 9122.1(b)(2)(iii)(B)(II)
    
    Returns:
        Decision that is True if there were no sexual intercourse w/ animal convictions in the record.  
    """
    decision = Decision(
        name="No intercourse with animals convictions in this record.",
        reasoning=[
            charge
            for case in crecord.cases
            for charge in case.charges
            if (
                case.years_passed_disposition() < within_years
                and charge.is_conviction()
                and charge.get_statute_chapter() == 18
                and charge.get_statute_section() == 3129
            )
        ],
    )
    decision.value = True if len(decision.reasoning) < conviction_limit else False
    return decision


def has_failure_to_register(crecord):
    """
    True-valued Decision if record contains any conviction for failure
    to register.
    """
    dec = no_failure_to_register(crecord, conviction_limit=1)
    dec.name = "Does the record have any convictions for failure to register?"
    dec.value = not dec.value
    return dec


def no_failure_to_register(
    item: Option[CRecord, Charge],
    conviction_limit: Optional[int] = None,
    within_years: Optional[int] = 15,
) -> Decision:
    """
    Cannot seal if record contains conviction for failure to register within 15 years.

    18 PA.C.S. 9122.1(b)(2)(iii)(B)(III)


    TODO the reasoning here doesn't return a readable set of Decisions.

    Returns:
        a Decision that is True if there were no failure-to-register offenses in the record.
    """
    # A Crecord
    try:
        decision = Decision(
            name="No failure-to-register convictions in this record.",
            reasoning=[
                charge
                for case in item.cases  # if item is a charge, this will throw exception.
                for charge in case.charges
                if (
                    (case.years_passed_disposition() < within_years)
                    and not no_failure_to_register(charge)
                )
            ],
        )
        decision.value = True if len(decision.reasoning) < conviction_limit else False
        return decision
    # item is A Charge
    except Exception as err:
        decision = Decision(name="This charge is not a failure-to-register conviction")
        decision.value = not (
            item.is_conviction()
            and item.get_statute_chapter() == 18
            and (
                item.get_statute_section() == 4915.1
                or item.get_statute_section() == 4915.2
            )
        )
        if not item.is_conviction():
            decision.reasoning = "Charge is not a conviction."
        elif decision.value:
            decision.reasoning = (
                f"Charge for {item.statute} is not a failure-to-register conviction."
            )
        else:
            decision.reasoning = (
                f"Charge for {item.statute} is a failure-to-register conviction."
            )
        return decision


def has_weapons_of_escape(crecord):
    """
    True-valued decision if record contains any convictions for a weapon of escape.
    """
    dec = no_weapons_of_escape(credits, 1, float("inf"))
    dec.name = "Does the record have any convictions for a weapon of escape."
    dec.value = not dec.value
    return dec


def no_weapons_of_escape(
    crecord: CRecord, conviction_limit: int, within_years: int = 15
) -> Decision:
    """
    Cannot seal if record contains conviction for possession of implement or weapon of escape within 15 years.

    18 PA.C.S. 9122.1(b)(2)(iii)(B)(IV)
    """
    decision = Decision(
        name="No possion-of-implement-of-escape convictions in this record.",
        reasoning=[
            charge
            for case in crecord.cases
            for charge in case.charges
            if (
                case.years_passed_disposition() < within_years
                and charge.is_conviction()
                and charge.get_statute_chapter() == 18
                and charge.get_statute_section() == 5122
            )
        ],
    )
    decision.value = True if len(decision.reasoning) < conviction_limit else False
    return decision


def has_abuse_of_corpse(crecord):
    """
    True-valued decision if crecord has any convictions for abuse of a corpse.
    """
    dec = no_abuse_of_corpse(crecord, 1, float("inf"))
    dec.name = "Does record contain any convictions for abuse of a corpse?"
    dec.value = not dec.value
    return dec


def no_abuse_of_corpse(
    crecord: CRecord, conviction_limit: int, within_years: int = 15
) -> Decision:
    """
    Cannot seal if record contains conviction for abuse of corpse within 15 years.

    18 PA.C.S. 9122.1(b)(2)(iii)(B)(V)
    """
    decision = Decision(
        name="No abuse of corpse convictions in this record.",
        reasoning=[
            charge
            for case in crecord.cases
            for charge in case.charges
            if (
                case.years_passed_disposition() < within_years
                and charge.is_conviction()
                and charge.get_statute_chapter() == 18
                and charge.get_statute_section() == 5510
            )
        ],
    )
    decision.value = True if len(decision.reasoning) < conviction_limit else False
    return decision


def has_paramilitary_training(crecord):
    """
    True valued Decision if record contains convictions for paramilitary
    training.
    """
    dec = no_paramilitary_training(crecord, 1, float("inf"))
    dec.name = "Does the record contain any convictions for paramilitary training?"
    dec.value = not dec.value
    return dec


def no_paramilitary_training(
    crecord: CRecord, conviction_limit: int, within_years: int = 15
) -> Decision:
    """
    Cannot seal if record contains conviction for paramilitary training within 15 years.

    18 PA.C.S. 9122.1(b)(2)(iii)(B)(VI)
    """
    decision = Decision(
        name="No paramilitary training offenses in this record.",
        reasoning=[
            charge
            for case in crecord.cases
            for charge in case.charges
            if (
                case.years_passed_disposition() < within_years
                and charge.is_conviction()
                and charge.get_statute_chapter() == 18
                and charge.get_statute_section() == 5515
            )
        ],
    )
    decision.value = True if len(decision.reasoning) < conviction_limit else False
    return decision


def full_record_requirements_for_petition_sealing(crecord: CRecord) -> Decision:
    """
    To seal a case or charge by petition, there are requirements that the record as a whole must satisfy. 

    This function makes the Decisions that evaluate whether the record meets these requirements. 
    """
    decision = Decision(name="Sealing requirements that relate to the whole record.")
    decision.reasoning = [
        ten_years_since_last_conviction_for_m_or_f(crecord),  # 18 Pa.C.S. 9122.1(a)
        # fines_and_costs_paid(crecord),  # 18 Pa.C.S. 9122.1(a)
        no_f1_convictions(crecord),  # 18 Pa.C.S. 9122.1(b)(2)(i)
        no_danger_to_person_offense(
            crecord, penalty_limit=7, conviction_limit=1, within_years=20
        ),
        no_offense_against_family(
            crecord, penalty_limit=7, conviction_limit=1, within_years=20
        ),
        no_firearms_offense(
            crecord, penalty_limit=7, conviction_limit=1, within_years=20
        ),
        no_sexual_offense(
            crecord, penalty_limit=7, conviction_limit=1, within_years=20
        ),
        offenses_punishable_by_two_or_more_years(
            crecord, conviction_limit=4, within_years=20
        ),
        offenses_punishable_by_two_or_more_years(
            crecord, conviction_limit=2, within_years=15
        ),
        no_indecent_exposure(crecord, conviction_limit=1, within_years=15),
        no_sexual_intercourse_w_animal(crecord, conviction_limit=1, within_years=15),
        no_failure_to_register(crecord, conviction_limit=1, within_years=15),
        no_weapons_of_escape(crecord, conviction_limit=1, within_years=15),
        no_abuse_of_corpse(crecord, conviction_limit=1, within_years=15),
        no_paramilitary_training(crecord, conviction_limit=1, within_years=15),
    ]
    decision.value = all(decision.reasoning)
    return decision


def petition_sealing_for_single_case(case: Case) -> Decision:
    """
    Make a decision about whether a specific case is sealable by petition.

    This function doesn't know about whether the whole record meets the full record requirements. 

    The function `slices` the input Case. It returns a SliceDecision, where the `value` is a 2-Tuple. The left side of the tuple
    holds parts of the case that can't be sealed, and the right side holds parts of the tuple that can be sealed.

    If you have a SliceDecision from this function, as in `sd = petition_sealing_for_single_case(case)`,
    and you want to know "is that case sealable at all?", you'd ask `sd.value[1] is None`. If that is `False`, 
    then there is some sealable charge or charges. 
    """
    case_decision = Decision(name=f"Sealing case {case.docket_number}", reasoning=[])
    fines_decision = fines_and_costs_paid(case)  # 18 Pa.C.S. 9122.1(a)
    case_decision.reasoning.append(fines_decision)
    # create copies of a case that don't include any charges.
    # sealable or unsealable charges will be added to these.
    sealable_parts_of_case = case.partialcopy()
    unsealable_parts_of_case = case.partialcopy()

    # Iterate over the charges in a case, to see which charges are sealable.
    charge_decisions = []
    for charge in case.charges:
        # The sealability of each charge is its own Decision.
        charge_decision = petition_sealing_for_single_charge(charge)
        charge_decisions.append(charge_decision)
        if bool(charge_decision) is True:
            sealable_parts_of_case.charges.append(charge)
        else:
            unsealable_parts_of_case.charges.append(charge)

    case_decision.value = (
        unsealable_parts_of_case if len(unsealable_parts_of_case.charges) > 0 else None,
        sealable_parts_of_case if len(sealable_parts_of_case.charges) > 0 else None,
    )

    case_decision.reasoning.extend(charge_decisions)
    return case_decision


def petition_sealing_for_single_charge(charge: Charge):
    """
    Decide whether a single charge is sealable.

    TODO `petition_sealing_for_single_charge` calls functions to check statutory exclusions, with values for 'penalty_limit' and so on, that seem like they shouldn't be relevant here?

    """
    charge_decision = Decision(name=f"Sealing charge {charge.offense}")
    # Conditions that determine whether this charge is sealable
    #  See 91 Pa.C.S. 9122.1(b)(1)
    charge_decision.reasoning = [
        is_misdemeanor_or_ungraded(charge),
        no_danger_to_person_offense(
            charge, penalty_limit=2, conviction_limit=1, within_years=float("Inf"),
        ),
        no_offense_against_family(
            charge, penalty_limit=2, conviction_limit=1, within_years=float("Inf"),
        ),
        no_firearms_offense(
            charge, penalty_limit=2, conviction_limit=1, within_years=float("Inf"),
        ),
        no_sexual_offense(
            charge, penalty_limit=2, conviction_limit=1, within_years=float("Inf"),
        ),
        no_corruption_of_minors_offense(
            charge, penalty_limit=2, conviction_limit=1, within_years=float("Inf"),
        ),
    ]
    charge_decision.value = all(charge_decision.reasoning)
    return charge_decision


def cannot_autoseal_m1_or_f(charge: Charge):
    """
    Autosealing is never possible for M1 or F convictions.

    This method assumes the charge is a conviction.
    
    """
    dec = Decision(name="Is the conviction less serious than an M1 or F?",)

    if charge.grade is None:
        dec.value = False
        dec.reasoning = (
            "Grade information is missing, so we cannot determine eligibility."
        )
        return dec

    val = not Charge.grade_GTE(charge.grade, "M1")
    dec.value = val
    less_or_more = "less" if val else "more"
    dec.reasoning = (
        f"The grade {charge.grade} is {less_or_more} serious than an M1 or F."
    )

    return dec


def no_m1_or_higher_in_this_case(case: Case) -> Decision:
    """
    True-valued decision if the case has no convictions graded m1 or more severe.
    """
    decision = Decision(
        name="Are there any convictions for M1 or more severe offenses in this case?"
    )
    serious_charges = [
        c for c in case.charges if c.is_conviction() and Charge.grade_GTE(c.grade, "M1")
    ]
    decision.value = False if len(serious_charges) > 0 else True
    decision.reasoning = f"There are {len(serious_charges)} charges graded M1 or more severe in the case {case.docket_number}."
    return decision
