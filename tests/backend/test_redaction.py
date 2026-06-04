from __future__ import annotations


def test_sanitize_body_recursively_redacts_sensitive_keys():
    from api_testing.backend.domain.redaction import REDACTED_VALUE, sanitize_body

    body = {
        "token": "top-secret-token",
        "nested": {
            "client_secret": "top-secret-client",
            "items": [{"password": "top-secret-password", "safe": "visible"}],
        },
    }

    sanitized = sanitize_body(body)

    assert sanitized.included is True
    assert sanitized.truncated is False
    assert sanitized.redaction_count == 3
    assert sanitized.content == {
        "token": REDACTED_VALUE,
        "nested": {
            "client_secret": REDACTED_VALUE,
            "items": [{"password": REDACTED_VALUE, "safe": "visible"}],
        },
    }


def test_sanitize_body_omits_large_unparsed_content():
    from api_testing.backend.domain.redaction import sanitize_body

    large_text = "x" * (64 * 1024 + 1)

    sanitized = sanitize_body(large_text)

    assert sanitized.included is False
    assert sanitized.truncated is True
    assert sanitized.content is None
    assert sanitized.preview == "x" * 2048
    assert sanitized.size_bytes == len(large_text.encode("utf-8"))


def test_sanitize_body_omits_large_parsed_json_content():
    from api_testing.backend.domain.redaction import REDACTED_VALUE, sanitize_body

    body = {
        "client_secret": "test-client-secret",
        "items": ["x" * 2048 for _ in range(40)],
    }

    sanitized = sanitize_body(body)

    assert sanitized.included is False
    assert sanitized.truncated is True
    assert sanitized.content is None
    assert "test-client-secret" not in sanitized.preview
    assert REDACTED_VALUE in sanitized.preview
    assert len(sanitized.preview) <= 2048
    assert sanitized.size_bytes > 64 * 1024


def test_sanitize_body_omits_unparseable_sensitive_text():
    from api_testing.backend.domain.redaction import REDACTED_VALUE, sanitize_body

    sanitized = sanitize_body("password=test-password")

    assert sanitized.included is False
    assert sanitized.content is None
    assert "test-password" not in sanitized.preview
    assert REDACTED_VALUE in sanitized.preview
    assert sanitized.redaction_count >= 1
