from __future__ import annotations

import json

import pytest

from api_testing.constraint.pipeline import run_constraint_pipeline
from api_testing.constraint.counter_example_research_run import (
    ResearchAutomationConfig,
    run_research_automation,
)


def _write_cache(tmp_path):
    cache_dir = tmp_path / ".cache" / "Run A"
    cache_dir.mkdir(parents=True)
    (cache_dir / "combine_constraint_miners.json").write_text(
        json.dumps(
            {
                "get-/items": {
                    "return.id": {
                        "endpoint": "get-/items",
                        "property": "return.id",
                        "static_constraint": "return.id in [1, 2]",
                        "dynamic_constraint": "return.id >= 1",
                        "status": "UNRESOLVED",
                        "relation": "STATIC_STRONGER",
                        "final_constraint": None,
                        "reason": "Needs evidence.",
                    },
                    "return.name": {
                        "endpoint": "get-/items",
                        "property": "return.name",
                        "static_constraint": "exists(return.name)",
                        "dynamic_constraint": "exists(return.name)",
                        "status": "RESOLVED",
                        "relation": "EQUIVALENT",
                        "final_constraint": "exists(return.name)",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "baseline_specification.json").write_text(
        json.dumps({"servers": [{"url": "https://example.test"}]}),
        encoding="utf-8",
    )
    return cache_dir


def test_research_runner_writes_labels_evidence_and_summary(tmp_path):
    cache_dir = _write_cache(tmp_path)
    calls = []

    def fake_executor(request):
        calls.append(request)
        return {
            "runtime_verdict": "STATIC_WIN",
            "runtime_result": {"status_code": 200},
        }

    result = run_research_automation(
        cache_dir,
        ResearchAutomationConfig(
            counter_examples_per_pair=2,
            allow_non_get=False,
            target_base_url="https://example.test",
            allowed_target_base_urls=("https://example.test",),
            request_budget=2,
            timeout_seconds=5,
        ),
        run_id="research-run-1",
        executor=fake_executor,
    )

    assert len(calls) == 2
    assert result.summary["pair_count"] == 1
    assert result.summary["evidence_case_count"] == 2
    assert result.output_dir == cache_dir / "research_runs" / "research-run-1"
    assert (cache_dir / "constraint_pair_labels.csv").exists()
    assert (cache_dir / "counter_example_case_results.jsonl").exists()
    assert (result.output_dir / "constraint_research_summary.json").exists()
    assert "STATIC_STRONGER" in (cache_dir / "constraint_pair_labels.csv").read_text(
        encoding="utf-8"
    )
    labels = (cache_dir / "constraint_pair_labels.csv").read_text(encoding="utf-8")
    assert "research_pair_id" in labels.splitlines()[0]
    evidence = (cache_dir / "counter_example_case_results.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"planner_status": "fallback"' in evidence
    assert result.summary["planner_status_counts"] == {"fallback": 2}
    assert result.summary["config"]["counter_examples_per_pair"] == 2


def test_research_runner_refuses_to_overwrite_existing_run_id(tmp_path):
    cache_dir = _write_cache(tmp_path)
    config = ResearchAutomationConfig(
        counter_examples_per_pair=1,
        target_base_url="https://example.test",
        allowed_target_base_urls=("https://example.test",),
        request_budget=1,
        timeout_seconds=5,
    )

    run_research_automation(
        cache_dir,
        config,
        run_id="same-run",
        executor=lambda request: {
            "runtime_verdict": "STATIC_WIN",
            "runtime_result": {"status_code": 200},
        },
    )

    with pytest.raises(FileExistsError):
        run_research_automation(cache_dir, config, run_id="same-run")


def test_research_runner_fails_fast_without_target_base_url(tmp_path):
    cache_dir = _write_cache(tmp_path)
    (cache_dir / "baseline_specification.json").unlink()

    with pytest.raises(ValueError, match="target base URL"):
        run_research_automation(
            cache_dir,
            ResearchAutomationConfig(counter_examples_per_pair=1),
            run_id="missing-target",
        )


def test_research_runner_uses_planner_and_records_planner_failure_fallback(tmp_path):
    cache_dir = _write_cache(tmp_path)

    class FailingPlanner:
        prompt_version = "fake-planner-v1"
        last_error = {
            "error_type": "planner_parse_error",
            "message": "synthetic parse failure",
        }

        def generate(self, context):
            assert context["planner_strategy"] == "static_stronger_diagnostic"
            return []

    result = run_research_automation(
        cache_dir,
        ResearchAutomationConfig(
            counter_examples_per_pair=1,
            target_base_url="https://example.test",
            allowed_target_base_urls=("https://example.test",),
            request_budget=1,
            timeout_seconds=5,
            live_planner=True,
        ),
        run_id="planner-fallback",
        planner_factory=lambda: FailingPlanner(),
        executor=lambda request: {
            "runtime_verdict": "STATIC_WIN",
            "runtime_result": {"status_code": 200},
        },
    )

    evidence = (cache_dir / "counter_example_case_results.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"planner_status": "failed"' in evidence
    assert '"planner_error_kind": "planner_parse_error"' in evidence
    assert '"weak_evidence": true' in evidence
    assert result.summary["planner_status_counts"] == {"failed": 1}


def test_research_runner_blocks_unsafe_methods_as_invalid_evidence(tmp_path):
    cache_dir = tmp_path / ".cache" / "Run A"
    cache_dir.mkdir(parents=True)
    (cache_dir / "combine_constraint_miners.json").write_text(
        json.dumps(
            {
                "delete-/items/{id}": {
                    "return.id": {
                        "endpoint": "delete-/items/{id}",
                        "property": "return.id",
                        "static_constraint": "exists(return.id)",
                        "dynamic_constraint": "exists(return.id)",
                        "status": "UNRESOLVED",
                        "relation": "DYNAMIC_STRONGER",
                        "final_constraint": None,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "baseline_specification.json").write_text(
        json.dumps({"servers": [{"url": "https://example.test"}]}),
        encoding="utf-8",
    )

    result = run_research_automation(
        cache_dir,
        ResearchAutomationConfig(
            counter_examples_per_pair=1,
            target_base_url="https://example.test",
            allowed_target_base_urls=("https://example.test",),
            request_budget=1,
            timeout_seconds=5,
        ),
        run_id="unsafe-blocked",
        executor=lambda request: pytest.fail("unsafe request should not execute"),
    )

    evidence = (cache_dir / "counter_example_case_results.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"invalid_reason": "unsafe_method_blocked"' in evidence
    assert result.summary["invalid_runtime_counts"] == {"unsafe_method_blocked": 1}


def test_research_runner_resolves_path_params_from_successful_test_cases(tmp_path):
    cache_dir = tmp_path / ".cache" / "Run A"
    cache_dir.mkdir(parents=True)
    (cache_dir / "combine_constraint_miners.json").write_text(
        json.dumps(
            {
                "get-/items/{itemId}": {
                    "return.id": {
                        "endpoint": "get-/items/{itemId}",
                        "property": "return.id",
                        "static_constraint": "exists(return.id)",
                        "dynamic_constraint": "input.itemId == return.id",
                        "status": "UNRESOLVED",
                        "relation": "DYNAMIC_STRONGER",
                        "final_constraint": None,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "baseline_specification.json").write_text(
        json.dumps(
            {
                "servers": [{"url": "https://example.test"}],
                "paths": {
                    "/items/{itemId}": {
                        "get": {
                            "parameters": [
                                {
                                    "name": "itemId",
                                    "in": "path",
                                    "schema": {"type": "integer"},
                                    "required": True,
                                }
                            ],
                            "responses": {"200": {"description": "OK"}},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (cache_dir / "test_cases.json").write_text(
        json.dumps(
            [
                {
                    "operation_id": "get-/items/{itemId}",
                    "path": "/items/42",
                    "http_method": "get",
                    "parameters": {"itemId": 42},
                    "status_code": 200,
                    "response_body": json.dumps({"id": 42}),
                }
            ]
        ),
        encoding="utf-8",
    )
    calls = []

    def fake_executor(request):
        calls.append(request)
        return {
            "runtime_verdict": "DYNAMIC_WIN",
            "runtime_result": {"status_code": 200},
        }

    result = run_research_automation(
        cache_dir,
        ResearchAutomationConfig(
            counter_examples_per_pair=1,
            target_base_url="https://example.test",
            allowed_target_base_urls=("https://example.test",),
            request_budget=1,
            timeout_seconds=5,
        ),
        run_id="path-param-resolved",
        executor=fake_executor,
    )

    assert calls[0]["path"] == "/items/42"
    assert result.summary["invalid_runtime_counts"] == {}


def test_research_runner_preserves_existing_human_labels_and_marks_orphans(tmp_path):
    cache_dir = _write_cache(tmp_path)
    first = run_research_automation(
        cache_dir,
        ResearchAutomationConfig(
            counter_examples_per_pair=1,
            target_base_url="https://example.test",
            allowed_target_base_urls=("https://example.test",),
            request_budget=1,
            timeout_seconds=5,
        ),
        run_id="first-run",
        executor=lambda request: {
            "runtime_verdict": "STATIC_WIN",
            "runtime_result": {"status_code": 200},
        },
    )
    labels_path = first.labels_path
    lines = labels_path.read_text(encoding="utf-8").splitlines()
    labels_path.write_text(
        "\n".join(
            [
                lines[0],
                lines[1].replace(",UNSURE,UNSURE,", ",TP,FP,"),
                (
                    "rp_old,Run A,cmb_old,get-/old,return.old,STATIC_STRONGER,"
                    "UNRESOLVED,old static,old dynamic,,INCONCLUSIVE,UNSURE,"
                    "UNSURE,,TP,UNSURE,,old note,2026-06-04T00:00:00Z,false"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    run_research_automation(
        cache_dir,
        ResearchAutomationConfig(
            counter_examples_per_pair=1,
            target_base_url="https://example.test",
            allowed_target_base_urls=("https://example.test",),
            request_budget=1,
            timeout_seconds=5,
        ),
        run_id="second-run",
        executor=lambda request: {
            "runtime_verdict": "STATIC_WIN",
            "runtime_result": {"status_code": 200},
        },
    )

    csv_text = labels_path.read_text(encoding="utf-8")
    assert ",TP,FP," in csv_text
    assert "rp_old" in csv_text
    assert "old note" in csv_text
    assert csv_text.rstrip().endswith("true")


def test_constraint_pipeline_disabled_by_default_does_not_run(tmp_path, monkeypatch):
    calls = []

    def fake_runner(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(
        "api_testing.constraint.pipeline.run_research_automation",
        fake_runner,
    )
    result = run_constraint_pipeline(
        cache_dir=tmp_path,
        pipeline_config={},
        counter_example_config={},
    )

    assert result is None
    assert calls == []


def test_constraint_pipeline_maps_config_to_research_runner(tmp_path, monkeypatch):
    captured = {}

    def fake_runner(cache_dir, config):
        captured["cache_dir"] = cache_dir
        captured["config"] = config
        return "pipeline-result"

    monkeypatch.setattr(
        "api_testing.constraint.pipeline.run_research_automation",
        fake_runner,
    )

    result = run_constraint_pipeline(
        cache_dir=tmp_path,
        pipeline_config={"enabled": True},
        counter_example_config={
            "counter_examples_per_pair": 3,
            "live_planner": True,
            "allow_non_get": True,
            "confirm_unsafe_methods": True,
            "target_base_url": "https://example.test",
            "allowed_target_base_urls": ["https://example.test"],
            "request_budget": 9,
            "timeout_seconds": 2.5,
            "overwrite_labels_with_backup": True,
            "overwrite_evidence": True,
        },
    )

    assert result == "pipeline-result"
    assert captured["cache_dir"] == tmp_path
    config = captured["config"]
    assert isinstance(config, ResearchAutomationConfig)
    assert config.counter_examples_per_pair == 3
    assert config.live_planner is True
    assert config.allow_non_get is True
    assert config.confirm_unsafe_methods is True
    assert config.target_base_url == "https://example.test"
    assert config.allowed_target_base_urls == ("https://example.test",)
    assert config.request_budget == 9
    assert config.timeout_seconds == 2.5
    assert config.overwrite_labels_with_backup is True
    assert config.overwrite_evidence is True
