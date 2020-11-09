from __future__ import annotations
import uuid
import re
import logging
from typing import Optional
from dataclasses import dataclass, asdict
from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from RecordLib.sourcerecords.parsingutilities import get_text_from_pdf
from RecordLib.sourcerecords.docket.re_parse_pdf import (
    re_parse_pdf as docket_pdf_parser,
    re_parse_pdf_text as docket_text_parser,
)
from RecordLib.sourcerecords.summary.parse_pdf import (
    parse_pdf as summary_pdf_parser,
    parse_text as summary_text_parser,
)

logger = logging.getLogger(__name__)


class DocumentTemplate(models.Model):
    """Abstact model for storing a template for expungement or sealing petitions."""

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="templates/")
    default = models.BooleanField(null=True)

    class Meta:
        abstract = True


class ExpungementPetitionTemplate(DocumentTemplate):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["default"],
                condition=models.Q(default=True),
                name="unique_default_expungement_petition",
            )
        ]

    pass


class SealingPetitionTemplate(DocumentTemplate):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["default"],
                condition=models.Q(default=True),
                name="unique_default_sealing_petition",
            )
        ]

    pass


class UserProfile(models.Model):
    """Information unrelated to authentication that is relevant to a user. """

    user = models.OneToOneField(to=User, on_delete=models.CASCADE)
    expungement_petition_template = models.ForeignKey(
        ExpungementPetitionTemplate,
        on_delete=models.CASCADE,
        null=True,
        related_name="expugement_template_user_profiles",
    )
    sealing_petition_template = models.ForeignKey(
        SealingPetitionTemplate,
        on_delete=models.CASCADE,
        null=True,
        related_name="sealing_petition_template_user_profiles",
    )

    default_atty_organization = models.CharField(max_length=200, default="", blank=True)
    default_atty_name = models.CharField(max_length=200, default="", blank=True)
    default_atty_address_line_one = models.CharField(
        max_length=200, default="", blank=True
    )
    default_atty_address_line_two = models.CharField(
        max_length=200, default="", blank=True
    )
    default_atty_phone = models.CharField(max_length=50, default="", blank=True)
    default_bar_id = models.CharField(max_length=50, default="", blank=True)

    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}".strip()


def create_profile(sender, **kwargs):
    user = kwargs["instance"]
    if kwargs["created"]:
        user_profile = UserProfile(user=user)
        user_profile.save()


post_save.connect(create_profile, sender=User)


def set_default_templates(sender, **kwargs):
    """ 
    Set the default templates to a new user's templates, 
    If the user hasn't picked any templates, and if there are 
    default templates in the database.
    """
    profile = kwargs["instance"]
    if kwargs["created"]:
        if (
            profile.expungement_petition_template is None
            and ExpungementPetitionTemplate.objects.filter(default__exact=True).count()
            == 1
        ):
            profile.expungement_petition_template = ExpungementPetitionTemplate.objects.filter(
                default__exact=True
            ).all()[
                0
            ]
        if (
            profile.sealing_petition_template is None
            and SealingPetitionTemplate.objects.filter(default__exact=True).count() == 1
        ):
            profile.sealing_petition_template = SealingPetitionTemplate.objects.filter(
                default__exact=True
            ).all()[0]

        profile.save()


post_save.connect(set_default_templates, sender=UserProfile)


def set_default_attorney_name(sender, **kwargs):
    """
    Set the default name of the attorney on a user profile to the user's own name, if 
    nothing else is supplied.
    """
    profile = kwargs["instance"]
    if kwargs["created"]:
        if profile.default_atty_name is None or profile.default_atty_name == "":
            profile.default_atty_name = profile.get_full_name()

        profile.save()


post_save.connect(set_default_attorney_name, sender=UserProfile)


@dataclass
class SourceRecordFileInfo:
    caption: str = ""
    docket_num: str = ""
    court: str = ""
    url: str = ""
    record_type: str = ""
    fetch_status: str = ""
    raw_text: str = ""


