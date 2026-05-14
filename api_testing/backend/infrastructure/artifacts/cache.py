"""Small file-signature cache for local artifact reads."""

from __future__ import annotations

from pathlib import Path
from typing import Generic, TypeVar


T = TypeVar("T")


class FileSignatureCache(Generic[T]):
    """Caches values until the source file's mtime or size changes."""

    def __init__(self) -> None:
        self._values: dict[Path, tuple[tuple[int, int], T]] = {}

    def get(self, path: Path) -> T | None:
        signature = self.signature(path)
        cached = self._values.get(path)
        if cached is None or cached[0] != signature:
            return None
        return cached[1]

    def set(self, path: Path, value: T) -> T:
        self._values[path] = (self.signature(path), value)
        return value

    @staticmethod
    def signature(path: Path) -> tuple[int, int]:
        stat = path.stat()
        return stat.st_mtime_ns, stat.st_size

