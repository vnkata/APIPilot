from __future__ import annotations

import tempfile
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from api_testing.backend.app import create_app
from api_testing.backend.settings import BackendSettings
from tests.backend_artifact_fixtures import build_artifact_cache


class FixtureBackendHandler(BaseHTTPRequestHandler):
    client: ClassVar[TestClient]

    def do_GET(self) -> None:
        self._proxy("GET")

    def do_OPTIONS(self) -> None:
        self._proxy("OPTIONS")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _proxy(self, method: str) -> None:
        response = self.client.request(
            method,
            self.path,
            headers={key: value for key, value in self.headers.items()},
        )
        self.send_response(response.status_code)

        skipped_headers = {"content-length", "transfer-encoding", "connection"}
        for key, value in response.headers.items():
            if key.lower() not in skipped_headers:
                self.send_header(key, value)

        body = response.content
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        if method != "OPTIONS":
            self.wfile.write(body)


def main() -> None:
    backend_port = int(os.environ.get("APIPILOT_E2E_BACKEND_PORT", "8765"))
    allowed_origin = os.environ.get(
        "APIPILOT_E2E_ALLOWED_ORIGIN",
        "http://127.0.0.1:5174",
    )
    fixture_parent = tempfile.TemporaryDirectory(prefix="apipilot-e2e-")
    cache_root = build_artifact_cache(Path(fixture_parent.name))
    app = create_app(
        BackendSettings(
            cache_root=cache_root,
            allowed_origins=(allowed_origin,),
        )
    )
    FixtureBackendHandler.client = TestClient(app)
    server = ThreadingHTTPServer(("127.0.0.1", backend_port), FixtureBackendHandler)
    print(
        f"APIPilot E2E fixture backend on http://127.0.0.1:{backend_port} using {cache_root}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
