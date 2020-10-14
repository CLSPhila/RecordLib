from typing import Tuple
from RecordLib.analysis.decision import (
    Decision,
    PetitionDecision,
    RecordEligibilityDecision,
)

from RecordLib.analysis.ruledefs import simple_sealing_rules as ssr
from RecordLib.crecord import CRecord, Case, Charge


def is_charge_autosealable(
    charge: Charge,
    case: Case,
    crecord: CRecord,
    no_outstanding_fines_costs: Decision,
    record_not_excluded: Decision,
):
    """
    Decision explaining if a given charge is autosealable

    True-valued if the charge is auto-sealable.

    Args:
        charge: The charge we're considering sealing.
        case: the case the charge comes from.
        crecord: the whole record the charge comes from.
        no_outstanding_fines_costs: A pre-computed Decision explaining if the record contains no outstanding fines or costs.
        record_not_excluded: Pre-computed decision explaining if the record contains disqualifying convictions.

    """
    dec = Decision(
        f"Is the charge for '{charge.offense}' in {case.docket_number} auto-sealable?"
    )
    dec.reasoning = []
    dec.reasoning.append(
        Decision(
            name="Is this a conviction?",
            value=charge.is_conviction(),
            reasoning=f"{charge.disposition} is {'not' if not charge.is_conviction() else ''} a conviction.",
        )
    )

    dec.reasoning.append(ssr.ten_years_between_convictions(charge, case, crecord))
    dec.reasoning.append(no_outstanding_fines_costs)
    dec.reasoning.append(ssr.charge_is_not_excluded_from_sealing(charge))
    dec.reasoning.append(ssr.no_m1_or_higher_in_this_case(case))
    dec.reasoning.append(record_not_excluded)

    dec.value = all(dec.reasoning)
    return dec


def autosealing_eligibility(
    crecord: CRecord,
) -> Tuple[CRecord, RecordEligibilityDecision]:
    """
    Determine the eligibility for autsealing of the charges in a CRecord.
    
    Args:
        crecord (CRecord): A person's criminal record.

    Returns:
        The original Crecord analyzed (this rule does not filter out sealing-eligible charges.)
        A RecordEligibilityDecision that explains what is sealable and why. 
            Its 'value' is a dict like {eligible: [Case[Charge]], ineligible: [Case[Charge]]}
            Its 'reasoning' is a dict. Keys are case docket numbers, and the values are each a 
                list with a Decision for each Charge on a Case.
    """
    decision = RecordEligibilityDecision(
        name="Eligibility for Automated Sealing",
        value={"eligible": [], "ineligible": []},
        reasoning={},
    )

    # I don't think this is actually a requirement. The rule is there must be 10 years between
    # convictions for the earlier one to be sealed.
    # has_had_10_years_free_of_m_or_f_convictions = ssr.ten_years_since_last_conviction_for_m_or_f(
    #    crecord
    # )
    no_outstanding_fines_costs = ssr.all_fines_and_costs_paid(crecord)
    record_not_excluded = ssr.record_contains_no_convictions_excluded_from_sealing(
        crecord
    )
    for case in crecord.cases:
        sealable_case = case.partialcopy()
        unsealable_case = case.partialcopy()
        decision.reasoning[case.docket_number] = []

        for charge in case.charges:
            charge_is_sealable = is_charge_autosealable(
                charge, case, crecord, no_outstanding_fines_costs, record_not_excluded
            )
            decision.reasoning[case.docket_number].append(charge_is_sealable)
            if bool(charge_is_sealable):
                sealable_case.charges.append(charge)
            else:
                unsealable_case.charges.append(charge)

        if len(sealable_case.charges) > 0:
            decision.value["eligible"].append(sealable_case)
        if len(unsealable_case.charges) > 0:
            decision.value["ineligible"].append(unsealable_case)
    return crecord, decision
