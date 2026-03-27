import random
from typing import Any, Literal, Callable
from faker import Faker

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from .random_generator import RandomGenerator


class RandomFileGenerator(RandomGenerator):
    """
    Generate random file data for upload testing.

    Return format:
        (filename: str, content: bytes, content_type: str)
    """

    SUPPORTED_TYPES = ("pdf", "docx", "txt", "png", "jpeg", "bmp")

    MIME_TYPES = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "png": "image/png",
        "jpeg": "image/jpeg",
        "bmp": "image/bmp",
    }

    EXTENSIONS = {
        "pdf": ".pdf",
        "docx": ".docx",
        "txt": ".txt",
        "png": ".png",
        "jpeg": ".jpeg",
        "bmp": ".bmp",
    }
    description: str = """
    A generator that produces random file data for upload testing.
    Attributes:
        file_type (Literal["pdf", "docx", "txt", "png", "jpeg", "bmp"] | None):
            Optional fixed file type to generate. If None, a random supported type is selected.
    """
    def __init__(
        self,
        file_type: Literal["pdf", "docx", "txt", "png", "jpeg", "bmp"] = None,
        seed: int | None = None,
    ):
        super().__init__(seed)

        self.file_type = file_type.lower() if file_type else None
        if self.file_type and self.file_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        self.fake = Faker()
        self._register_providers()

        # map type → generator function
        self._generators: dict[str, Callable[[], tuple[str, bytes, str]]] = {
            t: lambda t=t: self._generate_file(t)
            for t in self.SUPPORTED_TYPES
        }

    # --------------------------
    # Provider registration
    # --------------------------
    def _register_providers(self):
        providers = [
            ("faker_file.providers.pdf_file", "PdfFileProvider"),
            ("faker_file.providers.docx_file", "DocxFileProvider"),
            ("faker_file.providers.txt_file", "TxtFileProvider"),
            ("faker_file.providers.png_file", "PngFileProvider"),
            ("faker_file.providers.jpeg_file", "JpegFileProvider"),
            ("faker_file.providers.bmp_file", "BmpFileProvider"),
        ]

        for module, cls in providers:
            try:
                mod = __import__(module, fromlist=[cls])
                provider_cls = getattr(mod, cls)
                self.fake.add_provider(provider_cls)
            except Exception:
                # fallback silently but safe
                continue

    # --------------------------
    # Core generator
    # --------------------------
    def _generate_file(self, file_type: str) -> tuple[str, bytes, str]:        
        method_name = f"{file_type}_file"

        if hasattr(self.fake, method_name):
            content = getattr(self.fake, method_name)(raw=True)
        else:
            # fallback nếu thiếu faker-file
            content = self.rand.randbytes(1024)

        filename = f"{self.fake.uuid4()}{self.EXTENSIONS[file_type]}"
        content_type = self.MIME_TYPES[file_type]
        return (filename, content, content_type)

    # --------------------------
    # Public API
    # --------------------------
    def next_value(self, context_pool=None, *args, **kwargs) -> tuple[str, bytes, str]:
        file_type = self.file_type
        if  file_type is None:
            file_type = random.choice(self.SUPPORTED_TYPES)
        return self._generators[file_type]()

    # --------------------------
    # Fuzzing
    # --------------------------
    def next_fuzz_value(
        self,
        strategy: FuzzStrategy | None,
        context_pool=None,
        *args,
        **kwargs,
    ) -> Any:

        strategies = [
            FuzzStrategy.EMPTY,
            FuzzStrategy.LARGE,
            FuzzStrategy.WRONG_TYPE,
            FuzzStrategy.JUNK,
            FuzzStrategy.CORRUPT,
        ]

        if strategy is None:
            strategy = self.rand.choice(strategies)

        filename, content, content_type = self.next_value()

        if strategy == FuzzStrategy.EMPTY:
            return (filename, b"", content_type)

        if strategy == FuzzStrategy.LARGE:
            return (filename, b"A" * (10 * 1024 * 1024), content_type)

        if strategy == FuzzStrategy.WRONG_TYPE:
            return f"invalid_file_{self.rand.getrandbits(32)}"

        if strategy == FuzzStrategy.JUNK:
            return (filename, self.rand.randbytes(2048), content_type)

        if strategy == FuzzStrategy.CORRUPT:
            if not content:
                return (filename, b"\xFF\xFF", content_type)

            mutable = bytearray(content)
            for i in range(min(16, len(mutable))):
                mutable[i] = self.rand.randint(0, 255)

            return (filename, bytes(mutable), content_type)

        return None