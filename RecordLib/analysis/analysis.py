from __future__ import annotations
from typing import Callable, Optional, Tuple, List
import copy
import re
from collections import OrderedDict
import logging
from RecordLib.analysis import Decision, WaitDecision

logger = logging.getLogger(__name__)


class Analysis:
    """
    The Analysis object structures the process of figuring out what can be sealed and expunged from a criminal record. 
    It also helps answer questions about why parts of a criminal record can't be expunged. 

    You initialize an Analysis with a CRecord (which represents someone's criminal record). 
    
    Next, you repeatedly call rule functions on the analysis, using the Analysis.rule method. 
    
    Each rule function evaluates whether certain cases or charges can be sealed or expunged under certain conditions. 
    The rule function separates the cases/charges that meet the rule's conditions from the cases/charges that don't. 

    A CRecord looks like:
        Person
        Cases
            Charges

    The rule function slices the CRecord into two: the slice that meets the rule's conditions, and the slice that doesn't. 
    The slice that _does_ meet the rule's conditions gets wrapped up in a `PetitionDecision.`

    The `PetitionDecision` is a Decision where the `name` describes the issue the rule deals with 
    (e.g. Expungements of nonconvictions); the value is a Petition object representing what petitions the rule decided it could create;
    and the `reasoning` is a tree of `Decisions`

    Each rule function takes a criminal record and returns a tuple of a tree of Decisions and a CRecord. 
    """

    def __init__(self, rec: "CRecord") -> None:
        self.record = rec
        self.remaining_record = copy.deepcopy(rec)
        self.decisions = []

    def rule(self, ruledef: Callable) -> Analysis:
        """
        Apply the rule `ruledef` to this analysis. 

        Args:
            ruledef (callable): ruledef is a callable. It takes a `crecord` as the only parameter. 
                It returns a tuple like (CRecord, Decision). The CRecord is whatever cases and charges remain
                on the input CRecord after applying `ruledef`. The Decision is an analysis of the record's
                eligibility for sealing or expungement. The Decision has a plain-langage `name`. It has a `value`
                that is a list of `Petiion` objects. And it has a `reasoning` that is a list of `Decisions` which
                explain how the rule decided what Petitions should be created.

        Returns:
            This Analyis, after applying the ruledef and updating the analysis with the results of the ruledef.
        """
        remaining_record, petition_decision = ruledef(self.remaining_record)
        self.remaining_record = remaining_record
        self.decisions.append(petition_decision)
        return self


