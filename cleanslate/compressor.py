from typing import Tuple, List
from docxtpl import DocxTemplate
from django.core.files import File
from django.conf import settings
import tempfile
import zipfile
import os
import shutil


class Compressor:
    """ Class for creating a zip file using django's file handling tools. """

    def __init__(self, zip_name: str, file_tuple: List[Tuple[str, DocxTemplate]]):
        """ need to store all the files in file_tuple to a zip named zip_name """
        with tempfile.TemporaryDirectory() as tempdir:
            zip_path = os.path.join(settings.MEDIA_ROOT, zip_name)
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for file_name, docxtemplate in file_tuple:
                    complete_file_name = os.path.join(tempdir, file_name)
                    docxtemplate.save(complete_file_name)
                    zipf.write(complete_file_name, arcname=file_name)
            self.compressed_files = File(zip_path)
            self.path = zip_path
            self.name = zip_name
