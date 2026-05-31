"""Filesystem storage for uploaded OpenAPI specifications."""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.write_models import StoredSpec


class FileSpecStorage:
    """Stores user-uploaded OpenAPI specifications under a configured root."""

    def __init__(self, storage_root: Path | str) -> None:
        self.storage_root = Path(storage_root).resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def save_spec(
        self,
        filename: str,
        content: str,
        *,
        spec_id: str | None = None,
    ) -> StoredSpec:
        if not filename.strip():
            raise InvalidArtifactRequest("filename is required")
        if not content.strip():
            raise InvalidArtifactRequest("content is required")

        safe_name = _safe_filename(filename)
        identifier = spec_id or uuid.uuid4().hex
        storage_name = f"{identifier}-{safe_name}"
        storage_path = self._safe_child_path(storage_name)
        storage_path.write_text(content, encoding="utf-8")

        return StoredSpec(
            filename=filename,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            storage_path=Path(storage_name),
        )

    def read_spec(self, storage_path: Path) -> str:
        path = self._resolve_storage_path(storage_path)
        if not path.is_file():
            raise InvalidArtifactRequest(f"Stored spec not found: {storage_path}")
        return path.read_text(encoding="utf-8")

    def _resolve_storage_path(self, storage_path: Path) -> Path:
        if storage_path.is_absolute():
            resolved = storage_path.resolve(strict=False)
        else:
            resolved = self._safe_child_path(*storage_path.parts)
        try:
            resolved.relative_to(self.storage_root)
        except ValueError as exc:
            raise InvalidArtifactRequest("Spec path traversal is not allowed") from exc
        return resolved

    def _safe_child_path(self, *parts: str) -> Path:
        resolved = self.storage_root.joinpath(*parts).resolve(strict=False)
        try:
            resolved.relative_to(self.storage_root)
        except ValueError as exc:
            raise InvalidArtifactRequest("Spec path traversal is not allowed") from exc
        return resolved


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip()
    if name in {"", ".", ".."}:
        raise InvalidArtifactRequest("filename is unsafe")
    stem = Path(name).stem or "spec"
    suffix = Path(name).suffix.lower() or ".json"
    if suffix not in {".json", ".yaml", ".yml"}:
        suffix = ".json"
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "-", stem).strip(".-") or "spec"
    return f"{safe_stem}{suffix}"