def summarize(analysis: Analysis) -> dict:
    """
    Summarize the results of an analysis in a dict. 
    
    This summary flattens the whole analysis to give a case-by-case
    and charge-by-charge summation of the record and what can be done 
    (i.e., pettion, wait for autosealing, pardon) with everything in a record.
    """
    errs = []
    summary = dict()
    crecord = analysis.record
    remaining = analysis.remaining_record
    decisions = analysis.decisions

    # the summary is a nested key-value mapping of case-to-charge-to-
    #    what-can-be-done-with-a-charge.
    # It also caches some additional useful information.

    # updater functions will increment these counters.
    summary["clearable_cases"] = 0
    summary["clearable_charges"] = 0

    summary["cases"] = dict()
    for case in crecord.cases:
        summary["cases"][case.docket_number] = {
            "next_steps": "",
            "docket_url": case.docket_url,
            "charges": dict(),
        }
        for charge in case.charges:
            summary["cases"][case.docket_number]["charges"][charge.sequence] = {
                "offense": charge.offense,
                "is_conviction": charge.is_conviction(),
                "grade": charge.grade,
                "disposition": charge.disposition
                if charge.disposition is not None
                else "We could not find the disposition. We are assuming this wasn't a conviction, but could be wrong. A lawyer would be able to help figure this out.",
                "disposition_date": charge.disposition_date or case.disposition_date,
                "next_steps": "",
            }

    # Now go through each Decision of the analysis. If the decision proposed doing something
    # with a charge, explain that in the 'next steps'. Or note "need to pay fines",
    # "wait till ... for eligibility", "need pardon".

    for decision in decisions:
        # each decision is from a different rule.
        #
        # For a filterdecision, the value is the cases that were filtered.
        # For a petitiondecision, the value is a Petition, and the Petition has cases that
        if decision.name == "Traffic Court cases removed from consideration.":
            summary = update_summary_for_traffic_cases(summary, decision)
        elif decision.name == "Expungements for a person over 70.":
            summary = update_summary_for_over_70_expungements(summary, decision)
        elif (
            decision.name
            == "Expungements for a deceased person, after three years afther their death."
        ):
            summary = update_summary_for_deceased_expungements(summary, decision)
        elif decision.name == "Expungements of nonconvictions.":
            summary = update_summary_for_nonconviction_expungements(summary, decision)
        elif decision.name == "Expungements for summary convictions.":
            summary = update_summary_for_summary_convictions(summary, decision)
        elif decision.name == "Sealing some convictions under the Clean Slate reforms.":
            summary = update_summary_for_sealing_convictions(summary, decision)
        elif decision.name == "Eligibility for Automated Sealing":
            summary = update_summary_for_automated_sealing(summary, decision)
        else:
            logger.error(
                "Decision named %s not recognized in summarize().", decision.name
            )
            errs.append(
                f"Decision named {decision.name} not recognized in summarize()."
            )

    # go through cases and charges, and if there's anything with no next steps, note that pardons may
    # necessary for cases that are closed.
    for docket_number, case in summary["cases"].items():
        if len(case["charges"].items()) == 0:
            case[
                "next_steps"
            ] = "The software was not able to find any charges in this case. This case may be a civil case unrelated to criminal charges. Or this case may be related to another (such as through a transfer), in which case sealing or expunging the other case may seal or expunge this one as well."
        for sequence, charge in case["charges"].items():
            if case["next_steps"] == "" and charge["next_steps"] == "":
                if any(
                    [charge["is_conviction"] for seq, charge in case["charges"].items()]
                ):
                    case[
                        "next_steps"
                    ] = "You may need a pardon before this can be expunged or sealed. "

    return summary, errs


def set_next_step(summary, docket_number, charge_sequence=None, next_step="") -> dict:
    if charge_sequence is None:
        summary["cases"][docket_number]["next_steps"] += next_step
    else:
        summary["cases"][docket_number]["charges"][charge_sequence][
            "next_steps"
        ] += next_step
    return summary


def update_summary_for_automated_sealing(summary, decision):
    charge_patt = re.compile(r"Is the charge (?P<sequence>\w+(?:,\w+)?) for .*")

    for docket_number, case_decision in decision.reasoning.items():
        case_is_clearable = False
        for charge_decision in case_decision:
            match = charge_patt.search(charge_decision.name)
            sequence = match.group("sequence")
            logging.info("Handling %s, %s", docket_number, charge_decision)
            if bool(charge_decision) is True:
                summary["clearable_charges"] += 1
                case_is_clearable = True
                summary = set_next_step(
                    summary,
                    docket_number,
                    sequence,
                    next_step="This charge may be automatically sealed.",
                )
            elif bool(charge_decision.reasoning[0]) and all(
                charge_decision.reasoning[2:]
            ):
                summary = set_next_step(
                    summary,
                    docket_number,
                    sequence,
                    next_step="This charge may be eligible for automatic sealing once all fines are paid.",
                )
            elif all(charge_decision.reasoning[1:]):
                years_between_decision = charge_decision.reasoning[0]
                summary = set_next_step(
                    summary,
                    docket_number,
                    sequence,
                    next_step="This charge may become sealable."
                    + years_between_decision.reasoning,
                )
        if case_is_clearable:
            summary["clearable_cases"] += 1
    return summary


def update_summary_for_traffic_cases(summary: dict, decision: "FilterDecision") -> dict:
    for case in decision.value:
        summary = set_next_step(
            summary,
            case.docket_number,
            next_step="Our system does not review traffic court cases. You can speak with a lawyer about your options for expunging traffic cases. ",
        )
    return summary


