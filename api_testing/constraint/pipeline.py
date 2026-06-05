"""Config-gated constraint research pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from api_testing.constraint.counter_example_research_run import (
    ResearchAutomationConfig,
    ResearchAutomationResult,
    run_research_automation,
)


def run_constraint_pipeline(
    *,
    cache_dir: str | Path,
    pipeline_config: dict[str, Any],
    counter_example_config: dict[str, Any],
) -> ResearchAutomationResult | None:
    """Run post-combination research automation when explicitly enabled."""
    if not pipeline_config.get("enabled", False):
        return None
    config = ResearchAutomationConfig(
        counter_examples_per_pair=int(
            counter_example_config.get("counter_examples_per_pair", 5)
        ),
        live_planner=bool(counter_example_config.get("live_planner", False)),
        allow_non_get=bool(counter_example_config.get("allow_non_get", False)),
        confirm_unsafe_methods=bool(
            counter_example_config.get("confirm_unsafe_methods", False)
        ),
        target_base_url=counter_example_config.get("target_base_url"),
        allowed_target_base_urls=tuple(
            counter_example_config.get("allowed_target_base_urls") or ()
        ),
        request_budget=int(counter_example_config.get("request_budget", 5)),
        timeout_seconds=float(counter_example_config.get("timeout_seconds", 10.0)),
        overwrite_labels_with_backup=bool(
            counter_example_config.get("overwrite_labels_with_backup", False)
        ),
        overwrite_evidence=bool(counter_example_config.get("overwrite_evidence", False)),
    )
    return run_research_automation(cache_dir, config)
