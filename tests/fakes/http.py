from __future__ import annotations

import json
from typing import Any


class FakeCookies:
    def __init__(self, values: dict[str, str] | None = None):
        self._values = dict(values or {})

    def get_dict(self) -> dict[str, str]:
        return dict(self._values)


class FakeJsonResponse:
    def __init__(
        self,
        payload: Any,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json"}
        self.text = json.dumps(payload)
        self.content = self.text.encode("utf-8")
        self.cookies = FakeCookies(cookies)
        self.encoding = "utf-8"

    def json(self) -> Any:
        return self._payload