def update_summary_for_over_70_expungements(
    summary: dict, decision: "PetitionDecision"
) -> dict:
    for case in decision.get_cases():
        summary = set_next_step(
            summary,
            case.docker_number,
            next_step="Case likely expungeable by petition. ",
        )
        summary["clearable_cases"] += 1
    return summary


def update_summary_for_deceased_expungements(
    summary: dict, decision: "PetitionDecision"
) -> dict:
    for case in decision.get_cases():
        summary = set_next_step(
            summary, case, next_step="Case likely expungeable by petition. "
        )
        summary["clearable_cases"] += 1
    return summary


def update_summary_for_nonconviction_expungements(
    summary: dict, decision: "PetitionDecision"
) -> dict:
    dkt_patt = re.compile(
        r"Does (?P<docket_number>.+) have expungeable nonconvictions\?"
    )  # re.compile(r"Is (?P<docket_number>.+) expungeable\?")
    charge_patt = re.compile(r"Is charge (?P<sequence>\w+(?:,\w+)?), for .*")
    for case_reason in decision.reasoning:
        # this Decision's reasoning is a list of Decisions.
        # The first one is about the whole record,
        # and the rest are each about each specific case.
        case_is_clearable = False
        dkt_search = dkt_patt.search(case_reason.name)
        if dkt_search:
            dkt_number = dkt_search.group("docket_number")
            # This decision _is_ about a specific case.
            for charge_reason in case_reason.reasoning:
                # the reasoning of the case_reasoning decision is
                # a list of decisions about each charge on the case.
                if bool(charge_reason) is False:
                    # the charge_reason is _false_ if the charge is _not_ a conviction, so its expungeable.
                    charge_match = charge_patt.search(charge_reason.name)
                    sequence_num = charge_match.group("sequence")

                    summary = set_next_step(
                        summary,
                        dkt_number,
                        sequence_num,
                        "Nonconviction likely expungeable by petition. ",
                    )
                    case_is_clearable = True
                    summary["clearable_charges"] += 1
        if case_is_clearable:
            summary["clearable_cases"] += 1
    return summary


def get_decision_by_name(ds: List[Decision], name: str) -> Optional[Decision]:
    """
    Find a decision in a list of decision with a matching name. The name can be a regex pattern. 
    """
    return [d for d in ds if re.match(name, d.name)]


def negative_decisions_only(decisions: List[Decision]) -> [Decision]:
    """
    Given a list of decisions, return only the negative ones.
    
    It's the caller's responsibility to know what 'negative' means in the set of decisions.

    For example, Negative/False doesn't always mean NOT SEALABLE ....
    """
    return [d for d in decisions if bool(d) is False]


def partition_decisions(
    decisions: List[Decision], partition_type: str = "Wait"
) -> Tuple[[Decision], [Decision]]:
    """
    Partition a list of decisions, based on the type of the decision.
    
    Args:
        decisions (List[Decision]): A list of Decisions.
        partition_type (str): The type of decision to partion by (e.g., "Wait", or "Eligibility")

    Returns: 
        A tuple. The first element is a list of the Decisions that _are_ of the type `partition_type`, and the 
            second element is the decisions that are not of that type.
    """
    return (
        [d for d in decisions if d.type == partition_type],
        [d for d in decisions if d.type != partition_type],
    )


def flatten(item) -> List:
    """
    given an item, if its a nested list, flatten it.
    """
    if item == []:
        return item
    if not isinstance(item, list):
        return [item]
    return flatten(item[0]) + flatten(item[1:])


def _base_decisions(decision: Decision) -> List[Decision]:
    """
    Given a single decision, if this decision has no Decisions as children, return it. 
    Otherwise return the base decisions of each of its children.
    """
    try:
        child1 = decision.reasoning[0]
        assert isinstance(child1, Decision)
        # This decision's reasoning is a list of more decisions.
        return flatten([_base_decisions(d) for d in decision.reasoning])
    except (AssertionError, IndexError):
        # This decision is the base decision.
        return [decision]


