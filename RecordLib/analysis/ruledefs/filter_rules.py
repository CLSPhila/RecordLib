from typing import Tuple
import copy
from RecordLib.analysis.decision import Decision, FilterDecision
from RecordLib.analysis.ruledefs import simple_sealing_rules as ssr
from RecordLib.crecord import CRecord, Case, Charge


def is_traffic_case(case: Case) -> Decision:
    """
    True-valued Decision if the Case is a traffic case.
    """
    decision = Decision(name=f"Is {case.docket_number} a traffic case?")
    decision.value = "TR" in case.docket_number
    decision.reasoning = (
        f"The case is {('not ') if not decision.value else ('')}a traffic case"
    )
    return decision


def filter_traffic_cases(crecord: CRecord) -> Tuple[CRecord, FilterDecision]:
    """
    We'll often want to exclude traffic court cases from analysis, because the expungement process is 
    more difficult than non-traffic cases.
    """
    decision = FilterDecision(
        name="Traffic Court cases removed from consideration.", value=[], reasoning=[]
    )
    modified_record = CRecord(person=crecord.person, cases=[])
    for case in crecord.cases:
        case_is_traffic_case = is_traffic_case(case)
        decision.reasoning.append(case_is_traffic_case)
        if not case_is_traffic_case:
            # If the case is not a traffic case, send it along to the next rule for processing.
            modified_record.cases.append(case)
        else:
            # If the is a traffic case, don't pass it along, but note that this rule collected it.
            decision.value.append(case)
    return modified_record, decision
