"""
Serialize models for the RecordLib web app.

"""

from rest_framework import serializers as S
from cleanslate.models import UserProfile, SourceRecord
from django.contrib.auth.models import User
from RecordLib.crecord import CRecord
from RecordLib.crecord import Case
from RecordLib.crecord import Person
from RecordLib.crecord import Charge, Sentence, SentenceLength


class UserSerializer(S.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class UserProfileSerializer(S.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            "id",
            "default_atty_organization",
            "default_atty_name",
            "default_atty_address_line_one",
            "default_atty_address_line_two",
            "default_atty_phone",
            "default_bar_id",
        ]

    default_atty_organization = S.CharField(allow_blank=True)
    default_atty_name = S.CharField(allow_blank=True)
    default_atty_address_line_two = S.CharField(allow_blank=True)
    default_atty_address_line_one = S.CharField(allow_blank=True)
    default_atty_phone = S.CharField(allow_blank=True)
    default_bar_id = S.CharField(allow_blank=True)


"""
These serializer classes are only for serializing and deserializing json/dict representations of these 
classes. Use each class's `from_dict` static method to actually get the object. 


Serializers also act like data validators for data in requests to the api.
"""


class FileUploadSerializer(S.Serializer):
    files = S.ListField(child=S.FileField(), allow_empty=True)


class SentenceLengthSerializer(S.Serializer):
    min_time = S.DurationField(required=False)  # S.IntegerField(required=False)
    min_unit = S.CharField(required=False)
    max_time = S.DurationField(required=False)  # S.IntegerField(required=False)
    max_unit = S.CharField(required=False)


class SentenceSerializer(S.Serializer):
    sentence_date = S.DateField(required=False)
    sentence_type = S.CharField(required=False, allow_blank=True)
    sentence_period = S.CharField(required=False, allow_blank=True)
    sentence_length = SentenceLengthSerializer()


class ChargeSerializer(S.Serializer):
    offense = S.CharField(required=False, allow_blank=True, allow_null=True, default="")
    grade = S.CharField(required=False, allow_blank=True, allow_null=True, default="")
    statute = S.CharField(required=False, allow_blank=True, allow_null=True, default="")
    disposition = S.CharField(
        required=False, allow_blank=True, allow_null=True, default=""
    )
    disposition_date = S.DateField(required=False, allow_null=True)
    sentences = SentenceSerializer(many=True, allow_empty=True)


class CaseSerializer(S.Serializer):
    status = S.CharField(required=False, allow_blank=True)
    county = S.CharField(required=False, allow_blank=True, default="")
    docket_number = S.CharField(required=True)
    otn = S.CharField(required=False, allow_blank=True)
    dc = S.CharField(required=False, allow_blank=True)
    charges = ChargeSerializer(many=True, allow_null=True)
    total_fines = S.IntegerField(required=False, default=0, allow_null=True)
    fines_paid = S.IntegerField(required=False, default=0, allow_null=True)
    complaint_date = S.DateField(required=False, allow_null=True)
    arrest_date = S.DateField(required=False, allow_null=True)
    disposition_date = S.DateField(required=False, allow_null=True)
    judge = S.CharField(required=False, allow_blank=True, allow_null=True)
    judge_address = S.CharField(
        required=False, allow_blank=True, default="", allow_null=True
    )
    affiant = S.CharField(required=False, allow_blank=True, allow_null=True)
    arresting_agency = S.CharField(
        required=False, allow_blank=True, default="", allow_null=True
    )
    arresting_agency_address = S.CharField(
        required=False, allow_blank=True, default="", allow_null=True
    )
    related_cases = S.ListField(child=S.CharField(allow_null=True), required=False,)


class AddressSerializer(S.Serializer):
    line_one = S.CharField(required=False, allow_blank=True)
    city_state_zip = S.CharField(required=False, allow_blank=True)


class AttorneySerializer(S.Serializer):
    organization = S.CharField(required=False, default="")
    full_name = S.CharField(required=False, default="")
    address = AddressSerializer(required=False)
    organization_phone = S.CharField(required=False, default="")
    bar_id = S.CharField(required=False, default="")


class PersonSerializer(S.Serializer):
    first_name = S.CharField(
        max_length=200, allow_blank=True, required=False, default=""
    )
    last_name = S.CharField(
        max_length=200, allow_blank=True, required=False, default=""
    )
    date_of_birth = S.DateField(required=False, allow_null=True)
    date_of_death = S.DateField(required=False, allow_null=True)
    aliases = S.ListField(
        child=S.CharField(allow_null=True), required=False,
    )  # CharField() doesn't seem to take many=True.
    ssn = S.CharField(max_length=15, required=False, allow_blank=True)
    address = AddressSerializer(required=False)


class AutoScreeningSerializer(S.Serializer):
    """
    Required elements for an auto-screening for expungements/sealings.
    """

    first_name = S.CharField(max_length=200, allow_blank=False)
    last_name = S.CharField(max_length=200, allow_blank=False)
    dob = S.DateField(required=True)
    email = S.EmailField(required=True)


class CRecordSerializer(S.Serializer):
    person = PersonSerializer()
    cases = CaseSerializer(many=True)


class PetitionSerializer(S.Serializer):
    attorney = AttorneySerializer(required=False)
    client = PersonSerializer()
    cases = CaseSerializer(many=True)
    expungement_type = S.CharField(required=False)
    petition_type = S.CharField(required=True)
    service_agencies = S.ListField(child=S.CharField(), required=False)
    include_crim_hist_report = S.CharField(required=False, allow_blank=True)
    ifp_message = S.CharField(required=False, allow_blank=True)
    expungement_reasons = S.CharField(required=False, allow_blank=True)


class PetitionViewSerializer(S.Serializer):
    """
    Validate data involving json objects describing petitions to generate.

    This serializer describes a very simple object that just has one key: `petitions`, which points to an array of PetitionSerializer objects. 
    """

    petitions = PetitionSerializer(many=True)


class SourceRecordSerializer(S.ModelSerializer):
    """ 
    Validate json that represents a criminal record source document, e.g., a summary pdf or docket pdf.
    """

    class Meta:
        model = SourceRecord
        exclude = [
            "owner",  # only the database knows who owns what files
            "file",
        ]  # the file itself isn't sent back and forth as a SourceRecord. The SourceRecord is a pointer to a file in the server.

    id = S.UUIDField(format="hex_verbose", required=False)


class IntegrateSourcesSerializer(S.Serializer):
    """
    Validate data where we've got a CRecord and source records that will be parsed and integrated into the crecord.
    """

    crecord = CRecordSerializer()
    source_records = SourceRecordSerializer(many=True, allow_empty=True)


class DownloadDocsSerializer(S.Serializer):
    """
    Validate json of a POST that contains source records (a collection of objects validated by SourceRecordSerializer)
    """

    source_records = SourceRecordSerializer(many=True)

    def create(self, validated_data):
        owner = validated_data.pop("owner")
        return [
            SourceRecord.objects.create(**rec, owner=owner)
            for rec in validated_data["source_records"]
        ]

