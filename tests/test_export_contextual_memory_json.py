import importlib.util
import json
from pathlib import Path


def _load_module(relative_path, module_name):
    module_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ContextualMemory = _load_module(
    Path("api_testing") / "memory" / "contextual_memory.py",
    "contextual_memory",
).ContextualMemory
exporter = _load_module(
    Path("scripts") / "export_contextual_memory_json.py",
    "export_contextual_memory_json",
)


def test_export_contextual_memory_json_from_cache_dir(tmp_path):
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.produce("user", {"id": 1, "name": "Ada"})
    memory.set_current("get-/users/{id}")
    memory.add({"id": 1})
    memory.close()

    output_path, context_count = exporter.export_contextual_memory_json(tmp_path)

    assert output_path == tmp_path / "contextual_memory.json"
    assert context_count == 2
    assert json.loads(output_path.read_text(encoding="utf-8")) == {
        "get-/users/{id}": {"whitelist": [{"id": 1}]},
        "user": [{"id": 1, "name": "Ada"}],
    }


def test_export_contextual_memory_json_accepts_db_path_and_custom_output(tmp_path):
    memory = ContextualMemory(cache_dir=str(tmp_path))
    memory.produce("project", {"id": 10})
    memory.close()

    custom_output = tmp_path / "exports" / "memory.json"
    output_path, context_count = exporter.export_contextual_memory_json(
        tmp_path / "contextual_memory.db",
        output=custom_output,
        indent=4,
    )

    assert output_path == custom_output
    assert context_count == 1
    assert json.loads(custom_output.read_text(encoding="utf-8")) == {
        "project": [{"id": 10}]
    }
