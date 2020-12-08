from cleanslate.services.initializers import create_default_petition
from cleanslate.models import ExpungementPetitionTemplate, SealingPetitionTemplate


def test_profile(admin_client):
    create_default_petition(
        ExpungementPetitionTemplate,
        "templates/petitions/790ExpungementTemplate.docx",
        "790ExpungementTemplate",
    )
    create_default_petition(
        SealingPetitionTemplate,
        "templates/petitions/791SealingTemplate.docx",
        "791SealingTemplate",
    )

    profile = admin_client.get("/api/record/profile/")
    assert profile.status_code == 200
    assert "expungement_petition_template_options" in profile.json().keys()
