from __future__ import annotations

import json
import tempfile
import os
import sys
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Keep the artifact backend E2E fixture independent from optional research-core
# imports performed by api_testing/__init__.py, such as vector DB dependencies.
api_testing_package = types.ModuleType("api_testing")
api_testing_package.__path__ = [str(REPO_ROOT / "api_testing")]
sys.modules.setdefault("api_testing", api_testing_package)

from fastapi.testclient import TestClient

from api_testing.backend.app import create_app
from api_testing.backend.settings import BackendSettings
from tests.fixtures.backend_artifacts import (
    add_combination_artifacts,
    build_artifact_cache,
    write_json,
)


class FixtureBackendHandler(BaseHTTPRequestHandler):
    client: ClassVar[TestClient]

    def do_GET(self) -> None:
        self._proxy("GET")

    def do_POST(self) -> None:
        self._proxy("POST")

    def do_PUT(self) -> None:
        self._proxy("PUT")

    def do_OPTIONS(self) -> None:
        self._proxy("OPTIONS")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _proxy(self, method: str) -> None:
        content_length = int(self.headers.get("content-length", "0") or "0")
        body = self.rfile.read(content_length) if content_length else None
        response = self.client.request(
            method,
            self.path,
            content=body,
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
    fixture_root = Path(fixture_parent.name)
    cache_root = build_artifact_cache(fixture_root)
    add_combination_artifacts(cache_root)
    write_json(
        cache_root / "Run A" / "configuration.json",
        {"base_url": "https://example.test"},
    )
    app = create_app(
        BackendSettings(
            cache_root=cache_root,
            metadata_db_path=fixture_root / "backend.db",
            spec_storage_root=fixture_root / "specs",
            allowed_origins=(allowed_origin,),
            allowed_target_base_urls=("https://example.test",),
            default_request_budget=5,
            default_execution_timeout_seconds=10,
        )
    )
    app.state.combination_review_service.planner_factory = lambda: FakePlanner()
    _install_fake_target_request()
    FixtureBackendHandler.client = TestClient(app)
    server = ThreadingHTTPServer(("127.0.0.1", backend_port), FixtureBackendHandler)
    print(
        f"APIPilot E2E fixture backend on http://127.0.0.1:{backend_port} using {cache_root}",
        flush=True,
    )
    server.serve_forever()


class FakePlanner:
    prompt_version = "e2e-fake-planner-v1"
    last_error = None

    def generate(self, context):
        return [
            {
                "case_id": "e2e-post-case",
                "request": {
                    "method": "POST",
                    "path": "/items",
                    "query": {"limit": 1},
                    "headers": {},
                    "body": {"safe": "visible"},
                },
                "target_truth_vector": {
                    "static_constraint": "true",
                    "dynamic_constraint": "false",
                },
                "rationale": "Deterministic E2E POST draft.",
                "risk": "low",
                "expected_observation": "The fake target returns a small item collection.",
            }
        ]


def _install_fake_target_request() -> None:
    import requests

    class FakeResponse:
        status_code = 200
        headers = {"Content-Type": "application/json"}
        text = json.dumps({"item_count": 1, "items": [{"id": 1, "status": "ACTIVE"}]})
        encoding = "utf-8"
        cookies = type("Cookies", (), {"get_dict": lambda self: {}})()

        def json(self):
            return {"item_count": 1, "items": [{"id": 1, "status": "ACTIVE"}]}

    original_request = requests.request

    def fake_request(method, url, **kwargs):
        if str(url).startswith("https://example.test"):
            return FakeResponse()
        return original_request(method, url, **kwargs)

    requests.request = fake_request


if __name__ == "__main__":
    main()
