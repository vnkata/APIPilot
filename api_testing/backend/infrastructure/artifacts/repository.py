"""Filesystem-backed artifact repository."""

from __future__ import annotations

from pathlib import Path

from pydantic import JsonValue

from api_testing.backend.domain.errors import ArtifactNotFound, InvalidArtifactRequest
from api_testing.backend.domain.models import ArtifactMetadata, Run
from api_testing.backend.infrastructure.artifacts.cache import FileSignatureCache
from api_testing.backend.infrastructure.artifacts.readers import (
    load_csv_rows,
    load_json_file,
    parse_har_session,
    to_utc_datetime,
)
from api_testing.backend.infrastructure.artifacts.registry import (
    KNOWN_ARTIFACTS,
    KNOWN_ARTIFACTS_BY_ID,
    ArtifactDefinition,
    har_artifact_definition,
)


class FileArtifactRepository:
    """Reads APIPilot artifacts from a configured local cache root."""

    def __init__(self, cache_root: Path | str) -> None:
        self.cache_root = Path(cache_root).resolve()
        self._json_cache = FileSignatureCache[JsonValue]()
        self._text_cache = FileSignatureCache[str]()
        self._csv_cache = FileSignatureCache[list[dict[str, str]]]()

    def list_runs(self) -> list[Run]:
        if not self.cache_root.exists():
            return []
        runs: list[Run] = []
        for child in sorted(self.cache_root.iterdir(), key=lambda path: path.name.lower()):
            if not child.is_dir() or child.name in {"tooling"} or child.name.startswith("."):
                continue
            artifacts = self.list_artifacts(child.name)
            runs.append(
                Run(
                    run_name=child.name,
                    artifact_count=len(artifacts),
                    has_history=any(artifact.kind.value == "har_session" for artifact in artifacts),
                    size_bytes=self._directory_size(child),
                    modified_at=to_utc_datetime(child.stat().st_mtime),
                )
            )
        return runs

    def get_run(self, run_name: str) -> Run:
        run_path = self._run_path(run_name)
        if not run_path.is_dir():
            raise ArtifactNotFound(f"Run not found: {run_name}")
        artifacts = self.list_artifacts(run_name)
        return Run(
            run_name=run_name,
            artifact_count=len(artifacts),
            has_history=any(artifact.kind.value == "har_session" for artifact in artifacts),
            size_bytes=self._directory_size(run_path),
            modified_at=to_utc_datetime(run_path.stat().st_mtime),
        )

    def list_artifacts(self, run_name: str) -> list[ArtifactMetadata]:
        run_path = self._run_path(run_name)
        if not run_path.is_dir():
            raise ArtifactNotFound(f"Run not found: {run_name}")

        artifacts: list[ArtifactMetadata] = []
        for definition in KNOWN_ARTIFACTS:
            artifact_path = self._artifact_path(run_name, definition)
            if artifact_path.is_file():
                artifacts.append(self._metadata(run_name, artifact_path, definition))

        for har_path in sorted((run_path / "history").glob("*.har")):
            definition = har_artifact_definition(har_path.stem)
            artifacts.append(self._metadata(run_name, har_path, definition))

        return sorted(artifacts, key=lambda artifact: artifact.artifact_id)

    def get_artifact(self, run_name: str, artifact_id: str) -> ArtifactMetadata:
        for artifact in self.list_artifacts(run_name):
            if artifact.artifact_id == artifact_id:
                return artifact
        raise ArtifactNotFound(f"Artifact not found: {artifact_id}")

    def read_json_artifact(self, run_name: str, artifact_id: str) -> JsonValue:
        path = self._path_for_artifact_id(run_name, artifact_id)
        if path.suffix.lower() not in {".json", ".har"}:
            raise InvalidArtifactRequest(f"Artifact is not JSON: {artifact_id}")
        cached = self._json_cache.get(path)
        if cached is not None:
            return cached
        return self._json_cache.set(path, load_json_file(path))

    def read_text_artifact(self, run_name: str, artifact_id: str) -> str:
        path = self._path_for_artifact_id(run_name, artifact_id)
        cached = self._text_cache.get(path)
        if cached is not None:
            return cached
        return self._text_cache.set(path, path.read_text(encoding="utf-8"))

    def read_csv_rows(self, run_name: str, artifact_id: str) -> list[dict[str, str]]:
        path = self._path_for_artifact_id(run_name, artifact_id)
        if path.suffix.lower() != ".csv":
            raise InvalidArtifactRequest(f"Artifact is not CSV: {artifact_id}")
        cached = self._csv_cache.get(path)
        if cached is not None:
            return [row.copy() for row in cached]
        rows = self._csv_cache.set(path, load_csv_rows(path))
        return [row.copy() for row in rows]

    def list_har_sessions(self, run_name: str):
        run_path = self._run_path(run_name)
        if not run_path.is_dir():
            raise ArtifactNotFound(f"Run not found: {run_name}")
        return [
            self._read_har_path(har_path)
            for har_path in sorted((run_path / "history").glob("*.har"))
        ]

    def read_har_session(self, run_name: str, session_id: str):
        self._reject_unsafe_segment(session_id, "session_id")
        path = self._safe_child_path(run_name, "history", f"{session_id}.har")
        if not path.is_file():
            raise ArtifactNotFound(f"HAR session not found: {session_id}")
        return self._read_har_path(path)

    def _read_har_path(self, path: Path):
        cached = self._json_cache.get(path)
        payload = cached if cached is not None else self._json_cache.set(path, load_json_file(path))
        return parse_har_session(path, payload)

    def _run_path(self, run_name: str) -> Path:
        self._reject_unsafe_path_part(run_name, "run_name")
        return self._safe_child_path(run_name)

    def _artifact_path(self, run_name: str, artifact: ArtifactDefinition) -> Path:
        return self._safe_child_path(run_name, *Path(artifact.relative_path).parts)

    def _path_for_artifact_id(self, run_name: str, artifact_id: str) -> Path:
        self._reject_unsafe_segment(artifact_id, "artifact_id")
        if artifact_id in KNOWN_ARTIFACTS_BY_ID:
            path = self._artifact_path(run_name, KNOWN_ARTIFACTS_BY_ID[artifact_id])
        elif artifact_id.startswith("history_"):
            session_id = artifact_id.removeprefix("history_")
            self._reject_unsafe_segment(session_id, "session_id")
            path = self._safe_child_path(run_name, "history", f"{session_id}.har")
        else:
            raise ArtifactNotFound(f"Artifact not found: {artifact_id}")
        if not path.is_file():
            raise ArtifactNotFound(f"Artifact not found: {artifact_id}")
        return path

    def _metadata(
        self,
        run_name: str,
        artifact_path: Path,
        artifact: ArtifactDefinition,
    ) -> ArtifactMetadata:
        stat = artifact_path.stat()
        return ArtifactMetadata(
            artifact_id=artifact.artifact_id,
            run_name=run_name,
            kind=artifact.kind,
            relative_path=artifact.relative_path,
            media_type=artifact.media_type,
            size_bytes=stat.st_size,
            modified_at=to_utc_datetime(stat.st_mtime),
            raw_supported=artifact.raw_supported,
            summary_supported=artifact.summary_supported,
            raw_policy=artifact.raw_policy,
        )

    def _safe_child_path(self, *parts: str) -> Path:
        path = self.cache_root.joinpath(*parts)
        resolved = path.resolve(strict=False)
        try:
            resolved.relative_to(self.cache_root)
        except ValueError as exc:
            raise InvalidArtifactRequest("Path traversal is not allowed") from exc
        return resolved

    @staticmethod
    def _reject_unsafe_path_part(value: str, field_name: str) -> None:
        path = Path(value)
        if path.is_absolute() or any(part == ".." for part in path.parts):
            raise InvalidArtifactRequest(f"Unsafe {field_name}: {value}")

    @staticmethod
    def _reject_unsafe_segment(value: str, field_name: str) -> None:
        if (
            not value
            or "/" in value
            or "\\" in value
            or value in {".", ".."}
            or Path(value).is_absolute()
        ):
            raise InvalidArtifactRequest(f"Unsafe {field_name}: {value}")

    @staticmethod
    def _directory_size(path: Path) -> int:
        return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())
