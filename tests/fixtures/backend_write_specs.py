from __future__ import annotations

import json
from pathlib import Path


def simple_openapi_content() -> str:
    return json.dumps(
        {
            "openapi": "3.0.3",
            "info": {"title": "Items API", "version": "1.0.0"},
            "servers": [{"url": "https://example.test"}],
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "listItems",
                        "summary": "List items",
                        "parameters": [
                            {
                                "name": "limit",
                                "in": "query",
                                "schema": {"type": "integer", "minimum": 1},
                            }
                        ],
                        "responses": {"200": {"description": "OK"}},
                    },
                    "post": {
                        "operationId": "createItem",
                        "summary": "Create item",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"name": {"type": "string"}},
                                    }
                                }
                            }
                        },
                        "responses": {"201": {"description": "Created"}},
                    },
                }
            },
        }
    )


def write_simple_openapi(path: Path) -> None:
    path.write_text(simple_openapi_content(), encoding="utf-8")

