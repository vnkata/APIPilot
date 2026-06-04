from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURE_MTIME = 1767225600  # 2026-01-01T00:00:00Z


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_artifact_cache(tmp_path: Path) -> Path:
    cache_root = tmp_path / ".cache"
    run_dir = cache_root / "Run A"
    history_dir = run_dir / "history"
    history_dir.mkdir(parents=True)
    (cache_root / "tooling").mkdir()

    write_json(
        run_dir / "specification.json",
        {
            "operations": {
                "get-/items": {
                    "uuid": "get-/items",
                    "operation_id": "ListItems",
                    "endpoint_path": "/items",
                    "http_method": "get",
                    "parameters": {
                        "limit": {
                            "name": "limit",
                            "in_value": "query",
                            "schema": {"type": "integer", "minimum": 1},
                        }
                    },
                    "request_body": {},
                    "responses": {"200": {"description": "OK"}},
                },
                "post-/items": {
                    "uuid": "post-/items",
                    "operation_id": "CreateItem",
                    "endpoint_path": "/items",
                    "http_method": "post",
                    "parameters": {},
                    "request_body": {"type": "object"},
                    "responses": {"201": {"description": "Created"}},
                },
            }
        },
    )
    write_json(
        run_dir / "reports.json",
        {
            "get-/items": {"200": 1, "404": 1},
            "post-/items": {"201": 1},
        },
    )
    write_json(
        run_dir / "semantic_property_dependency_graph.json",
        {
            "nodes": ["get-/items", "post-/items"],
            "edges": [
                {
                    "from_node": "post-/items",
                    "to_node": "get-/items",
                    "similar_parameters": [
                        {
                            "value1": "item.id",
                            "value2": "itemId",
                            "in_value": "response to parameter via test",
                        }
                    ],
                }
            ],
        },
    )
    write_json(
        run_dir / "static_constraint_miner.json",
        {
            "common": {
                "get-/items": {"return.items[].id": "return.items.id >= 1"}
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
                "get-/items": {"return.items[].name": "required"}
            },
        },
    )
    write_json(
        run_dir / "static_constraint_miner_request_response.json",
        {
            "get-/items": [
                {
                    "property": "input.limit",
                    "predicate": "input.limit <= return.item_count",
                    "parameter": "limit",
                }
            ]
        },
    )
    write_json(
        run_dir / "dynamic_constraint_miner.json",
        {
            "constraints": {
                "get-/items": {"return.items[].id": "return.items.id >= 1"}
            },
            "group_invariants": {
                "get-/items": [
                    {
                        "pptname": "get-/items:::EXIT",
                        "invariant": "return.items.id >= 1",
                    }
                ]
            },
            "raw": [
                {
                    "endpoint": "get-/items",
                    "variable": "return.items[].id",
                    "postmanAssertion": "pm.expect(return_items_id).to.be.at.least(1)",
                }
            ],
        },
    )
    write_json(
        run_dir / "constraint_miner.json",
        {
            "get-/items": {
                "return.items[].id": "return.items.id >= 1",
                "return.items[].name": "required",
            }
        },
    )
    write_json(
        run_dir / "test_cases.json",
        [
            {
                "test_case_id": "tc-1",
                "operation_id": "get-/items",
                "path": "/items",
                "http_method": "get",
                "parameters": {"limit": 1},
                "request_body": {},
                "status_code": 200,
                "response_body": json.dumps({"items": [{"id": 1, "name": "alpha"}]}),
            },
            {
                "test_case_id": "tc-2",
                "operation_id": "get-/items",
                "path": "/items",
                "http_method": "get",
                "parameters": {"limit": 1},
                "request_body": {
                    "client_secret": "test-client-secret",
                    "safe": "visible",
                },
                "status_code": 404,
                "response_body": json.dumps(
                    {"error": "missing", "token": "test-response-token"}
                ),
            },
        ],
    )
    (run_dir / "invariants.csv").write_text(
        "\n".join(
            [
                "pptname;invariant;invariantType;variables;postmanAssertion",
                "get-/items:::EXIT;return.items.id >= 1;"
                "daikon.inv.unary.scalar.LowerBound;(return.items.id);"
                "pm.expect(return_items_id).to.be.at.least(1)",
            ]
        ),
        encoding="utf-8",
    )
    write_json(
        history_dir / "session-1.har",
        {
            "log": {
                "version": "1.2",
                "creator": {"name": "pytest", "version": "1.0"},
                "sessionId": "session-1",
                "entries": [
                    {
                        "startedDateTime": "2026-01-01T00:00:00Z",
                        "time": 12.5,
                        "request": {
                            "method": "GET",
                            "url": "https://example.test/items",
                            "headers": [
                                {
                                    "name": "Authorization",
                                    "value": "Bearer test-secret",
                                },
                                {"name": "Accept", "value": "application/json"},
                            ],
                            "queryString": [{"name": "limit", "value": "1"}],
                            "postData": {
                                "text": json.dumps(
                                    {
                                        "unsafe": "body",
                                        "password": "test-password",
                                    }
                                )
                            },
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "headers": [
                                {"name": "Set-Cookie", "value": "session=secret"},
                                {
                                    "name": "Content-Type",
                                    "value": "application/json",
                                },
                            ],
                            "content": {
                                "mimeType": "application/json",
                                "text": json.dumps(
                                    {
                                        "items": [{"id": 1}],
                                        "access_token": "test-access-token",
                                    }
                                ),
                            },
                        },
                    }
                ],
            }
        },
    )
    _build_canada_holidays_medium(cache_root)
    _set_deterministic_mtime(cache_root)
    return cache_root


