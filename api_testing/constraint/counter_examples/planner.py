"""LLM-backed draft-only counter-example planner."""

from __future__ import annotations

import json
from typing import Any, Mapping

from api_testing.constraint.counter_examples.models import (
    CounterExamplePlannerResponse,
)

PROMPT_VERSION = "counter-example-planner-v1"


class CounterExampleLLMPlanner:
    """Generate untrusted diagnostic counter-example drafts.

    The planner intentionally does not execute requests or make final constraint
    decisions. Callers must validate and approve generated cases before use.
    """

    SYSTEM_PROMPT = """
You are an API testing assistant generating diagnostic counter-example draft
requests for one static constraint and one dynamic constraint.

Generate only draft test cases. Do not claim proof, do not choose a final
constraint, and do not produce secrets. Prefer GET requests when possible.
For non-GET requests, keep payloads minimal and explicitly mark the risk.

Use the target_truth_vector to state what the diagnostic case is intended to
show:
- static_constraint: "true", "false", or "unknown"
- dynamic_constraint: "true", "false", or "unknown"

The request must contain method and path. Headers may only use non-sensitive
names or typed secret references, never raw token or password values.
Return JSON conforming exactly to the requested schema, without markdown.
"""

    PROMPT_TEMPLATE = """
Counter-example planning context:
{context_json}

Return 1 to 3 diagnostic draft cases. Keep them bounded and safe.
"""

    REPAIR_TEMPLATE = """
Previous structured output error: {error}

Regenerate the same counter-example plan as valid JSON for the required schema.
Do not include markdown or fields outside the schema.

Original planning context:
{context_json}
"""

    def __init__(self, llm: Any) -> None:
        self.llm = llm
        self.last_interactions: list[dict[str, Any]] = []
        self.last_error: dict[str, str] | None = None

    def generate(self, context: Mapping[str, Any]) -> list[dict[str, Any]]:
        self.last_interactions = []
        self.last_error = None
        context_json = json.dumps(context, ensure_ascii=False, indent=2, default=str)
        attempts = [
            self.PROMPT_TEMPLATE.format(context_json=context_json),
        ]
        last_error_message: str | None = None

        for attempt_index in range(2):
            if attempt_index == 1:
                attempts.append(
                    self.REPAIR_TEMPLATE.format(
                        error=last_error_message or "unknown structured output error",
                        context_json=context_json,
                    )
                )
            prompt = attempts[attempt_index]
            interaction: dict[str, Any] = {
                "attempt": attempt_index + 1,
                "system_prompt": self.SYSTEM_PROMPT,
                "prompt": prompt,
                "parsed_response": None,
                "error": None,
            }
            case_id = context.get("case_id")
            if case_id is not None:
                interaction["case_id"] = str(case_id)
            try:
                response, _ = self.llm.generate(
                    system_prompt=self.SYSTEM_PROMPT,
                    prompt=prompt,
                    schema=CounterExamplePlannerResponse,
                )
                parsed = response.model_dump()
                interaction["parsed_response"] = parsed
                self.last_interactions.append(interaction)
                return parsed["cases"]
            except Exception as exc:
                last_error_message = str(exc)
                interaction["error"] = last_error_message
                self.last_interactions.append(interaction)

        self.last_error = {
            "error_type": "planner_parse_error",
            "message": last_error_message or "unknown structured output error",
        }
        return []
