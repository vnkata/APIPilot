from typing import Any, Literal
from faker import Faker

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator

class RandomFileGenerator(RandomGenerator):
    """
    A generator that produces random file bytes for various file types (PDF, DOCX, TXT, PNG, JPEG, BMP).

    Attributes:
        file_type (str): The type of file to generate ('pdf', 'docx', 'txt', 'png', 'jpeg', 'bmp').
    """
    description: str = """A generator that produces random file bytes for various file types (PDF, DOCX, TXT, PNG, JPEG, BMP).
    Attributes:
        file_type (str): The type of file to generate ('pdf', 'docx', 'txt', 'png', 'jpeg', 'bmp').
    """

    def __init__(
        self,
        file_type: Literal["pdf", "docx", "txt", "png", "jpeg", "bmp"] = "pdf",
        seed: int | None = None
    ):
        super().__init__(seed)
        self.file_type = file_type.lower()
        self.fake = Faker()
        try:
            from faker_file.providers.pdf_file import PdfFileProvider
            from faker_file.providers.docx_file import DocxFileProvider
            from faker_file.providers.txt_file import TxtFileProvider
            from faker_file.providers.png_file import PngFileProvider
            from faker_file.providers.jpeg_file import JpegFileProvider
            from faker_file.providers.bmp_file import BmpFileProvider
            self.fake.add_provider(PdfFileProvider)
            self.fake.add_provider(DocxFileProvider)
            self.fake.add_provider(TxtFileProvider)
            self.fake.add_provider(PngFileProvider)
            self.fake.add_provider(JpegFileProvider)
            self.fake.add_provider(BmpFileProvider)
        except ImportError:
            pass

    def next_value(self) -> bytes:
        if self.file_type == "pdf":
            return self.fake.pdf_file(raw=True)
        elif self.file_type == "docx":
            return self.fake.docx_file(raw=True)
        elif self.file_type == "txt":
            return self.fake.txt_file(raw=True)
        elif self.file_type == "png":
            return self.fake.png_file(raw=True)
        elif self.file_type == "jpeg":
            return self.fake.jpeg_file(raw=True)
        elif self.file_type == "bmp":
            return self.fake.bmp_file(raw=True)
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")
    def next_fuzz_value(self, strategy: FuzzStrategy) -> Any:
        if strategy == FuzzStrategy.EMPTY:
            return b""

        if strategy == FuzzStrategy.LARGE:
            return b"A" * (1024 * 1024 * 10)

        if strategy == FuzzStrategy.WRONG_TYPE:
            return f"binary_data_{self.rand.getrandbits(32)}"

        if strategy == FuzzStrategy.JUNK:
            return self.rand.randbytes(2048)

        if strategy == FuzzStrategy.CORRUPT:
            valid_file = self.next_value() # Assume next_value() generates valid bytes
            if not valid_file: return b"\xFF\xFF"
            mutable = bytearray(valid_file)
            for i in range(min(16, len(mutable))):
                mutable[i] = self.rand.randint(0, 255)
            return bytes(mutable)
            
        return None
    