def source_record_info(a_file):
    """
    Attempt to figure out basic information about what a source record relates to. 
    """
    filename = a_file.name
    file_info = SourceRecordFileInfo()
    try:
        file_info.raw_text = get_text_from_pdf(a_file)
    except Exception:
        pass

    # caption
    #  this is hard to get w/out parsing a lot.

    # record type

    first_five_lines = "\n".join(file_info.raw_text.split("\n")[0:5])

    if re.search("docket", first_five_lines, re.IGNORECASE):
        file_info.record_type = SourceRecord.RecTypes.DOCKET_PDF
    elif re.search("summary", first_five_lines, re.IGNORECASE):
        file_info.record_type = SourceRecord.RecTypes.SUMMARY_PDF

    # fetch status
    file_info.fetch_status = SourceRecord.FetchStatuses.FETCHED

    # docket_number
    docket_numbers = re.findall(r"(?P<docket_num>(?:\w+\-)+\d{4})", file_info.raw_text)

    if len(docket_numbers) < 1:
        logger.warning("Could not find docket number for doc %s", a_file.name)

    if file_info.record_type == SourceRecord.RecTypes.SUMMARY_PDF:
        file_info.docket_num = f"Summary({', '.join(docket_numbers)})"
        max_docket_num_length = SourceRecord._meta.get_field("docket_num").max_length
        if len(file_info.docket_num) > max_docket_num_length:
            file_info.docket_num = (
                file_info.docket_num[0 : (max_docket_num_length - 4)] + "..."
            )
    elif file_info.record_type == SourceRecord.RecTypes.DOCKET_PDF:
        file_info.docket_num = docket_numbers[0]

    # court
    if re.search("CP", file_info.docket_num):
        file_info.court = SourceRecord.Courts.CP
    elif re.search("MJ", file_info.docket_num):
        file_info.court = SourceRecord.Courts.MDJ
    elif re.search("MC", file_info.docket_num):
        file_info.court = SourceRecord.Courts.MC

    return file_info


class SourceRecord(models.Model):
    """
    Class to manage documents that provide information about a person's criminal record, such as a 
    summary pdf sheet or a docket pdf sheet.
    
    caption="Comm. v. Smith",
        docket_num="CP-1234", 
        court=SourceRecord.COURTS.CP,
        url="https://ujsportal.gov", 
        record_type=SourceRecord.RecTypes.SUMMARY,
        owner=admin_user
    """

    @classmethod
    def from_unknown_file(
        cls, a_file: InMemoryUploadedFile, **kwargs
    ) -> Optional[SourceRecord]:
        """ Create a SourceRecord from an uploaded file, or return None if we cannot tell what the file is.
        """
        try:
            file_info = source_record_info(a_file)
            if file_info:
                return cls(**asdict(file_info), file=a_file, **kwargs)
            else:
                return None
        except:
            return None

    class Courts:
        """ Documents may come from one of these courts. 
        
        Common Pleas (CP) (philly), Magisterial District Courts (out of philly), Muncipal (MC) (philly lower court)
        
        """

        CP = "CP"
        MDJ = "MDJ"
        MC = "MC"
        __choices__ = [
            ("CP", "CP"),
            ("MDJ", "MDJ"),
            ("MC", "MC"),
        ]

    class RecTypes:
        """ These types of records may be stored in this class. 
        """

        SUMMARY_PDF = "SUMMARY_PDF"
        DOCKET_PDF = "DOCKET_PDF"
        __choices__ = [
            ("SUMMARY_PDF", "SUMMARY_PDF"),
            ("DOCKET_PDF", "DOCKET_PDF"),
        ]

    def get_parser(self):
        """

        Based on the record_type of this SourceRecord, identify the parser it should use.
        """
        if self.record_type == SourceRecord.RecTypes.SUMMARY_PDF:
            if self.raw_text:
                return summary_text_parser
            else:
                return summary_pdf_parser
        else:
            # this is a docket, I hope.
            if self.raw_text:
                return docket_text_parser
            else:
                return docket_pdf_parser

    class FetchStatuses:
        """
        Documents have to be fetched and saved locally. 
        Has a particular document been fetched?
        """

        NOT_FETCHED = "NOT_FETCHED"
        FETCHING = "FETCHING"
        FETCHED = "FETCHED"
        FETCH_FAILED = "FETCH_FAILED"
        __choices__ = [
            ("NOT_FETCHED", "NOT_FETCHED"),
            ("FETCHING", "FETCHING"),
            ("FETCHED", "FETCHED"),
            ("FETCH_FAILED", "FETCH_FAILED"),
        ]

    class ParseStatuses:
        """
        Track whether the source record could be successfully parsed or not.
        """

        UNKNOWN = "UNKNOWN"
        SUCCESS = "SUCCESSFULLY_PARSED"
        FAILURE = "PARSE_FAILED"
        __choices__ = [
            ("UNKNOWN", "UNKNOWN"),
            ("SUCCESSFULLY_PARSED", "SUCCESSFULLY_PARSED"),
            ("PARSE_FAILED", "PARSE_FAILED"),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    caption = models.CharField(blank=True, max_length=300)

    docket_num = models.CharField(blank=True, max_length=50)

    court = models.CharField(max_length=3, choices=Courts.__choices__, blank=True)

    url = models.URLField(blank=True, default="")

    record_type = models.CharField(
        max_length=30, blank=True, choices=RecTypes.__choices__
    )

    fetch_status = models.CharField(
        max_length=100,
        choices=FetchStatuses.__choices__,
        default=FetchStatuses.NOT_FETCHED,
    )

    parse_status = models.CharField(
        max_length=100,
        choices=ParseStatuses.__choices__,
        default=ParseStatuses.UNKNOWN,
    )

    file = models.FileField(null=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    raw_text = models.TextField(null=True)
