"""Export DuckDB-backed contextual memory to the legacy JSON cache file."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_DB_NAME = "contextual_memory.db"
DEFAULT_JSON_NAME = "contextual_memory.json"


def resolve_paths(source: Path, output: Path | None = None) -> tuple[Path, Path]:
    """Resolve a cache directory or database path to db and json paths."""
    source = source.expanduser()

    if source.suffix.lower() == ".db":
        db_path = source
        default_output = source.with_name(DEFAULT_JSON_NAME)
    else:
        db_path = source / DEFAULT_DB_NAME
        default_output = source / DEFAULT_JSON_NAME

    json_path = output.expanduser() if output is not None else default_output
    return db_path, json_path


def _decode_payload(payload: Any) -> Any:
    if isinstance(payload, (dict, list)):
        return payload
    if payload is None:
        return None
    return json.loads(payload)


def load_contextual_memory_from_db(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"Contextual memory database not found: {db_path}")

    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError(
            "The `duckdb` package is required. Install project dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    try:
        conn = duckdb.connect(str(db_path), read_only=True)
    except Exception as exc:
        raise RuntimeError(
            f"Could not open {db_path}. Close any running APIPilot process or DuckDB "
            "shell that is using the file, then retry."
        ) from exc

    try:
        table_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = 'contextual_memory'
            """
        ).fetchone()[0]
        if table_count == 0:
            raise RuntimeError(
                f"{db_path} does not contain a `contextual_memory` table."
            )

        rows = conn.execute(
            """
            SELECT context_key, CAST(payload AS VARCHAR)
            FROM contextual_memory
            ORDER BY context_key
            """
        ).fetchall()
        data = {}
        for context_key, payload in rows:
            try:
                data[str(context_key)] = _decode_payload(payload)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON payload for context key {context_key!r}."
                ) from exc
        return data
    finally:
        conn.close()


def write_json_atomic(data: dict[str, Any], output_path: Path, indent: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_name(f".{output_path.name}.tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=indent)
        file.write("\n")
    os.replace(temp_path, output_path)


def export_contextual_memory_json(
    source: Path,
    output: Path | None = None,
    indent: int = 2,
) -> tuple[Path, int]:
    if indent < 0:
        raise ValueError("indent must be greater than or equal to 0")

    db_path, json_path = resolve_paths(source, output)
    if db_path.resolve() == json_path.resolve():
        raise ValueError("output path must not be the same as the database path")

    data = load_contextual_memory_from_db(db_path)
    write_json_atomic(data, json_path, indent)
    return json_path, len(data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate contextual_memory.json from a DuckDB contextual_memory.db file."
        )
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=".",
        type=Path,
        help=(
            "Cache directory containing contextual_memory.db, or the .db file itself. "
            "Defaults to the current directory."
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help=(
            "Output JSON path. Defaults to contextual_memory.json next to the source "
            "database."
        ),
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation level. Defaults to 2.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        json_path, context_count = export_contextual_memory_json(
            args.source,
            output=args.output,
            indent=args.indent,
        )
    except Exception as exc:
        parser.exit(1, f"error: {exc}\n")

    print(f"Wrote {json_path} with {context_count} context keys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
