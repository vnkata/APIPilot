from __future__ import annotations

import ast
from pathlib import Path


def test_clean_architecture_modules_exist():
    expected_modules = [
        "api_testing.backend.api.dependencies",
        "api_testing.backend.api.errors",
        "api_testing.backend.application.ports",
        "api_testing.backend.application.querying",
        "api_testing.backend.application.write_ports",
        "api_testing.backend.application.write_services",
        "api_testing.backend.application.read_services.constraints",
        "api_testing.backend.application.read_services.graphs",
        "api_testing.backend.application.read_services.reports",
        "api_testing.backend.application.services",
        "api_testing.backend.domain.models",
        "api_testing.backend.domain.redaction",
        "api_testing.backend.domain.write_models",
        "api_testing.backend.infrastructure.artifacts.repository",
        "api_testing.backend.infrastructure.spec_storage",
        "api_testing.backend.infrastructure.write_metadata",
    ]

    for module_name in expected_modules:
        __import__(module_name)


def test_application_and_infrastructure_do_not_import_fastapi_or_api_schemas():
    backend_root = Path("api_testing/backend")
    checked_files = [
        *backend_root.joinpath("application").rglob("*.py"),
        *backend_root.joinpath("domain").rglob("*.py"),
        *backend_root.joinpath("infrastructure").rglob("*.py"),
    ]

    assert checked_files
    for path in checked_files:
        source = path.read_text(encoding="utf-8")
        assert "fastapi" not in source
        assert "api_testing.backend.api.schemas" not in source


def test_artifact_query_service_is_thin_facade():
    source = Path("api_testing/backend/application/services.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    private_helpers = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("_")
        and node.name != "__init__"
    ]

    assert "read_json_artifact" not in source
    assert "sanitize_body" not in source
    assert private_helpers == []
