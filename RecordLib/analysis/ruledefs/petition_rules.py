"""
This collection of rule functions determine what Petitions can be generated from a crecord.

These rule functions take a CRecord, and return a tuple. The first member of the tuple
is a CRecord that represents the parts of the input CRecord that do _not_ meet the conditions 
of the rule. The second member of the tuple is a PetitionDecision (a Decision where the `value`
is a Petition object)

These rule functions are useful to pass into an `Analysis` and collect a set of `Petitions` to create for a user to 
expunge or seal their record.
"""
from typing import Tuple
from RecordLib.analysis.decision import Decision, PetitionDecision
from RecordLib.analysis.ruledefs import simple_expungement_rules as ser
from RecordLib.analysis.ruledefs import simple_sealing_rules as ssr
from RecordLib.crecord import CRecord
from RecordLib.petitions import Expungement, Sealing, Petition
import copy


def expunge_over_70(crecord: CRecord) -> Tuple[CRecord, PetitionDecision]:
    """
    Analyze a crecord for expungements if the defendant is over 70.

    18 Pa.C.S. 9122(b)(1) provides for expungements of an individual who
    is 70 or older, and has been free of arrest or prosecution for 10
    years following the final release from confinement or supervision.
    """
    conclusion = PetitionDecision(
        name="Expungements for a person over 70.",
        reasoning=[
            ser.is_over_age(crecord.person, 70),
            ser.years_since_last_contact(crecord, 10),
            ser.years_since_final_release(crecord, 10),
        ],
    )

    if all(conclusion.reasoning):
        exps = [
            Expungement(
                client=crecord.person,
                cases=[c],
                expungement_reasons="and the Petitioner is over 70 years old has been free of arrest or prosecution for ten years following from completion the sentence",
            )
            for c in crecord.cases
        ]
        for e in exps:
            e.expungement_type = Expungement.ExpungementTypes.FULL_EXPUNGEMENT
        conclusion.value = exps
        remaining_record = CRecord(person=copy.deepcopy(crecord.person), cases=[])
    else:
        conclusion.value = []
        remaining_record = crecord

    return remaining_record, conclusion


def expunge_deceased(crecord: CRecord) -> Tuple[CRecord, PetitionDecision]:
    """
    Analyze a crecord for expungments if the individual has been dead for three years.

    18 Pa.C.S. 9122(b)(2) provides for expungement of records for an individual who has been dead for three years.
    """
    conclusion = PetitionDecision(
        name="Expungements for a deceased person, after three years afther their death.",
        reasoning=[
            Decision(
                name=f"Has {crecord.person.first_name} been deceased for 3 years?",
                value=crecord.person.years_dead() > 3,
                reasoning=f"{crecord.person.first_name} is not dead, as far as I know."
                if crecord.person.years_dead() < 0
                else f"It has been {crecord.person.years_dead()} since {crecord.person.first_name}'s death.",
            )
        ],
    )

    if all(conclusion.reasoning):
        exps = [Expungement(crecord.person, c) for c in crecord.cases]
        for e in exps:
            e.expungement_type = Expungement.ExpungementTypes.FULL_EXPUNGEMENT
        conclusion.value = exps
        remaining_record = CRecord(person=copy.deepcopy(crecord.person), cases=[])
    else:
        conclusion.value = []
        remaining_record = crecord

    return remaining_record, conclusion


