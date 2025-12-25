import os
from typing import Optional
from faker import Faker
from faker_file.providers.pdf_file import PdfFileProvider, REPORTLAB_PDF_GENERATOR
from faker_file.providers.docx_file import DocxFileProvider
from faker_file.providers.txt_file import TxtFileProvider

from api_testing.data_generator.heuristic_data_generator.BaseProvider import BaseProvider


class FileProvider(BaseProvider):
    """
    Provides methods to generate random file bytes for PDF, DOCX, and TXT formats using Faker.
    """
    def __init__(self, faker_instance: Faker):
        """
        Initialize the FileProvider with a Faker instance and add file providers.

        :param faker_instance: An instance of Faker.
        """
        self.fake = faker_instance
        self.fake.add_provider(PdfFileProvider)
        self.fake.add_provider(DocxFileProvider)
        self.fake.add_provider(TxtFileProvider)

    def pdf(self) -> bytes:
        """
        Generate random PDF file bytes.

        :return: Bytes of a randomly generated PDF file.
        """
        return self.fake.pdf_file(
            raw=True, 
            pdf_generator_cls=REPORTLAB_PDF_GENERATOR
        )

    def docx(self) -> bytes:
        """
        Generate random DOCX file bytes.

        :return: Bytes of a randomly generated DOCX file.
        """
        return self.fake.docx_file(raw=True)

    def txt(self) -> bytes:
        """
        Generate random TXT file bytes.

        :return: Bytes of a randomly generated TXT file.
        """
        return self.fake.txt_file(raw=True)

    def generate_bytes(self, file_type: str = "pdf") -> bytes:
        """
        Central dispatcher for random file bytes based on file type.

        :param file_type: The type of file to generate ('pdf', 'docx', or 'txt').
        :return: Bytes of the generated file.
        """
        ftype = file_type.lower().strip()
        if ftype == "pdf":
            return self.pdf()
        elif ftype == "docx":
            return self.docx()
        return self.txt()