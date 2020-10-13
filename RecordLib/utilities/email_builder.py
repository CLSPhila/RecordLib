from typing import Dict, Set, List, Tuple
from RecordLib.crecord import Case
from RecordLib.petitions import Petition
from RecordLib.analysis import Analysis
from RecordLib.analysis.ruledefs import simple_sealing_rules as ssr
from mako.lookup import TemplateLookup
from mako.template import Template
import sendgrid
from sendgrid.helpers.mail import Email, To, Content, Mail
import os


class EmailBuilder:
    """
    build an email out of an analysis of a criminal record. 
    
    """

    def __init__(self, sources, analysis: Analysis):
        """


        Args:
            analysis: a dictionary representing the results of a clean slate analysis.
        """
        self.sourcerecords = sources
        self.analysis = analysis
        self.counties = None
        self.num_petitions = None

    def email(self, to_address):
        """Send an html email"""
        sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_APIKEY"])
        from_email = Email("cleanslatescreener@clsphila.org")
        to_email = To(to_address)
        subject = "Test of Clean Slate Analysis."
        content = Content("text/html", self.html())
        mail = Mail(from_email, to_email, subject, content)
        response = sg.client.mail.send.post(request_body=mail.get())
        print(response.status_code)
        print(response.body)
        print(response.headers)

    def get_counties(self) -> Set[str]:
        """
        Collect a list of the counties in which an analysis contains records.
        """
        if self.counties is None:
            self.counties = set()
            for case in self.analysis.record.cases:
                if case.county is None:
                    continue
                self.counties.add(case.county.strip().lower())

        return self.counties

    def get_petitions_filed(self) -> List[Petition]:
        """
        A list of the petitions that this analysis recommends filing.
        """
        return [
            petition
            for petition_decision in self.analysis.decisions
            for petition in petition_decision.value
        ]

    def get_cases_cleared(self) -> List[Case]:
        """
        A list of the cases that appear in petitions that this analysis recommends.
        """
        return [
            case for petition in self.get_petitions_filed() for case in petition.cases
        ]

    def get_num_cases_cleared(self) -> Dict[str, int]:
        """
        Calculate the number of cases and charges that can be cleared.

        """
        results = {
            "num_petitions": 0,
            "num_cases": 0,
            "num_charges": 0,
        }
        for petition_decision in self.analysis.decisions:
            petitions = petition_decision.value
            results["num_petitions"] += len(petitions)
        results["num_cases"] += len(self.get_cases_cleared())
        for case in self.get_cases_cleared():
            results["num_charges"] += len(case.charges)
        return results

    def get_unsealable_because_of_fines(self) -> List[Tuple[str]]:
        """
        Get the _charges_ that are unsealable because of fines on the _case_. 

        return a list of Tuples, with (docket number, fines owed)
        """
        # Find the PetitionDecision for sealing

        # iterate over the reasoning, and if not everything's true up to the "Sealing Case Number ___" decisions, return nothing.

        # All the rest of the decisions are about sealing specific cases. For each one:

        # Find the Fines and Costs decision on the case. If its True (meaning fines and costs are paid), continue to the next case

        # If Fines and Costs is False, check the rest of the decisions on the case, which are decisions about sealing a charge. Each Charge that is
        # marked "Sealable", should be returned by this function, because these charges _would_ be sealable but for the fines.
        pass

    def caseExist(self, case, cases) -> bool:
        result = False;
        for c in cases:
            if(c.docket_number == case.docket_number):
                result = True;
                break;
        return result;
    def petionDetails(self, case, petitions):
        for petition_type in petitions:
            for petition in petition_type.value:
                if(petition.cases[0].docket_number == case.docket_number):
                    return petition_type.name
        return "";

    def get_unsealable_until_date(self, case) -> List:
        """
        Explain whether a case will be sealable after a certain date. 

        In other words, charges that are sealble but-for the charge being too recent. 
        """

        case_sealability = ssr.petition_sealing_for_single_case(case)
        if case_sealability.value[1] is None:
            # If the [1] position of the value tuple is None, that means nothing in this case is sealable, when we're
            # looking just at the case- and charge-specific requirements.
            # If the case's case- and charge-specific conditions aren't met, then
            # the date-of-last-conviction cannot be the only reason the case isn't sealable.
            return None

        crecord = self.analysis.record
        global_rules = ssr.full_record_requirements_for_petition_sealing(crecord)
        if (
            sum(list(map(int, map(bool, global_rules.reasoning))))
            != len(global_rules.reasoning) - 1
        ):
            # If there was not one and only one reason that the record can't be sealed (i.e. the correspoding decision isn't false),
            # then date-of-last-conviction cannot be the only reason the case isn't sealable.
            # So here we count the number of True decisions, and if the value isn't one less than the number of decisions,
            # then the date-of-last-conviction cant be the only reason the case isn't sealable.
            return None

        ten_years_decision = ssr.ten_years_since_last_conviction_for_m_or_f(crecord)
        if bool(ten_years_decision) is True:
            # This record passes the ten years since conviction requirement, so
            # that rule is not what's preventing this case from being sealable.
            return None

        return ten_years_decision.reasoning

    def get_fees_on_case(self, docket_number) -> int:
        """
        Get the fees owed on a case, if any.
        """
        crec = self.analysis.record
        cases = [c for c in crec.cases if c.docket_number == docket_number]
        if len(cases) == 0:
            raise ValueError(f"Cannot find {docket_number}")
        if len(cases) != 1:
            raise ValueError(f"There are too many cases names {docket_number}")
        case = cases[0]
        return (case.total_fines or 0) - (case.fines_paid or 0)

    def get_search_details(self):
        try:
            crec = self.analysis.record
            person = crec.person
            return {
                "first_name": person.first_name,
                "last_name": person.last_name,
                "dob": person.date_of_birth,
            }
        except:
            return {"error": "Something went wrong with the search."}

    def html(self) -> str:
        """
        Return an html-formatted string that describes the analysis.
        """
        mylookup = TemplateLookup(
            directories=[os.environ["EMAIL_TEMPLATE_DIR"]],
            module_directory=os.environ["MAKO_MODULE_DIR"],
        )
        if len(self.sourcerecords) > 0:
            base_template = mylookup.get_template("found_record.html")
        else:
            base_template = mylookup.get_template("did_not_find_record.html")
        return base_template.render(
            analysis=self.analysis,
            counties=self.get_counties(),
            sealable_with_fines=self.get_unsealable_because_of_fines(),
            num_cases_cleared=self.get_num_cases_cleared(),
            get_fees_on_case=self.get_fees_on_case,
            get_unsealable_until_date=self.get_unsealable_until_date,
            search_details=self.get_search_details(),
            caseExist=self.caseExist,
            petionDetails=self.petionDetails
        )