def base_decisions(decisions: [Decision]) -> List[Decision]:
    """
    Given a list of decisions, return all the decisions that don't have any Decisions as their children.

    In other words, a Decision can be a tree of Decisions. Return the nodes w/ no children.
    """
    return flatten([_base_decisions(d) for d in decisions])


def fines_and_wait_for_sealing(
    charge_decision: Decision, case_decision: Decision, full_record_decision: Decision
) -> Tuple[Optional[Decision], Optional[WaitDecision]]:
    """
    Takes a Decision about a case and a decision about the full record, and returns the fines decision and a list of any decisions at the base of this
        Decision that have (remember, Decisons' `reasoning` might be more Decisions)
        waiting times or fines. 
        
    It'll only return these decisions if fines and WaitDecisions are the only 
        Decisions preventing sealing. 
 
    Args: 
        case_decision: The first element of the case_decision's reasoning is about whether fines and costs are paid on the case. 
        full_record_decision: There are a number of Decisions about whether the person must wait before anything in the record is eligible for sealing.
    """

    # Note: for some reason, the decision indicating if a 'case' has disqualifying fines is the first decision in the
    #       reasoning of the _charge_.
    fines_decisions = get_decision_by_name(
        charge_decision.reasoning, r"Fines and costs are all paid on the case .*"
    )
    try:
        fines_decision = fines_decisions[0]
    except IndexError:
        fines_decision = None

    if bool(fines_decision):
        # fines were not a problem here, so its value is True.
        fines_decision = None
    # Collect a list of the decisions preventing sealing
    negative_decisions = negative_decisions_only(
        base_decisions(full_record_decision.reasoning)
    )
    # Of those, separate the decisions that will change to allowing sealing, after a waiting period
    # 'wait_decisions' are decisions that are blocking sealing until some time passes.
    # 'other_decisions' are other decisions blocking sealing.
    # If 'other_decisions' is empty but 'wait_decisions' is not, then this means
    # that the decisions requiring somebody waits for eligibility are the only reasons
    # the case isn't sealable.
    wait_decisions, other_decisions = partition_decisions(
        negative_decisions, partition_type="Wait"
    )

    # combine the negative decisions from the full record with the negative decisions from the charge
    # other_decisions += negative_decisions_only(charge_decision.reasoning)

    if len(other_decisions) == 0:
        # If the non-wait decisions were not preventing sealing, then the _only_ reasons preventing sealing are decisions
        # that will flip to true after a waiting period.
        return fines_decision, wait_decisions

    return fines_decision, None


