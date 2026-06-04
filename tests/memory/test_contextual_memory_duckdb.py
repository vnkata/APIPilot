import importlib.util
import json
from pathlib import Path


def _load_contextual_memory_class():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "api_testing"
        / "memory"
        / "contextual_memory.py"
    )
    spec = importlib.util.spec_from_file_location("contextual_memory", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ContextualMemory


ContextualMemory = _load_contextual_memory_class()


def test_contextual_memory_persists_to_duckdb(tmp_path):
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.produce("user", {"id": 1, "name": "Ada"})
    memory.set_current("get-/users/{id}")
    memory.add({"id": 1})
    memory.remove({"id": 2})
    memory.close()

    assert (tmp_path / "contextual_memory.db").exists()
    assert not (tmp_path / "contextual_memory.json").exists()

    reloaded = ContextualMemory(cache_dir=str(tmp_path))
    assert reloaded.consume("user") == [{"id": 1, "name": "Ada"}]

    reloaded.set_current("get-/users/{id}")
    assert reloaded.in_whitelist({"id": 1}) is True
    assert reloaded.is_blacklisted({"id": 2}) is True
    reloaded.close()


def test_contextual_memory_imports_existing_json_once(tmp_path):
    legacy_json = tmp_path / "contextual_memory.json"
    legacy_payload = {
        "project": [{"id": 10}],
        "delete-/projects/{id}": {"blacklist": [{"id": 10}]},
    }
    legacy_json.write_text(json.dumps(legacy_payload, indent=2), encoding="utf-8")

    memory = ContextualMemory(cache_dir=str(tmp_path))
    assert memory.contexts == legacy_payload

    original_json = legacy_json.read_text(encoding="utf-8")
    memory.produce("project", {"id": 11})
    memory.close()

    assert legacy_json.read_text(encoding="utf-8") == original_json

    reloaded = ContextualMemory(cache_dir=str(tmp_path))
    assert reloaded.consume("project") == [{"id": 10}, {"id": 11}]
    reloaded.close()


def test_contextual_memory_copy_is_in_memory_until_merged(tmp_path):
    shared = ContextualMemory(cache_dir=str(tmp_path))
    shared.produce("user", {"id": 1})

    tree_copy = shared.copy()
    tree_copy.produce("user", {"id": 2})
    tree_copy.set_current("get-/users/{id}")
    tree_copy.add({"id": 2})
    tree_copy.clear_current()
    tree_copy.close()

    shared.close()
    reloaded_before_merge = ContextualMemory(cache_dir=str(tmp_path))
    assert reloaded_before_merge.consume("user") == [{"id": 1}]

    reloaded_before_merge.merge(tree_copy)
    reloaded_before_merge.close()

    reloaded_after_merge = ContextualMemory(cache_dir=str(tmp_path))
    assert reloaded_after_merge.consume("user") == [{"id": 1}, {"id": 2}]
    reloaded_after_merge.set_current("get-/users/{id}")
    assert reloaded_after_merge.in_whitelist({"id": 2}) is True
    reloaded_after_merge.close()
