from __future__ import annotations

import argparse
import json
from pathlib import Path

from api_testing.backend.app import create_app
from api_testing.backend.settings import BackendSettings


def export_openapi(output: Path, settings: BackendSettings | None = None) -> None:
    app = create_app(settings or BackendSettings.from_env())
    schema = app.openapi()
    output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export APIPilot backend OpenAPI.")
    parser.add_argument("--output", type=Path, default=Path("openapi.json"))
    args = parser.parse_args()
    export_openapi(args.output)


if __name__ == "__main__":
    main()
