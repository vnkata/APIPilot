from __future__ import annotations

from pathlib import Path

from tests.backend_artifact_fixtures import build_artifact_cache, write_json


def build_explorer_artifact_cache(tmp_path: Path) -> Path:
    cache_root = build_artifact_cache(tmp_path)
    run_dir = cache_root / "Run A"

    write_json(
        run_dir / "static_constraint_miner.json",
        {
            "common": {
                "get-/items": {"return.items[].id": "return.items.id >= 1"},
                "post-/items": {"return.item.name": "required"},
            },
            "request_response": {
                "get-/items": [
                    {
                        "property": "input.limit",
                        "predicate": "input.limit <= return.item_count",
                        "parameter": "limit",
                    }
                ]
            },
            "response_properties": {
                "get-/items": {"return.items[].name": "required"},
                "post-/items": {"return.item.id": "return.item.id >= 1"},
            },
        },
    )
    write_json(
        run_dir / "constraint_miner.json",
        {
            "get-/items": {
                "return.items[].id": "return.items.id >= 1",
                "return.items[].name": "required",
            },
            "post-/items": {
                "return.item.id": "return.item.id >= 1",
                "return.item.name": "required",
            },
        },
    )
    write_json(
        run_dir / "dynamic_constraint_miner.json",
        {
            "constraints": {
                "get-/items": {"return.items[].id": "return.items.id >= 1"},
                "post-/items": {"return.item.name": "return.item.name != null"},
            },
            "group_invariants": {
                "get-/items": [
                    {
                        "pptname": "get-/items:::EXIT",
                        "invariant": "return.items[].id >= 1",
                    }
                ],
                "post-/items": [
                    {
                        "pptname": "post-/items:::EXIT",
                        "invariant": "return.item.name != null",
                    }
                ],
            },
            "raw": [
                {
                    "endpoint": "get-/items",
                    "variable": "return.items[].id",
                    "postmanAssertion": "pm.expect(return_items_id).to.be.at.least(1)",
                },
                {
                    "endpoint": "post-/items",
                    "variable": "return.item.name",
                    "postmanAssertion": "pm.expect(response.item.name).to.exist",
                },
            ],
        },
    )
    write_json(
        run_dir / "heuristic_edges.json",
        [
            {
                "from_node": "post-/items",
                "to_node": "get-/items",
                "similar_parameters": [
                    {
                        "value1": "item.id",
                        "value2": "itemId",
                        "in_value": "response to parameter via heuristic",
                    }
                ],
            }
        ],
    )
    write_json(
        run_dir / "gpt_edges.json",
        [
            {
                "from_node": "post-/items",
                "to_node": "get-/items",
                "similar_parameters": [
                    {
                        "value1": "item.id",
                        "value2": "limit",
                        "in_value": "response to query parameter via gpt",
                    }
                ],
            },
            {
                "from_node": "get-/items",
                "to_node": "post-/items",
                "similar_parameters": [
                    {
                        "value1": "return.items[].name",
                        "value2": "name",
                        "in_value": "candidate response to request body via gpt",
                    }
                ],
            },
        ],
    )
    write_json(
        run_dir / "dependency_sequences.json",
        {
            "get-/items": [
                {
                    "type": "producer-path",
                    "combined_sequences": [["post-/items", "get-/items"]],
                    "params": {
                        "itemId": [
                            {
                                "source_param": "item.id",
                                "source_endpoint": "post-/items",
                            }
                        ]
                    },
                    "score": 2,
                }
            ],
            "post-/items": [
                {
                    "type": "candidate-path",
                    "combined_sequences": [["get-/items", "post-/items"]],
                    "params": {
                        "name": [
                            {
                                "source_param": "return.items[].name",
                                "source_endpoint": "get-/items",
                            }
                        ]
                    },
                    "score": 5,
                }
            ],
        },
    )
    (run_dir / "invariants.csv").write_text(
        "\n".join(
            [
                "pptname;invariant;invariantType;variables;postmanAssertion",
                "get-/items:::EXIT;return.items[].id >= 1;"
                "daikon.inv.unary.scalar.LowerBound;(return.items[].id);"
                "pm.expect(return_items_id).to.be.at.least(1)",
                "post-/items:::EXIT;return.item.name != null;"
                "daikon.inv.unary.string.NonZero;(return.item.name);"
                "pm.expect(response.item.name).to.exist",
            ]
        ),
        encoding="utf-8",
    )
    return cache_root


def build_list_sequence_artifact_cache(tmp_path: Path) -> Path:
    cache_root = build_explorer_artifact_cache(tmp_path)
    write_json(
        cache_root / "Run A" / "dependency_sequences.json",
        [["post-/items", "get-/items"], ["get-/items", "post-/items"]],
    )
    return cache_root