def _set_deterministic_mtime(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda current: len(current.parts), reverse=True):
        os.utime(path, (FIXTURE_MTIME, FIXTURE_MTIME))
    os.utime(root, (FIXTURE_MTIME, FIXTURE_MTIME))


def add_combination_artifacts(cache_root: Path, run_name: str = "Run A") -> Path:
    run_dir = cache_root / run_name
    write_json(
        run_dir / "combine_constraint_miners.json",
        {
            "get-/items": {
                "return.items[].id": {
                    "endpoint": "get-/items",
                    "property": "return.items[].id",
                    "static_constraint": "return.items.id >= 1",
                    "dynamic_constraint": "return.items.id >= 1",
                    "status": "RESOLVED",
                    "relation": "EQUIVALENT",
                    "runtime_verdict": "BOTH_TRUE",
                    "final_constraint": "return.items.id >= 1 and return.items.id <= 100",
                    "reason": "Resolved by equivalent static and dynamic evidence.",
                    "counter_example": {
                        "staged_payload": {
                            "endpoint_path": "/items",
                            "http_method": "get",
                            "headers": {"Authorization": "Bearer combo-secret"},
                            "parameters": {"limit": 1},
                            "body": {"api_key": "combo-api-key", "safe": "visible"},
                        },
                        "server_actual_response": {
                            "status_code": 200,
                            "set_cookie": "combo-cookie",
                        },
                    },
                    "runtime_evaluation": {
                        "cases_executed": 1,
                        "cases_evaluated": 1,
                        "case_verdicts": ["BOTH_TRUE"],
                    },
                    "validation_cases": [
                        {
                            "case_number": 1,
                            "request": {
                                "headers": {"Authorization": "Bearer case-secret"},
                                "body": {"password": "case-password"},
                            },
                            "response_payload": {
                                "items": [{"id": 1}],
                                "token": "case-response-token",
                            },
                            "runtime_verdict": "BOTH_TRUE",
                        }
                    ],
                },
                "return.items[].status": {
                    "endpoint": "get-/items",
                    "property": "return.items[].status",
                    "static_constraint": "return.items.status one of {ACTIVE}",
                    "dynamic_constraint": "return.items.status one of {INACTIVE}",
                    "status": "CONFLICT",
                    "relation": "DISJOINT",
                    "runtime_verdict": None,
                    "final_constraint": None,
                    "reason": "CONFLICT_PENDING: Runtime verification is required.",
                    "counter_example": None,
                },
                "malformed": "not a record",
            }
        },
    )
    _write_contextual_memory_db(
        run_dir / "contextual_memory.db",
        {
            "get-/items": {
                "whitelist": [{"id": 1, "token": "memory-token"}],
                "blacklist": [{"id": 0}],
            },
            "item": [{"id": 1, "secret": "memory-secret"}],
        },
    )
    _set_deterministic_mtime(cache_root)
    return cache_root


