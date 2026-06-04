from __future__ import annotations

import pytest

from tests.fixtures.backend_artifacts import build_artifact_cache, write_json


def test_repository_lists_runs_and_excludes_tooling(tmp_path):
    from api_testing.backend.repository import FileArtifactRepository

    cache_root = build_artifact_cache(tmp_path)
    repository = FileArtifactRepository(cache_root)

    runs = repository.list_runs()

    assert [run.run_name for run in runs] == ["Canada Holidays Medium", "Run A"]
    assert runs[0].artifact_count >= 7
    assert runs[0].has_history is True


def test_repository_catalogs_known_artifacts_with_stable_ids(tmp_path):
    from api_testing.backend.repository import FileArtifactRepository

    cache_root = build_artifact_cache(tmp_path)
    repository = FileArtifactRepository(cache_root)

    artifact_ids = {
        artifact.artifact_id for artifact in repository.list_artifacts("Run A")
    }

    assert {
        "specification",
        "reports",
        "semantic_property_dependency_graph",
        "constraint_miner",
        "static_constraint_miner",
        "dynamic_constraint_miner",
        "test_cases_json",
        "invariants_csv",
        "history_session-1",
    }.issubset(artifact_ids)
    assert all("/" not in artifact_id for artifact_id in artifact_ids)


def test_repository_rejects_path_traversal(tmp_path):
    from api_testing.backend.repository import (
        FileArtifactRepository,
        InvalidArtifactRequest,
    )

    cache_root = build_artifact_cache(tmp_path)
    repository = FileArtifactRepository(cache_root)

    with pytest.raises(InvalidArtifactRequest):
        repository.get_run("../Run A")


def test_repository_missing_run_raises_not_found(tmp_path):
    from api_testing.backend.repository import ArtifactNotFound, FileArtifactRepository

    cache_root = build_artifact_cache(tmp_path)
    repository = FileArtifactRepository(cache_root)

    with pytest.raises(ArtifactNotFound):
        repository.get_run("missing")


def test_repository_cached_json_invalidates_when_file_changes(tmp_path):
    from api_testing.backend.repository import FileArtifactRepository

    cache_root = build_artifact_cache(tmp_path)
    repository = FileArtifactRepository(cache_root)

    first = repository.read_json_artifact("Run A", "specification")
    write_json(cache_root / "Run A" / "specification.json", {"operations": {}})
    second = repository.read_json_artifact("Run A", "specification")

    assert first != second
    assert second == {"operations": {}}
