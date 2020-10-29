"""
Ruledefs are functions that encapsulate legal logic. 

A ruledef takes a criminal record and produces a Decision explaining how a particular rule applies to that criminal record.

These ruledef functions can have a few different signatures. A ruledef might return a PetitionDecision or a regular Decision,
along with the part of a record that didn't match the rule's requirements.
"""

from .petition_rules import (
    expunge_nonconvictions,
    expunge_summary_convictions,
    expunge_deceased,
    expunge_over_70,
    seal_convictions,
)

from .simple_expungement_rules import (
    is_over_age,
    years_since_final_release,
    years_since_last_contact,
)


from .simple_sealing_rules import *

from .filter_rules import filter_traffic_cases

from .autosealing_rules import autosealing_eligibility
