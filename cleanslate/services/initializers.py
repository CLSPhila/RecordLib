import os
from django.core.files import File
from django.conf import settings
from cleanslate.models import ExpungementPetitionTemplate, SealingPetitionTemplate


def create_default_petition(TemplateModel, template_path, new_name):
    default_petitions = TemplateModel.objects.filter(default=True)
    if len(default_petitions) == 0:
        # if no exp. petition default, create one.
        with open(template_path, "rb") as pet:
            new_petition = File(pet)
            new_petition.name = new_name
            template_model = TemplateModel(
                name=new_name, file=new_petition, default=True
            )
            template_model.save()
            return template_model


def clear_template_if_file_missing(template):
    """
    Check on template - if the file it points to is missing, delete this template from the database.
    """
    path = os.path.join(settings.MEDIA_ROOT, template.file.name)
    if not os.path.exists(path):
        template.delete()


def clear_missing_petition_templates():
    """
    Review stored petition templates. 

    If any database records of petition templates point to files that don't exist, delete these database records.
    """
    for template in ExpungementPetitionTemplate.objects.all():
        clear_template_if_file_missing(template)

    for template in SealingPetitionTemplate.objects.all():
        clear_template_if_file_missing(template)
