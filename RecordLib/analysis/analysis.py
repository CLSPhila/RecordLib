from __future__ import annotations
from typing import Callable
import copy
import re
from collections import OrderedDict
import logging


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
        summary["cases"][case.docket_number] = {"next_steps": "", "charges": dict()}
        for charge in case.charges:
            summary["cases"][case.docket_number]["charges"][charge.sequence] = {
                "offense": charge.offense,
                "is_conviction": charge.is_conviction(),
                "grade": charge.grade,
                "disposition": charge.disposition,
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
            ] = "This case may be related to another (such as through a transfer), and sealing or expunging the other case may seal or expunge this one as well."
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


def update_summary_for_sealing_convictions(
    summary: dict, decision: "PetitionDecision"
) -> dict:
    # the value of this Decision is a list of Decisions.
    # the first Decision encapsulates all the requirements for sealing related to the whole record.
    # The subsequent decisions are each about a single case, and the charges in that case.
    sealing_patt = re.compile(r"Sealing case (?P<docket_number>.*)")
    charge_patt = re.compile(r"Sealing charge (?P<sequence>[0-9,]+), .*")
    full_record_decision = decision.reasoning[0]
    # Decision about how much time is left for sealing is the first decision of the full_record_decision.
    time_left_decision = full_record_decision.reasoning[0]
    rest_of_full_record_decisions_are_true = all(full_record_decision.reasoning[1:])
    for case_decision in decision.reasoning[1:]:
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
            for charge_decision in case_decision.reasoning:
                match = charge_patt.search(charge_decision.name)
                sequence = match.group("sequence")
                if charge_decision.value == "Sealable":
                    summary = set_next_step(
                        summary,
                        docket_number,
                        sequence,
                        next_step="Charge is likely sealable by petition. ",
                    )
                    case_is_clearable = True
                    summary["clearable_charges"] += 1
                else:
                    # check if this charge is sealable but-for fines, and but-for time that needs to pass.
                    # if fines are the only reason this charge isn't sealable, say so.
                    there_are_no_outstanding_fines = charge_decision.reasoning[0]
                    rest_are_true = all(
                        [bool(dec) for dec in charge_decision.reasoning[1:]]
                    )
                    explanation = ""
                    if (
                        rest_are_true
                        and rest_of_full_record_decisions_are_true
                        and not bool(time_left_decision)
                    ):
                        # if everything but the fines decision is satisfied for this charge to be sealable,
                        # and if there is
                        explanation += (
                            "You'll need to wait before this may become sealable. "
                        )
                    ## TODO need to also explain if the other time-based decisions are blocking sealing here -
                    ## rules 0, 6, and 7 in the full_record_sealing_requirements all deal with 'x years must have passed since y convictions`.
                    if not bool(there_are_no_outstanding_fines):
                        if len(explanation) > 0:
                            explanation += "Also, it "
                        else:
                            explanation += "It "
                        explanation += (
                            "looks like there are outstanding fines that must be paid before any sealing could be possible. "
                            + there_are_no_outstanding_fines.reasoning
                        )
                    summary = set_next_step(
                        summary, docket_number, sequence, next_step=explanation
                    )
                    # if rest_are_true and not bool(there_are_no_outstanding_fines):
                    #     summary = set_next_step(
                    #         summary,
                    #         docket_number,
                    #         sequence,
                    #         next_step="Charge may be sealable, but you must pay outstanding fines. "
                    #         + there_are_no_outstanding_fines.reasoning,
                    #     )
                    # if all(
                    #     [bool(dec) for dec in charge_decision.reasoning]
                    # ) and not bool(time_left_decision):
                    #     # In this case, the only reason the charge isn't sealable is that
                    #     # more time needs to pass.
                    #     # So let's tell the user how much more time there is to wait for sealability.
                    #     summary = set_next_step(
                    #         summary,
                    #         docket_number,
                    #         sequence,
                    #         next_step="Need to wait ___ for sealing.",
                    #     )
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

