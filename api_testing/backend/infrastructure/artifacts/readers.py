"""Artifact file readers and shape parsers."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import JsonValue

from api_testing.backend.domain.errors import InvalidArtifactRequest
from api_testing.backend.domain.models import HarSession, SanitizedHarEntry
from api_testing.backend.domain.redaction import redact_headers, sanitize_body


def to_utc_datetime(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def load_json_text(text: str) -> JsonValue:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise InvalidArtifactRequest("Artifact contains invalid JSON") from exc


def load_json_file(path: Path) -> JsonValue:
    return load_json_text(path.read_text(encoding="utf-8"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter=";"))


def parse_jsonish(value: JsonValue | str | None) -> JsonValue | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def parse_har_session(path: Path, payload: JsonValue) -> HarSession:
    log = payload.get("log", {}) if isinstance(payload, dict) else {}
    entries_raw = log.get("entries", []) if isinstance(log, dict) else []
    entries = entries_raw if isinstance(entries_raw, list) else []
    session_id = log.get("sessionId", path.stem) if isinstance(log, dict) else path.stem
    return HarSession(
        session_id=str(session_id),
        entry_count=len(entries),
        size_bytes=path.stat().st_size,
        modified_at=to_utc_datetime(path.stat().st_mtime),
        entries=[
            _parse_har_entry(str(session_id), index, entry)
            for index, entry in enumerate(entries)
            if isinstance(entry, dict)
        ],
    )


def name_value_items(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, list):
        return {}
    items: dict[str, JsonValue] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if name is None:
            continue
        items[str(name).lower()] = item.get("value")
    return items


def _parse_har_entry(
    session_id: str,
    index: int,
    entry: dict[str, JsonValue],
) -> SanitizedHarEntry:
    request = entry.get("request", {})
    response = entry.get("response", {})
    request_map = request if isinstance(request, dict) else {}
    response_map = response if isinstance(response, dict) else {}
    post_data = request_map.get("postData", {})
    content = response_map.get("content", {})
    post_data_map = post_data if isinstance(post_data, dict) else {}
    content_map = content if isinstance(content, dict) else {}

    return SanitizedHarEntry(
        entry_id=f"{session_id}:{index}",
        started_at=_optional_str(entry.get("startedDateTime")),
        duration_ms=_to_float_or_none(entry.get("time")),
        request_method=_optional_str(request_map.get("method")),
        request_url=_optional_str(request_map.get("url")),
        request_headers=redact_headers(name_value_items(request_map.get("headers", []))),
        query_params=name_value_items(request_map.get("queryString", [])),
        request_body=sanitize_body(post_data_map.get("text")),
        response_status=_to_int_or_none(response_map.get("status")),
        response_status_text=_optional_str(response_map.get("statusText")),
        response_headers=redact_headers(name_value_items(response_map.get("headers", []))),
        response_body=sanitize_body(content_map.get("text")),
    )


def _optional_str(value: JsonValue) -> str | None:
    return None if value is None else str(value)


def _to_int_or_none(value: JsonValue) -> int | None:
    if not isinstance(value, bool | int | float | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float_or_none(value: JsonValue) -> float | None:
    if not isinstance(value, bool | int | float | str):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

