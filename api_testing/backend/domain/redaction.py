"""Sensitive-value redaction for artifact bodies and headers."""

from __future__ import annotations

import json
import re

from pydantic import JsonValue

from api_testing.backend.domain.models import SanitizedBody


REDACTED_VALUE = "<REDACTED>"
MAX_BODY_BYTES = 64 * 1024
MAX_PREVIEW_CHARS = 2048
SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "set-cookie",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "passwd",
    "secret",
    "client_secret",
    "api_key",
    "x-api-key",
    "session",
)
_SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)(?:[\"']?)\b("
    r"authorization|cookie|set-cookie|token|access_token|refresh_token|"
    r"password|passwd|secret|client_secret|api_key|x-api-key|session"
    r")\b(?:[\"']?)\s*[:=]\s*(?:[\"']?)[^,\s;&}\]]+"
)


def is_sensitive_key(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(part.replace("-", "_") in normalized for part in SENSITIVE_KEY_PARTS)


def redact_headers(headers: dict[str, JsonValue]) -> dict[str, str]:
    return {
        name: REDACTED_VALUE if is_sensitive_key(name) else str(value)
        for name, value in headers.items()
    }


def sanitize_body(value: JsonValue | str | None) -> SanitizedBody:
    if value in (None, ""):
        return SanitizedBody(
            included=False,
            truncated=False,
            content=None,
            preview=None,
            size_bytes=0,
            redaction_count=0,
        )

    if isinstance(value, str):
        size_bytes = len(value.encode("utf-8"))
        if size_bytes > MAX_BODY_BYTES:
            preview, redactions = _sanitize_preview(value)
            return SanitizedBody(
                included=False,
                truncated=True,
                content=None,
                preview=preview,
                size_bytes=size_bytes,
                redaction_count=redactions,
            )
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            preview, redactions = _sanitize_preview(value)
            return SanitizedBody(
                included=False,
                truncated=False,
                content=None,
                preview=preview,
                size_bytes=size_bytes,
                redaction_count=redactions,
            )
        content, redactions = _sanitize_json(parsed)
        return SanitizedBody(
            included=True,
            truncated=False,
            content=content,
            preview=None,
            size_bytes=size_bytes,
            redaction_count=redactions,
        )

    serialized = json.dumps(value, ensure_ascii=False)
    size_bytes = len(serialized.encode("utf-8"))
    if size_bytes > MAX_BODY_BYTES:
        preview, redactions = _sanitize_preview(serialized)
        return SanitizedBody(
            included=False,
            truncated=True,
            content=None,
            preview=preview,
            size_bytes=size_bytes,
            redaction_count=redactions,
        )
    content, redactions = _sanitize_json(value)
    return SanitizedBody(
        included=True,
        truncated=False,
        content=content,
        preview=None,
        size_bytes=size_bytes,
        redaction_count=redactions,
    )


def _sanitize_json(value: JsonValue) -> tuple[JsonValue, int]:
    if isinstance(value, dict):
        sanitized: dict[str, JsonValue] = {}
        redactions = 0
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                sanitized[str(key)] = REDACTED_VALUE
                redactions += 1
                continue
            sanitized_item, item_redactions = _sanitize_json(item)
            sanitized[str(key)] = sanitized_item
            redactions += item_redactions
        return sanitized, redactions
    if isinstance(value, list):
        sanitized_items: list[JsonValue] = []
        redactions = 0
        for item in value:
            sanitized_item, item_redactions = _sanitize_json(item)
            sanitized_items.append(sanitized_item)
            redactions += item_redactions
        return sanitized_items, redactions
    return value, 0


def _sanitize_preview(value: str) -> tuple[str, int]:
    preview = value[:MAX_PREVIEW_CHARS]
    redactions = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal redactions
        redactions += 1
        key = match.group(1)
        return f"{key}={REDACTED_VALUE}"

    return _SENSITIVE_TEXT_PATTERN.sub(replace, preview), redactions