def _write_contextual_memory_db(path: Path, contexts: dict[str, object]) -> None:
    import duckdb

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contextual_memory (
                context_key VARCHAR PRIMARY KEY,
                payload JSON NOT NULL,
                updated_at TIMESTAMP
            )
            """
        )
        for context_key, payload in contexts.items():
            conn.execute(
                """
                INSERT OR REPLACE INTO contextual_memory (context_key, payload, updated_at)
                VALUES (?, CAST(? AS JSON), to_timestamp(?))
                """,
                [context_key, json.dumps(payload), FIXTURE_MTIME],
            )
    finally:
        conn.close()


def _build_canada_holidays_medium(cache_root: Path) -> None:
    run_dir = cache_root / "Canada Holidays Medium"
    history_dir = run_dir / "history"
    history_dir.mkdir(parents=True)

    operations = {
        "get-/api/v1/holidays": {
            "uuid": "get-/api/v1/holidays",
            "operation_id": "ListHolidays",
            "endpoint_path": "/api/v1/holidays",
            "http_method": "get",
            "parameters": {
                "year": {
                    "name": "year",
                    "in_value": "query",
                    "schema": {"type": "integer", "minimum": 2015, "maximum": 2030},
                },
                "province": {
                    "name": "province",
                    "in_value": "query",
                    "schema": {"type": "string", "enum": ["ON", "QC", "BC", "AB"]},
                },
            },
            "request_body": {},
            "responses": {
                "200": {"description": "Holiday collection"},
                "400": {"description": "Invalid query"},
                "404": {"description": "Province not found"},
            },
        },
        "get-/api/v1/holidays/{id}": {
            "uuid": "get-/api/v1/holidays/{id}",
            "operation_id": "GetHoliday",
            "endpoint_path": "/api/v1/holidays/{id}",
            "http_method": "get",
            "parameters": {
                "id": {
                    "name": "id",
                    "in_value": "path",
                    "schema": {"type": "integer", "minimum": 1},
                }
            },
            "request_body": {},
            "responses": {
                "200": {"description": "Holiday detail"},
                "404": {"description": "Holiday not found"},
            },
        },
        "get-/api/v1/provinces": {
            "uuid": "get-/api/v1/provinces",
            "operation_id": "ListProvinces",
            "endpoint_path": "/api/v1/provinces",
            "http_method": "get",
            "parameters": {},
            "request_body": {},
            "responses": {"200": {"description": "Province collection"}},
        },
        "get-/api/v1/status": {
            "uuid": "get-/api/v1/status",
            "operation_id": "GetStatus",
            "endpoint_path": "/api/v1/status",
            "http_method": "get",
            "parameters": {},
            "request_body": {},
            "responses": {
                "200": {"description": "Backend status"},
                "503": {"description": "Backend unavailable"},
            },
        },
    }

    write_json(run_dir / "specification.json", {"operations": operations})
    write_json(
        run_dir / "configuration.json",
        {
            "base_url": "https://canada-holidays.example.test",
            "execution_mode": "fixture",
            "sanitized": True,
        },
    )
    write_json(
        run_dir / "reports.json",
        {
            "get-/api/v1/holidays": {"200": 18, "400": 1, "404": 1},
            "get-/api/v1/holidays/{id}": {"200": 6, "404": 2},
            "get-/api/v1/provinces": {"200": 5},
            "get-/api/v1/status": {"200": 2, "503": 1},
        },
    )
    write_json(
        run_dir / "semantic_property_dependency_graph.json",
        {
            "nodes": list(operations),
            "edges": [
                {
                    "from_node": "get-/api/v1/provinces",
                    "to_node": "get-/api/v1/holidays",
                    "similar_parameters": [
                        {
                            "value1": "provinces[].id",
                            "value2": "province",
                            "in_value": "response to query parameter",
                        }
                    ],
                },
                {
                    "from_node": "get-/api/v1/holidays",
                    "to_node": "get-/api/v1/holidays/{id}",
                    "similar_parameters": [
                        {
                            "value1": "holidays[].id",
                            "value2": "id",
                            "in_value": "response to path parameter",
                        }
                    ],
                },
                {
                    "from_node": "get-/api/v1/status",
                    "to_node": "get-/api/v1/holidays",
                    "similar_parameters": [
                        {
                            "value1": "status.available",
                            "value2": "holiday query readiness",
                            "in_value": "status precondition",
                        }
                    ],
                },
            ],
        },
    )
    write_json(
        run_dir / "dependency_sequences.json",
        [
            ["get-/api/v1/status", "get-/api/v1/provinces", "get-/api/v1/holidays"],
            ["get-/api/v1/holidays", "get-/api/v1/holidays/{id}"],
        ],
    )
    write_json(
        run_dir / "static_constraint_miner.json",
        {
            "common": {
                "get-/api/v1/holidays": {
                    "input.year": "input.year >= 2015 && input.year <= 2030",
                    "return.holidays[].id": "required",
                },
                "get-/api/v1/holidays/{id}": {
                    "input.id": "input.id >= 1",
                },
            },
            "request_response": {
                "get-/api/v1/holidays": {
                    "input.province": "input.province in return.provinces",
                    "input.year": "return.year == input.year",
                },
                "get-/api/v1/holidays/{id}": {
                    "input.id": "return.id == input.id",
                },
            },
            "response_properties": {
                "get-/api/v1/holidays": {
                    "return.holidays[].date": "matches YYYY-MM-DD",
                    "return.holidays[].federal": "boolean",
                },
                "get-/api/v1/provinces": {
                    "return.provinces[].id": "two-letter province code",
                },
            },
        },
    )
    write_json(
        run_dir / "dynamic_constraint_miner.json",
        {
            "constraints": {
                "get-/api/v1/holidays": {
                    "return.holidays[].date": "return.holidays.date >= input.year-01-01",
                    "return.holidays[].province": "return.holidays.province == input.province",
                },
                "get-/api/v1/holidays/{id}": {
                    "return.id": "return.id == input.id",
                },
                "get-/api/v1/provinces": {
                    "return.provinces[].id": "return.provinces.id in {ON, QC, BC, AB}",
                },
            },
            "group_invariants": {
                "get-/api/v1/holidays": [
                    {
                        "pptname": "get-/api/v1/holidays:::EXIT",
                        "invariant": "return.holidays[].date != null",
                    },
                    {
                        "pptname": "get-/api/v1/holidays:::EXIT",
                        "invariant": "return.holidays[].name != null",
                    },
                ],
                "get-/api/v1/holidays/{id}": [
                    {
                        "pptname": "get-/api/v1/holidays/{id}:::EXIT",
                        "invariant": "return.id == input.id",
                    }
                ],
            },
            "raw": {
                "get-/api/v1/holidays": [
                    "return.holidays[].date != null",
                    "return.holidays[].name != null",
                ]
            },
        },
    )
    write_json(
        run_dir / "constraint_miner.json",
        {
            "get-/api/v1/holidays": {
                "input.year": "input.year >= 2015 && input.year <= 2030",
                "return.holidays[].date": "matches YYYY-MM-DD",
                "return.holidays[].province": "return.holidays.province == input.province",
            },
            "get-/api/v1/holidays/{id}": {
                "input.id": "input.id >= 1",
                "return.id": "return.id == input.id",
            },
            "get-/api/v1/provinces": {
                "return.provinces[].id": "return.provinces.id in {ON, QC, BC, AB}",
            },
        },
    )
    write_json(
        run_dir / "static_constraint_miner_request_response.json",
        {
            "get-/api/v1/holidays": [
                {
                    "property": "input.province",
                    "predicate": "input.province in return.provinces",
                    "parameter": "province",
                },
                {
                    "property": "input.year",
                    "predicate": "return.year == input.year",
                    "parameter": "year",
                },
            ],
            "get-/api/v1/holidays/{id}": [
                {
                    "property": "input.id",
                    "predicate": "return.id == input.id",
                    "parameter": "id",
                }
            ],
        },
    )
    write_json(run_dir / "test_cases.json", _canada_holidays_test_cases())
    write_json(
        run_dir / "gpt-4.1-mini_usages.json",
        {
            "currency": "USD",
            "prompt_tokens": 1123,
            "completion_tokens": 456,
            "sanitized": True,
        },
    )
    (run_dir / "invariants.csv").write_text(
        "\n".join(
            [
                "pptname;invariant;invariantType;variables;postmanAssertion",
                "get-/api/v1/holidays&get-/api/v1/holidays&200&holidays&provinces():::EXIT;return.holidays[].date != null;"
                "daikon.inv.unary.string.NonZero;(return.holidays.date);"
                "pm.expect(holiday.date).to.exist",
                "get-/api/v1/holidays:::EXIT;return.holidays[].federal one of {true,false};"
                "daikon.inv.unary.scalar.OneOfScalar;(return.holidays.federal);"
                "pm.expect([true,false]).to.include(holiday.federal)",
                "get-/api/v1/holidays/{id}:::EXIT;return.id == input.id;"
                "daikon.inv.binary.twoScalar.IntEqual;(return.id,input.id);"
                "pm.expect(response.id).to.eql(request.id)",
                "get-/api/v1/provinces:::EXIT;return.provinces[].id != null;"
                "daikon.inv.unary.string.NonZero;(return.provinces.id);"
                "pm.expect(province.id).to.exist",
            ]
        ),
        encoding="utf-8",
    )
    write_json(history_dir / "session-medium.har", _canada_holidays_har("session-medium"))
    write_json(history_dir / "session-regression.har", _canada_holidays_har("session-regression"))


def _canada_holidays_test_cases() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    provinces = ["ON", "QC", "BC", "AB"]
    for index in range(24):
        province = provinces[index % len(provinces)]
        status_code = 200 if index < 18 else 400 if index < 21 else 404
        records.append(
            {
                "test_case_id": f"medium-holidays-{index + 1:02d}",
                "operation_id": "get-/api/v1/holidays",
                "path": "/api/v1/holidays",
                "http_method": "get",
                "parameters": {
                    "province": province,
                    "year": 2024 + (index % 2),
                },
                "request_body": {},
                "status_code": status_code,
                "response_body": json.dumps(
                    {
                        "holidays": [
                            {
                                "id": index + 1,
                                "date": f"2025-0{(index % 9) + 1}-01",
                                "federal": index % 3 == 0,
                                "name": f"Fixture Holiday {index + 1}",
                                "province": province,
                            }
                        ],
                        "access_token": f"medium-token-{index + 1}",
                    }
                ),
            }
        )

    for index in range(8):
        status_code = 200 if index < 6 else 404
        records.append(
            {
                "test_case_id": f"medium-holiday-detail-{index + 1:02d}",
                "operation_id": "get-/api/v1/holidays/{id}",
                "path": f"/api/v1/holidays/{index + 1}",
                "http_method": "get",
                "parameters": {"id": index + 1},
                "request_body": {},
                "status_code": status_code,
                "response_body": json.dumps(
                    {
                        "id": index + 1,
                        "name": f"Fixture Holiday {index + 1}",
                        "secret_note": f"internal-note-{index + 1}",
                    }
                ),
            }
        )

    for index, province in enumerate(provinces + ["YT"], start=1):
        records.append(
            {
                "test_case_id": f"medium-province-{index:02d}",
                "operation_id": "get-/api/v1/provinces",
                "path": "/api/v1/provinces",
                "http_method": "get",
                "parameters": {},
                "request_body": {},
                "status_code": 200,
                "response_body": json.dumps(
                    {
                        "provinces": [{"id": province, "name": f"Province {province}"}],
                        "api_key": f"province-key-{index}",
                    }
                ),
            }
        )

    for index, status_code in enumerate([200, 200, 503], start=1):
        records.append(
            {
                "test_case_id": f"medium-status-{index:02d}",
                "operation_id": "get-/api/v1/status",
                "path": "/api/v1/status",
                "http_method": "get",
                "parameters": {},
                "request_body": {},
                "status_code": status_code,
                "response_body": json.dumps(
                    {"available": status_code == 200, "session_token": f"status-{index}"}
                ),
            }
        )
    return records


def _canada_holidays_har(session_id: str) -> dict[str, object]:
    return {
        "log": {
            "version": "1.2",
            "creator": {"name": "pytest", "version": "1.0"},
            "sessionId": session_id,
            "entries": [
                {
                    "startedDateTime": "2026-01-01T00:00:00Z",
                    "time": 31.25,
                    "request": {
                        "method": "GET",
                        "url": "https://canada-holidays.example.test/api/v1/holidays?year=2025&province=ON",
                        "headers": [
                            {"name": "Authorization", "value": "Bearer medium-secret"},
                            {"name": "Accept", "value": "application/json"},
                        ],
                        "queryString": [
                            {"name": "year", "value": "2025"},
                            {"name": "province", "value": "ON"},
                        ],
                        "postData": {
                            "text": json.dumps(
                                {"probe": "holidays", "client_secret": "medium-client"}
                            )
                        },
                    },
                    "response": {
                        "status": 200,
                        "statusText": "OK",
                        "headers": [
                            {"name": "Content-Type", "value": "application/json"},
                            {"name": "Set-Cookie", "value": "fixture=session"},
                        ],
                        "content": {
                            "mimeType": "application/json",
                            "text": json.dumps(
                                {
                                    "holidays": [{"id": 1, "name": "New Year's Day"}],
                                    "access_token": "medium-access-token",
                                }
                            ),
                        },
                    },
                }
            ],
        }
    }