def expunge_summary_convictions(crecord: CRecord) -> Tuple[CRecord, PetitionDecision]:
    """
    Analyze crecord for expungements of summary convictions.

    18 Pa.C.S. 9122(b)(3)(i) and (ii) provide for expungement of summary convictions if the individual 
    has been free of arrest or prosecution for five years following the conviction for the offense.

    Not available if person got ARD for certain offenses listed in (b.1)

    Returns:
        The function creates a Decision. The Value of the decision is a list of the Petions that can be
        generated according to this rule. The Reasoning of the decision is a list of decisions. The first
        decision is the global requirement for any expungement under this rule. The following decisions
        are a decision about the expungeability of each case. Each case-decision, contains its own explanation
        of what charges were or were not expungeable.  

    TODO excluding ARD offenses from expungements here.

    TODO grades are often missing. We should tell users we're uncertain.
    """
    # Initialize the decision explaining this rule's outcome. It starts with reasoning that includes the
    # decisions that are conditions of any case being expungeable.
    arrest_free = ser.arrest_free_for_n_years(crecord)
    conclusion = PetitionDecision(
        name="Expungements for summary convictions.", value=[], reasoning=[arrest_free],
    )

    # initialize a blank crecord to hold the cases and charges that can't be expunged under this rule.
    remaining_record = CRecord(person=crecord.person)
    for case in crecord.cases:
        # Find expungeable charges in a case. Save a Decision explaining what's
        # expungeable to
        # the reasoning of the Decision about the whole record.
        case_d = Decision(name=f"Is {case.docket_number} expungeable?", reasoning=[])
        expungeable_case = (
            case.partialcopy()
        )  # The charges in this case that are expungeable.
        not_expungeable_case = (
            case.partialcopy()
        )  # Charges in this case that are not expungeable.

        for charge in case.charges:
            charge_d = ser.is_summary_conviction(charge)
            if arrest_free and all(charge_d.reasoning):
                expungeable_case.charges.append(charge)
                charge_d.value = True
            else:
                charge_d.value = False
                not_expungeable_case.charges.append(charge)
            case_d.reasoning.append(charge_d)

        # If there are any expungeable charges, add an Expungepent to the Value of the decision about
        # this whole record.
        if len(expungeable_case.charges) > 0:
            case_d.value = True
            exp = Expungement(
                client=crecord.person,
                cases=[expungeable_case],
                expungement_reasons=".  The petitioner has been arrest free for more than five years since this summary conviction",
            )
            if len(expungeable_case.charges) == len(case.charges):
                exp.expungement_type = Expungement.ExpungementTypes.FULL_EXPUNGEMENT
            else:
                exp.expungement_type = Expungement.ExpungementTypes.PARTIAL_EXPUNGEMENT
            conclusion.value.append(exp)

        if len(not_expungeable_case.charges) > 0:
            case_d.value = False
            remaining_record.cases.append(not_expungeable_case)
        conclusion.reasoning.append(case_d)

    return remaining_record, conclusion


def expunge_nonconvictions(crecord: CRecord) -> Tuple[CRecord, PetitionDecision]:
    """
    18 Pa.C.S. 9122(a) provides that non-convictions (cases are closed with no disposition recorded) "shall be expunged."
    
    Returns:
        a Decision with:
            name: str,
            value: [Petition],
            reasoning: [Decision]
    """
    conclusion = PetitionDecision(
        name="Expungements of nonconvictions.", value=[], reasoning=[]
    )

    remaining_record = CRecord(person=crecord.person)
    for case in crecord.cases:
        # Go through each case in the record, and each charge in each case.
        #   If a charge is a conviction, then it can't be expunged under this rule.
        #   Add unexpungeable charges and their cases to the remaining record,
        #   and add expungeable charges to the value of this rule.
        case_d = Decision(
            name=f"Does {case.docket_number} have expungeable nonconvictions?",
            reasoning=[],
        )
        unexpungeable_case = case.partialcopy()
        expungeable_case = case.partialcopy()
        for charge in case.charges:
            charge_d = ser.is_conviction_or_unresolved(charge)

            if bool(charge_d) is False and charge_d.value is not None:
                # if the charge_d's value is False, then the charge is _not_ a conviction, and its not unresolved. Hence
                # _is_ expungeable here.
                expungeable_case.charges.append(charge)
            else:
                unexpungeable_case.charges.append(charge)
            case_d.reasoning.append(charge_d)

        # If there are any expungeable charges, add an Expungepent to the Value of the decision about
        # this whole record.
        if len(expungeable_case.charges) > 0:
            case_d.value = True
            exp = Expungement(client=crecord.person, cases=[expungeable_case])
            if len(expungeable_case.charges) == len(case.charges):
                exp.expungement_type = Expungement.ExpungementTypes.FULL_EXPUNGEMENT
            else:
                exp.expungement_type = Expungement.ExpungementTypes.PARTIAL_EXPUNGEMENT
            conclusion.value.append(exp)
        else:
            case_d.value = False

        if len(unexpungeable_case.charges) > 0:
            remaining_record.cases.append(unexpungeable_case)
        conclusion.reasoning.append(case_d)
    return remaining_record, conclusion


