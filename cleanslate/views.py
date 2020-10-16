"""
Views for the Recordlib webapp.

"""
from typing import Tuple, List
import logging
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework import permissions, status
from django_q.tasks import async_task
from RecordLib.crecord import CRecord
from RecordLib.sourcerecords import SourceRecord as RLSourceRecord
from RecordLib.analysis import Analysis
from RecordLib.utilities.serializers import to_serializable
from RecordLib.utilities import cleanslate_screen
from RecordLib.analysis.ruledefs import (
    expunge_summary_convictions,
    expunge_nonconvictions,
    expunge_deceased,
    expunge_over_70,
    seal_convictions,
)
from RecordLib.petitions import Expungement, Sealing
from cleanslate.models import User, UserProfile
from cleanslate.serializers import (
    CRecordSerializer,
    PetitionViewSerializer,
    FileUploadSerializer,
    UserProfileSerializer,
    UserSerializer,
    IntegrateSourcesSerializer,
    SourceRecordSerializer,
    DownloadDocsSerializer,
    AutoScreeningSerializer,
)
from cleanslate.compressor import Compressor
from cleanslate.services import download as download_service
from cleanslate.models import SourceRecord

logger = logging.getLogger(__name__)


class FileUploadView(APIView):
    """
    Handle uploads of source records.
    """

    parser_classes = [MultiPartParser, FormParser]

    # noinspection PyMethodMayBeStatic
    def post(self, request):
        """Accept dockets and summaries locally uploaded by a user, save them to the server,
        and return SourceRecords relating to those files..


        This POST needs to be a FORM post, not a json post.
        """
        file_serializer = FileUploadSerializer(data=request.data)
        if file_serializer.is_valid():
            files = file_serializer.validated_data.get("files")
            results = []
            try:
                for upload in files:
                    source_record = SourceRecord.from_unknown_file(
                        upload, owner=request.user
                    )
                    source_record.save()
                    if source_record is not None:
                        results.append(source_record)
                        # TODO FileUploadView should report errors in turning uploaded pdfs into SourceRecords.
                return Response(
                    {"source_records": SourceRecordSerializer(results, many=True).data},
                    status=status.HTTP_200_OK,
                )
            except Exception as err:
                return Response(
                    {"error_message": f"Parsing failed: {str(err)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response(
                {"error_message": "Invalid Data.", "errors": file_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SourceRecordsFetchView(APIView):
    """
    Views for handling fetching source records that are sent as urls
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        API endpoint that takes a set of cases with urls to docket or summary sheets, downloads them,
        and returns SourceRecords, which point to the documents' ids in the database.

        This is for accepting the UJS Search results, and creating SourceRecord objects describing each of those search results. 
        
        This view does _not_ attempt download the source records, or parse them.

        """
        try:
            posted_data = DownloadDocsSerializer(data=request.data)
            if posted_data.is_valid():
                records = posted_data.save(owner=request.user)
                download_service.source_records(records)
                return Response(
                    DownloadDocsSerializer({"source_records": records}).data,
                )
            return Response({"errors": posted_data.errors})
        except Exception as err:
            return Response({"errors": [str(err)]})


def integrate_dockets(
    crecord: CRecord,
    docket_source_records: List[SourceRecord],
    nonfatal_errors: List[str],
) -> Tuple[CRecord, List[str]]:
    """ Combine a set of source records representing 'dockets' with a criminal record"""
    for docket_source_record in docket_source_records:
        try:
            # get a RecordLib SourceRecord from the webapp sourcerecord model. The RecordLib SourceRecord has the machinery for
            # parsing the record to get a Person and Cases out of it.
            rlsource = RLSourceRecord(
                docket_source_record.raw_text or docket_source_record.file.path,
                parser=docket_source_record.get_parser(),
            )
            # If we reach this line, the parse succeeded.
            docket_source_record.parse_status = SourceRecord.ParseStatuses.SUCCESS
            # Integrate this docket with the full crecord.
            crecord.add_sourcerecord(
                rlsource,
                override_person=True,
                docket_number=docket_source_record.docket_num,
            )
        except Exception:
            docket_source_record.parse_status = SourceRecord.ParseStatuses.FAILURE
            nonfatal_errors.append(
                f"Could not parse {docket_source_record.docket_num} ({docket_source_record.record_type})"
            )
        finally:
            docket_source_record.save()
    return crecord, nonfatal_errors


def integrate_summaries(
    crecord: CRecord,
    summary_source_records: List[SourceRecord],
    docket_source_records: List[SourceRecord],
    nonfatal_errors: List[str],
    owner,
) -> Tuple[CRecord, List[SourceRecord], List[str]]:
    """
    Combine a set of source records representing summary sheets with a criminal record. In addition, 
    find any cases that the summary sheets mention which are not already in the criminal record. 
    
    For these extra cases, find a docket sheet for this case, and add it as a source record and integrate its information
    into the criminal record.
    """
    dockets_in_summaries = []
    for summary_source_record in summary_source_records:
        try:
            rlsource = RLSourceRecord(
                summary_source_record.raw_text or summary_source_record.file.path,
                parser=summary_source_record.get_parser(),
            )
            summary_source_record.parse_status = SourceRecord.ParseStatuses.SUCCESS
            dockets_in_summaries.extend([c.docket_number for c in rlsource.cases])
        except Exception:
            summary_source_record.parse_status = SourceRecord.ParseStatuses.FAILURE
        finally:
            summary_source_record.save()

    # compare the dockets_in_summaries to dockets already collected as source records
    # to see what dockets are missing from the set of source records.
    missing_dockets = [
        dn for dn in dockets_in_summaries if dn not in docket_source_records
    ]
    new_source_dockets = download_service.dockets(missing_dockets, owner=owner)
    logger.info("Downloaded %d", len(new_source_dockets))

    # now parse and integrate these new source dockets into the crecord.
    crecord, nonfatal_errors = integrate_dockets(
        crecord, new_source_dockets, nonfatal_errors
    )
    return crecord, new_source_dockets, nonfatal_errors


class IntegrateCRecordWithSources(APIView):
    """
    View to handle combining the information about a case or cases from source records with a crecord. 
    """

    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        """
        Accept a CRecord and a set of SourceRecords.
        
        Parse the SourceRecords, and incorporate the information that the SourceRecords
        contain into the CRecord.

        Two api endpoints of the Django app interact with RecordLib. This one
        accepts a serialzed crecord and a list of sourcerecords. It attempts
        to parse each source_record, and then integrate the sourcerecords into the crecord.

        TODO IntegrateCRecordWithSources should communicate failures better.

        """
        try:
            serializer = IntegrateSourcesSerializer(data=request.data)
            if serializer.is_valid():
                nonfatal_errors = []
                crecord = CRecord.from_dict(serializer.validated_data["crecord"])
                source_records = []
                # Find the SourceRecords in the database that have been sent in this request,
                # or if these are new source records, download the files they point to.
                # TODO this probably doesn't handle a request with a new SoureRecord missing a URL.
                for source_record_data in serializer.validated_data["source_records"]:
                    try:
                        source_records.append(
                            SourceRecord.objects.get(id=source_record_data["id"])
                        )
                    except Exception:
                        # create this source record in the database, if it is new.
                        source_rec = SourceRecord(
                            **source_record_data, owner=request.user
                        )
                        source_rec.save()
                        # also download it to the server.
                        download_service.source_records([source_rec])
                        source_records.append(source_rec)
                # Parse the uploaded source records, collecting RecordLib.SourceRecord objects.
                # These objects are parsing the records and figuring out case information in the SourceRecords.
                # For any source records that are summaries, find out if the summary describes cases that aren't also
                # docket source records. Search CPCMS for those, add the missing dockets to the list of source records.

                # First, parse the dockets.
                # Then we'll parse the summaries to find out if there are cases the summaries mention which the dockets do not.
                docket_source_records = [
                    sr
                    for sr in source_records
                    if sr.record_type == SourceRecord.RecTypes.DOCKET_PDF
                ]
                crecord, nonfatal_errors = integrate_dockets(
                    crecord, docket_source_records, nonfatal_errors
                )
                # Now attempt to parse summary records. Check the cases in each summary record to see if we have a docket for this case yet.
                # If we dont yet have a docket for this case, fetch it, parse it, integrate it into the CRecord.
                summary_source_records = [
                    sr
                    for sr in source_records
                    if sr.record_type == SourceRecord.RecTypes.SUMMARY_PDF
                ]
                crecord, new_source_records, nonfatal_errors = integrate_summaries(
                    crecord,
                    summary_source_records,
                    docket_source_records,
                    nonfatal_errors,
                    owner=request.user,
                )
                source_records += new_source_records
                return Response(
                    {
                        "crecord": CRecordSerializer(crecord).data,
                        "source_records": SourceRecordSerializer(
                            source_records, many=True
                        ).data,
                        "errors": nonfatal_errors,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as err:
            return Response(
                {"errors": [str(err)]}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AnalysisView(APIView):
    """
    Views related to an analysis of a CRecord.
    """

    permission_classes = [permissions.IsAuthenticated]
    # noinspection PyMethodMayBeStatic
    def post(self, request):
        """ Analyze a Criminal Record for expungeable and sealable cases and charges.
        
        POST body should be json-endoded CRecord object. 

        Return, if not an error, will be a json-encoded Decision that explains the expungements
        and sealings that can be generated for this record.

        """
        try:
            serializer = CRecordSerializer(data=request.data)
            if serializer.is_valid():
                rec = CRecord.from_dict(serializer.validated_data)
                analysis = (
                    Analysis(rec)
                    .rule(expunge_deceased)
                    .rule(expunge_over_70)
                    .rule(expunge_nonconvictions)
                    .rule(expunge_summary_convictions)
                    .rule(seal_convictions)
                )
                return Response(to_serializable(analysis))
            return Response(
                {"validation_errors": serializer.errors},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as err:
            logger.error(err)
            return Response({"errors": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class PetitionsView(APIView):
    """ Create petitions and an Overview document from an Analysis.
    
    POST should be a json-encoded object with an 'petitions' property that is a list of
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Accept an object describing petitions to generate, and generate them.
        """
        try:
            serializer = PetitionViewSerializer(data=request.data)
            if serializer.is_valid():
                errors = []
                petitions = []
                for petition_data in serializer.validated_data["petitions"]:
                    if petition_data["petition_type"] == "Sealing":
                        new_petition = Sealing.from_dict(petition_data)
                        # this could be done earlier, if needed, to avoid querying db over and over.
                        # but we'd need to test what types of templates are actually needed.
                        try:
                            new_petition.set_template(
                                request.user.userprofile.sealing_petition_template.file
                            )
                            petitions.append(new_petition)

                        except Exception as err:
                            logger.error(
                                "User has not set a sealing petition template, or "
                            )
                            errors.append(
                                "User has not set a sealing petition template."
                            )
                            logger.error(str(err))
                            continue
                    else:
                        new_petition = Expungement.from_dict(petition_data)
                        try:
                            new_petition.set_template(
                                request.user.userprofile.expungement_petition_template.file
                            )
                            petitions.append(new_petition)
                        except Exception as err:
                            logger.error(
                                "User has not set an expungement petition template, or "
                            )
                            errors.append(
                                "User has not set an expungememnt petition template"
                            )
                            logger.error(str(err))
                            continue
                client_last = petitions[0].client.last_name
                petitions = [(p.file_name(), p.render()) for p in petitions]
                package = Compressor(f"PetitionsFor{client_last}.zip", petitions)

                logger.info("Returning x-accel-redirect to zip file.")

                resp = HttpResponse()
                resp["Content-Type"] = "application/zip"
                resp["Content-Disposition"] = f"attachment; filename={package.name}"
                resp["X-Accel-Redirect"] = f"/protected/{package.name}"
                return resp
            else:
                return Response(
                    {"validation_errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                    content_type="application/json",
                )
        except Exception as e:
            logger.error(str(e))
            return Response(
                {"errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
                content_type="application/json",
            )


class UserProfileView(APIView):
    """Information about a user's account.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get the currently logged in user's profile information.
        """
        user = User.objects.get(id=request.user.id)
        profile = UserProfile.objects.get(user=user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "profile": UserProfileSerializer(profile).data,
            }
        )

    def put(self, request):
        """Update information about the logged in user's account."""

        user = User.objects.get(id=request.user.id)
        user_serializer = UserSerializer(user, data=request.data)

        profile = UserProfile.objects.get(user=user)
        profile_serializer = UserProfileSerializer(profile, data=request.data)
        if user_serializer.is_valid() and profile_serializer.is_valid():
            user_serializer.save()
            profile_serializer.save()
            # Should we return the user and profile here?
            return Response({"message": "Successful update"})

        return Response(
            {
                "errors": {
                    "user": user_serializer.errors,
                    "profile": profile_serializer.errors,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class AutoScreeningView(APIView):
    """
    Trigger an automated screening of a person's record.
    """

    def post(self, request):
        """
        Receive a name, dob, and email address, and send an automated review of a person's public record
        to the email address.
        """
        screening_request = AutoScreeningSerializer(data=request.data)
        if screening_request.is_valid():
            async_task(cleanslate_screen.by_name, **screening_request.validated_data)
            return Response({"status": "screening started."})
        else:
            return Response({"status": screening_request.errors})

