"""Create a smaller ohsome OpenAPI dataset with a fixed number of endpoints."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path


DEFAULT_INPUT = Path("datasets/ohsome.json")
DEFAULT_OUTPUT = Path("datasets/ohsome_20_endpoint.json")
DEFAULT_LIMIT = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trim the ohsome OpenAPI dataset to the first N path endpoints."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Source OpenAPI JSON file. Defaults to {DEFAULT_INPUT}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Trimmed OpenAPI JSON file. Defaults to {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Number of path endpoints to keep. Defaults to {DEFAULT_LIMIT}.",
    )
    return parser.parse_args()


def cut_openapi_paths(spec: dict, limit: int) -> dict:
    if limit < 1:
        raise ValueError("--limit must be at least 1")

    paths = spec.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("Input spec does not contain a JSON object at 'paths'")

    selected_paths = dict(list(paths.items())[:limit])
    if len(selected_paths) < limit:
        raise ValueError(
            f"Input spec only has {len(selected_paths)} path endpoints; requested {limit}"
        )

    trimmed_spec = deepcopy(spec)
    trimmed_spec["paths"] = selected_paths
    return trimmed_spec


def main() -> None:
    args = parse_args()

    with args.input.open("r", encoding="utf-8") as source:
        spec = json.load(source)

    trimmed_spec = cut_openapi_paths(spec, args.limit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as target:
        json.dump(trimmed_spec, target, indent=2, ensure_ascii=False)
        target.write("\n")

    print(
        f"Wrote {args.output} with {len(trimmed_spec['paths'])} path endpoints "
        f"from {args.input}"
    )


if __name__ == "__main__":
    main()
