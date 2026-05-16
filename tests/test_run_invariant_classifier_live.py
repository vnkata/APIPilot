from __future__ import annotations

from pathlib import Path

import scripts.run_invariant_classifier_live as runner

from api_testing.constraint.dynamic_constraints.invariant_extractor import (
    EXPECTED_INVARIANTS_HEADER,
)


def _write_invariants(path: Path, rows: list[str]) -> None:
    path.write_text(
        EXPECTED_INVARIANTS_HEADER + "\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def test_run_one_uses_live_output_filename_and_debug_flag(monkeypatch, tmp_path: Path):
    calls: dict[str, object] = {}
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    _write_invariants(
        cache_dir / "invariants.csv",
        [
            "get-/widgets&get-/widgets&200():::EXIT;return.id >= 1;"
            "daikon.inv.unary.scalar.LowerBound;(return.id);pm.expect(return_id).to.be.at.least(1)"
        ],
    )

    class FakeSpecificationParser:
        def __init__(self, spec_path: str):
            calls["spec_path"] = spec_path
            self.operations = {"get-/widgets": object()}

        def parse_specification(self) -> None:
            calls["parse_specification"] = True

    class FakeOpenAIModel:
        def __init__(self, model: str):
            calls["model_name"] = model

    class FakeInvariantClassifier:
        def __init__(self, *, spec_parser, model, cache_dir):
            calls["classifier_cache_dir"] = Path(cache_dir)
            calls["classifier_spec_parser"] = spec_parser
            calls["classifier_model"] = model

        def classify_invariants(
            self,
            *,
            input_path,
            output_path,
            persist_debug_artifacts,
            resume,
            max_workers,
            max_rows,
            summary_json_path,
            summary_csv_path,
        ):
            calls["input_path"] = Path(input_path)
            calls["output_path"] = Path(output_path)
            calls["persist_debug_artifacts"] = persist_debug_artifacts
            calls["resume"] = resume
            calls["max_workers"] = max_workers
            calls["max_rows"] = max_rows
            calls["summary_json_path"] = Path(summary_json_path)
            calls["summary_csv_path"] = Path(summary_csv_path)
            Path(output_path).write_text("ok\n", encoding="utf-8")
            return Path(output_path)

    monkeypatch.setattr(runner, "SpecificationParser", FakeSpecificationParser)
    monkeypatch.setattr(runner, "OpenAIModel", FakeOpenAIModel)
    monkeypatch.setattr(runner, "InvariantClassifier", FakeInvariantClassifier)

    output_path = runner.run_one(
        spec_path=tmp_path / "spec.json",
        cache_dir=cache_dir,
        model_name="test-live-model",
        output_filename=runner.OUTPUT_FILENAME,
        limit=None,
        max_rows=7,
        resume=True,
        max_workers=3,
        persist_debug_artifacts=True,
    )

    assert output_path == cache_dir / runner.OUTPUT_FILENAME
    assert calls["output_path"] == cache_dir / runner.OUTPUT_FILENAME
    assert calls["input_path"] == cache_dir / "invariants.csv"
    assert calls["model_name"] == "test-live-model"
    assert calls["persist_debug_artifacts"] is True
    assert calls["resume"] is True
    assert calls["max_workers"] == 3
    assert calls["max_rows"] == 7
    assert calls["summary_json_path"] == cache_dir / runner.SUMMARY_JSON_FILENAME
    assert calls["summary_csv_path"] == cache_dir / runner.SUMMARY_CSV_FILENAME
    assert calls["parse_specification"] is True


def test_run_one_limit_uses_sample_without_modifying_source(monkeypatch, tmp_path: Path):
    calls: dict[str, object] = {}
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    source_path = cache_dir / "invariants.csv"
    rows = [
        "ppt1;inv1;type1;(a);assert1",
        "ppt2;inv2;type2;(b);assert2",
        "ppt3;inv3;type3;(c);assert3",
    ]
    _write_invariants(source_path, rows)
    original_source = source_path.read_text(encoding="utf-8")

    class FakeSpecificationParser:
        def __init__(self, spec_path: str):
            self.operations = {"op": object()}

        def parse_specification(self) -> None:
            return None

    class FakeOpenAIModel:
        def __init__(self, model: str):
            return None

    class FakeInvariantClassifier:
        def __init__(self, *, spec_parser, model, cache_dir):
            return None

        def classify_invariants(self, *, input_path, output_path, **kwargs):
            sample_path = Path(input_path)
            calls["input_path"] = sample_path
            calls["sample_text"] = sample_path.read_text(encoding="utf-8")
            Path(output_path).write_text("ok\n", encoding="utf-8")
            return Path(output_path)

    monkeypatch.setattr(runner, "SpecificationParser", FakeSpecificationParser)
    monkeypatch.setattr(runner, "OpenAIModel", FakeOpenAIModel)
    monkeypatch.setattr(runner, "InvariantClassifier", FakeInvariantClassifier)

    runner.run_one(
        spec_path=tmp_path / "spec.json",
        cache_dir=cache_dir,
        limit=2,
    )

    assert calls["input_path"] != source_path
    assert source_path.read_text(encoding="utf-8") == original_source
    assert str(calls["sample_text"]).count("\n") == 3
    assert "ppt1;inv1;type1;(a);assert1" in str(calls["sample_text"])
    assert "ppt2;inv2;type2;(b);assert2" in str(calls["sample_text"])
    assert "ppt3;inv3;type3;(c);assert3" not in str(calls["sample_text"])


def test_main_continues_after_dataset_failure(monkeypatch, tmp_path: Path):
    calls: list[str] = []
    output_path = tmp_path / "classified.csv"

    monkeypatch.setattr(
        runner,
        "DATASET_TO_CACHE_DIR",
        {
            "datasets/one.json": str(tmp_path / "one"),
            "datasets/two.json": str(tmp_path / "two"),
        },
    )
    monkeypatch.setattr(runner, "_count_invariant_rows", lambda path: 1)

    def fake_run_one(*, spec_path, cache_dir, **kwargs):
        calls.append(str(cache_dir))
        if str(cache_dir).endswith("one"):
            raise RuntimeError("boom")
        return output_path

    monkeypatch.setattr(runner, "run_one", fake_run_one)

    exit_code = runner.main()

    assert exit_code == 1
    assert calls == [str(tmp_path / "one"), str(tmp_path / "two")]