def update_summary_for_sealing_convictions(
    summary: dict, decision: "PetitionDecision"
) -> dict:
    # the value of this Decision is a list of Decisions.
    # the first Decision encapsulates all the requirements for sealing related to the whole record.
    # The subsequent decisions are each about a single case, and the charges in that case.
    sealing_patt = re.compile(r"Sealing case (?P<docket_number>.*)")
    charge_patt = re.compile(r"Sealing charge (?P<sequence>[0-9,]+), .*")
    full_record_decision = decision.reasoning[0]
    for case_decision in decision.reasoning[1:]:
        # `case_is_clearable` indicates that _something_ in the case can be cleared,
        # so we can tell the user about what's sealable at a very high level.
        case_is_clearable = False
        match = sealing_patt.search(case_decision.name)
        docket_number = match.group("docket_number")

        if case_decision.value == "All charges sealable":
            summary = set_next_step(
                summary, docket_number, next_step="Case likely sealable by petition. ",
            )
            summary["clearable_cases"] += 1
            summary["clearable_charges"] += len(case_decision.reasoning)
        else:
            # The whole case isn't sealable, so we'll review each charge.
            for charge_decision in case_decision.reasoning:
                match = charge_patt.search(charge_decision.name)
                sequence = match.group("sequence")
                if charge_decision.value == "Sealable":
                    # This charge is sealable, so tell the user.
                    summary = set_next_step(
                        summary,
                        docket_number,
                        sequence,
                        next_step="Charge is likely sealable by petition. ",
                    )
                    case_is_clearable = True
                    summary["clearable_charges"] += 1
                else:
                    # This charge is _not_ sealable. We need to check if:
                    # 1) the charge will _become_ sealable after some time passes.
                    # 2) Either:
                    #    A) It will become sealable, and there are also charges that need to get paid
                    #    B) The only reason its not sealable is the fees.
                    # check if this charge is sealable but-for fines, and but-for time that needs to pass.
                    # if fines are the only reason this charge isn't sealable, say so.

                    # TODO We're going to do this by
                    #    create a Decision subclass called WaitDecision that has
                    #       an extra prop, 'years_to_wait'. If the WaitDecision is that
                    #       time must pass before the Decision's value flips, then
                    #       `years_to_wait` will explain that.
                    #   Then we'll have a function `fines_and_wait_for_sealing :: Decision -> Optional[Decision], Optional[Decision]` that
                    #       takes a Decision, and returns the fines decision and a list of any decisions at the base of this
                    #       Decision that have (remember, Decisons' `reasoning` might be more Decisions)
                    #       waiting times. It'll only return these decisions if fines and WaitDecisions are the only
                    #       Decisions preventing sealing.
                    #   At that point, we'll have the decision about fines, and a list of decisions that will flip their value after waiting.
                    #       We can tell the user "you've got to pay xxx", and "You've got to wait for yyy"

                    fines_all_paid, wait_decisions = fines_and_wait_for_sealing(
                        charge_decision, case_decision, full_record_decision
                    )

                    next_step = ""
                    if not fines_all_paid:
                        next_step = f"{fines_all_paid.reasoning} Fines remaining on this case must be resolved before the charge can be sealed."
                        if wait_decisions:
                            # there are fines to pay, and the person must wait for some time to seal.
                            max_time_to_wait = max(
                                wait_decisions, key=lambda d: d.years_to_wait
                            )
                            # TODO - the WaitDecisions need 'reasoning' that's text, not a list of the disqualifying convictions.
                            next_step += f" In addition, it looks like you must wait {max_time_to_wait.years_to_wait} before eligibility. {max_time_to_wait.reasoning}"
                            summary = set_next_step(
                                summary, docket_number, sequence, next_step
                            )
                    elif wait_decisions:
                        # Person must wait for time to pass, before sealing.
                        max_time_to_wait = max(
                            wait_decisions, key=lambda d: d.years_to_wait
                        )
                        next_step = f"{max_time_to_wait.reasoning} Sealing this charge immeditately may require a pardon first."  # This charge may become eligible for sealing in {max_time_to_wait.years_to_wait} years."
                    else:
                        # Charge is not sealable.
                        next_step = "This charge does not appear eligible for sealing."
                    summary = set_next_step(
                        summary, docket_number, sequence, next_step=next_step
                    )
        if case_is_clearable:
            summary["clearable_cases"] += 1
    return summary


def update_summary_for_summary_convictions(summary, decision):
    case_pattern = re.compile(r"Is (?P<docket_number>.+) expungeable\?")
    charge_pattern = re.compile(r"Is the charge (?P<sequence>\w+(?:,\w+)?) for .*")
    arrest_free = decision.reasoning[0]
    for case_decision in decision.reasoning[1:]:
        case_is_clearable = False
        match = case_pattern.search(case_decision.name)
        docket_number = match.group("docket_number")
        for charge_decision in case_decision.reasoning:
            match = charge_pattern.search(charge_decision.name)
            # I don't check for `match is None` because this should never happen.
            # The software is writing the name of this decision, so if the match doesn't work,
            # its a software bug, not a weird docket value or user input.
            sequence = match.group("sequence")
            if bool(charge_decision) and bool(arrest_free):
                summary = set_next_step(
                    summary,
                    docket_number,
                    sequence,
                    next_step="Charge likely can be expunged. ",
                )
                case_is_clearable = True
                summary["clearable_charges"] += 1
            elif bool(charge_decision):
                summary = set_next_step(
                    summary,
                    docket_number,
                    sequence,
                    next_step="Charge likely cannot be expunged yet. There must be five (5) years since the last arrest for prosecution. "
                    + arrest_free.reasoning,
                )
        if case_is_clearable:
            summary["clearable_cases"] += 1
    return summary

