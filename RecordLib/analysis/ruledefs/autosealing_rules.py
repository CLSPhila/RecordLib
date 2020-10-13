from RecordLib.analysis.decision import (
    Decision,
    PetitionDecision,
    RecordEligibilityDecision,
)
from RecordLib.analysis.ruledefs import simple_sealing_rules as ssr
from RecordLib.crecord import CRecord


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
            Its 'reasoning' is a list with a Decision for each Charge.
    """
    decision = RecordEligibilityDecision(
        name="Eligibility for Automated Sealing", value={}, reasoning={}
    )

    has_had_10_years_free_of_m_or_f_convictions = ssr.ten_years_since_last_conviction_for_m_or_f(
        crecord
    )
    no_outstanding_fines_costs = fines_costs_paid()
    record_not_excluded = does_crecord_have_excluded_convictions(crecord)
    for case in crecord.cases:

        for charge in case.charges:
            charge_is_sealable = is_nonconviction(charge) or (
                (no_outstanding_fines_costs and is_summary_conviction(charge))
                or (
                    grade_is_between("M", "M2", charge.grade)
                    and has_had_10_years_free_of_m_or_f_convictions
                    and no_outstanding_fines_costs
                    and not_excluded_offense(charge)
                    and no_m1_or_worse_in_this_case(case)
                    and record_not_excluded
                )
            )

    return decision