def seal_convictions(crecord: CRecord) -> Tuple[CRecord, PetitionDecision]:
    """
    18 Pa.C.S. 9122.1 provides for petition-based sealing of records when certain
    conditions are met.

    Paragraph (a) provides a general rule that sealing is available when someone has been free of conviction for 10 years of certain offenses,
    and has paid fines and costs.


    Returns:
        A Decision. The decision's name is "Sealable Convictions". Its `value` is a list of the Cases and 
            charges that are selable from `crecord`. 
            Its `reasoning` is a list of all the decisions relating to the whole record, and all the decisions 
            relating to each case.

    TODO Paragraph (b)(2) provides conditions that disqualify a person's whole record from sealing.

    TODO Paragraph (b)(1) provides conditions that exclude convictions from sealing.

    """
    conclusion = PetitionDecision(
        name="Sealing some convictions under the Clean Slate reforms.",
        value=[],
        reasoning=[],
    )
    mod_rec = CRecord(person=crecord.person, cases=[])
    # Requirements for sealing any part of a record
    full_record_decision = ssr.full_record_requirements_for_petition_sealing(crecord)
    conclusion.reasoning.append(full_record_decision)
    for case in crecord.cases:
        # The sealability of each case is its own decision
        case_decision = Decision(
            name=f"Sealing case {case.docket_number}", reasoning=[]
        )
        fines_decision = ssr.restitution_paid(case)  # 18 Pa.C.S. 9122.1(a)
        # case_decision.reasoning.append(fines_decision)
        # create copies of a case that don't include any charges.
        # sealable or unsealable charges will be added to these.
        # This is like we're taking a case, and slicing it into two parts:
        # a sealable part, and an unsealable part.
        sealable_parts_of_case = case.partialcopy()
        unsealable_parts_of_case = case.partialcopy()

        # Iterate over the charges in a case, to see which charges are sealable.
        charge_decisions = []
        for charge in case.charges:
            # The sealability of each charge is its own Decision.
            charge_decision = Decision(
                name=f"Sealing charge {charge.sequence}, {charge.offense}"
            )
            # Conditions that determine whether this charge is sealable
            #  See 91 Pa.C.S. 9122.1(b)(1)
            charge_decision.reasoning = [
                fines_decision,
                ssr.is_misdemeanor_or_ungraded(charge),
                ssr.no_danger_to_person_offense(
                    charge,
                    penalty_limit=2,
                    conviction_limit=1,
                    within_years=float("Inf"),
                ),
                ssr.no_offense_against_family(
                    charge,
                    penalty_limit=2,
                    conviction_limit=1,
                    within_years=float("Inf"),
                ),
                ssr.no_firearms_offense(
                    charge,
                    penalty_limit=2,
                    conviction_limit=1,
                    within_years=float("Inf"),
                ),
                ssr.no_sexual_offense(
                    charge,
                    penalty_limit=2,
                    conviction_limit=1,
                    within_years=float("Inf"),
                ),
                ssr.no_corruption_of_minors_offense(
                    charge,
                    penalty_limit=2,
                    conviction_limit=1,
                    within_years=float("Inf"),
                ),
            ]
            if all(charge_decision.reasoning) and bool(full_record_decision):
                # if all the reasoning for this charge is `true` (i.e. sealable)
                # _and_ the full record's requirements are also met
                # this charge is sealable, and it should be added to the sealable slice of
                # this case.
                charge_decision.value = "Sealable"
                sealable_parts_of_case.charges.append(charge)
            else:
                charge_decision.value = "Not sealable"
                unsealable_parts_of_case.charges.append(charge)
            charge_decisions.append(charge_decision)
        if all([decision.value == "Sealable" for decision in charge_decisions]):
            # All the charges in the current case are sealable.
            case_decision.value = "All charges sealable"
            conclusion.value.append(
                Sealing(client=crecord.person, cases=[sealable_parts_of_case])
            )
        elif any([decision.value == "Sealable" for decision in charge_decisions]):
            # At least one charge in the current case is sealable.
            case_decision.value = "Some charges sealable"
            mod_rec.cases.append(unsealable_parts_of_case)
            conclusion.value.append(
                Sealing(client=crecord.person, cases=[sealable_parts_of_case])
            )
        else:
            case_decision.value = "No charges sealable"
            mod_rec.cases.append(unsealable_parts_of_case)
        case_decision.reasoning.extend(charge_decisions)
        conclusion.reasoning.append(case_decision)
    return mod_rec, conclusion

