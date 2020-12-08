from datetime import datetime
import time
import logging
import os
import pytest
import requests
from django.core.files import File
from django.conf import settings
from cleanslate.models import (
    SourceRecord,
    ExpungementPetitionTemplate,
    User,
    UserProfile,
)
import cleanslate.services.download as download
from cleanslate.services.initializers import clear_missing_petition_templates

logger = logging.getLogger(__name__)


class FakeResponse:
    def __init__(self):
        self.content = b"some bytes content"
        self.status_code = 200


def test_download_source_records(admin_user, monkeypatch):
    def slow_get(*args, **kwargs):
        time.sleep(3)
        return FakeResponse()

    monkeypatch.setattr(requests, "get", slow_get)

    rec = SourceRecord.objects.create(
        caption="Test v Test",
        docket_num="CP-1234",
        court=SourceRecord.Courts.CP,
        url="https://some.slow.url",
        record_type=SourceRecord.RecTypes.SUMMARY_PDF,
        owner=admin_user,
    )
    rec.save()
    assert rec.file.name is None
    before = datetime.now()
    recs = [rec, rec, rec]
    download.source_records(recs)
    after = datetime.now()
    time_spent = after - before
    assert rec.file.name is not None
    # use pytest --log-cli-level info to see this.
    logger.info(
        f"downloading {len(recs)} document took {time_spent.total_seconds()} seconds."
    )


@pytest.mark.django_db
def test_clear_missing_templates(admin_user):
    # Create a template record in the database
    with open("templates/petitions/790ExpungementTemplate.docx", "rb") as f:
        fl = File(f)
        template = ExpungementPetitionTemplate(name="example", file=fl)
        template.save()
        templateid = template.id
        filepath = os.path.join(settings.MEDIA_ROOT, template.file.name)

    # file is uploaded to the MEDIA ROOT path.
    assert os.path.exists(filepath)

    # assign this template to a user.
    admin_user.userprofile.expungement_petition_template = template
    admin_user.userprofile.save()

    # delete the file that it points to.
    os.remove(filepath)
    assert not os.path.exists(filepath)

    # run clear_missing_templates
    clear_missing_petition_templates()

    # the template record in the database should be gone.
    with pytest.raises(Exception):
        ExpungementPetitionTemplate.objects.get(id=templateid)

    # the user no longer has a template set.
    refreshed_admin_user = User.objects.get(id=admin_user.id)
    assert refreshed_admin_user.userprofile.expungement_petition_template == None


@pytest.mark.django_db
def test_clear_missing_templates_doesnt_delete_valid_templates(admin_user):
    # Create a template record in the database
    with open("templates/petitions/790ExpungementTemplate.docx", "rb") as f:
        fl = File(f)
        template = ExpungementPetitionTemplate(name="example", file=fl)
        template.save()
        templateid = template.id
        filepath = os.path.join(settings.MEDIA_ROOT, template.file.name)

    # assign this template to a user.
    admin_user.userprofile.expungement_petition_template = template
    admin_user.userprofile.save()

    # run clear_missing_templates
    clear_missing_petition_templates()

    # the template record in the database should still be present.
    template_still_there = ExpungementPetitionTemplate.objects.get(id=templateid)

    # the user still has a template set.
    refreshed_admin_user = User.objects.get(id=admin_user.id)
    assert refreshed_admin_user.userprofile.expungement_petition_template != None

