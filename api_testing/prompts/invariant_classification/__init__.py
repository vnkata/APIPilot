from __future__ import annotations

import json
import os
import re
from typing import Sequence

from pydantic import ValidationError

from api_testing.prompts.invariant_classification.schema import (
    InvariantClassificationResult,
)
from api_testing.utils.log import getLogger


class InvariantClassificationPrompt:
    """Prompt wrapper for LLM-based invariant classification."""

    DEBUG_ENV_VAR = "INVARIANT_CLASSIFICATION_DEBUG"

    SYSTEM_PROMPT = """
You are an API testing expert who evaluates whether a dynamic invariant for a REST API is trustworthy.
Classify the invariant as:
- "true-positive": the invariant is likely valid for all valid requests and responses.
- "false-positive": the invariant is likely overfit, contradicted by the API contract, or semantically implausible.
- "inconclusive": the evidence is insufficient or too ambiguous to make a reliable decision.

Return only valid JSON with the fields:
- verdict: exactly one of "true-positive", "false-positive", or "inconclusive"
- confidence: a JSON number between 0.0 and 1.0, never a string
- reason: a concise string

Guidelines:
- Consider the API specification excerpt, the invariant semantics, and the observed examples together.
- Use only the evidence explicitly present in the prompt. Do not invent schema values, missing enum members, or counterexamples.
- If you claim a contradiction, the reason must cite the exact contradicting spec detail or observed example from the prompt.
- If every observed example supports the invariant and the spec excerpt does not contradict it, do not say the observed examples contradict it.
- More observed calls without counterexamples increases confidence, but does not override a clear specification contradiction.
- If the invariant restricts a field in a way that conflicts with explicitly documented values, ranges, or semantics, prefer "false-positive".
- For "one of", exact constant, fixed length, fixed size, or exact array-size invariants, prefer "true-positive" only when the spec explicitly documents the same enum/constant/range/size or the invariant follows directly from documented API semantics.
- If a "one of" or exact-value invariant is supported only by observed examples while the spec field is broad (for example integer/string with no enum), prefer "false-positive" for likely overfitting.
- If the invariant compares fields that do not make semantic sense together, prefer "false-positive".
- If the specification is too weak or the context is incomplete, prefer "inconclusive" instead of guessing.
- Keep the reason concise but specific.
- Treat the deterministic evidence checks in the user prompt as authoritative for
  whether the shown examples satisfy simple operators and whether a one-of
  invariant matches the documented enum.

Mechanical example-checking rules:
- For `x <= y`, an observed example supports the invariant when x is less than or equal to y; it contradicts only when x > y. A negative x and positive y supports `x <= y`.
- For `x >= y`, an observed example supports the invariant when x is greater than or equal to y; it contradicts only when x < y.
- For `x < y`, an observed example contradicts only when x >= y.
- For `x > y`, an observed example contradicts only when x <= y.
- For `x == y`, an observed example contradicts only when the two values differ.
- For `x is a substring of y`, equality supports the invariant because every string is a substring of itself.
- If you cannot mechanically verify a claimed contradiction from the provided examples, do not classify as "false-positive" because of that contradiction.

Valid response example:
{"verdict":"true-positive","confidence":0.9,"reason":"The invariant matches the documented enum values and observed examples."}

Invalid responses to avoid:
- {"verdict":"true-positive","confidence":"high","reason":"..."}
- Here is the classification: {"verdict":"true-positive","confidence":0.9,"reason":"..."}
- ```json
  {"verdict":"true-positive","confidence":0.9,"reason":"..."}
  ```
""".strip()

    USER_PROMPT_TEMPLATE = """
Invariant: {invariant}
Invariant type: {invariant_type}
Invariant description: {invariant_description}
Program point: {program_point}
Observed successful calls in this cache: {approx_number_of_operations}

Fields starting with "input." refer to request parameters or request body fields.
Fields starting with "return." refer to response body fields.
Response container path context: {response_container_path}

Relevant API specification excerpt:
{spec_excerpt}

Observed examples:
{examples_block}

Deterministic evidence checks:
{evidence_checks_block}

Classify the invariant as "true-positive", "false-positive", or "inconclusive".
""".strip()

    def __init__(self, llm) -> None:
        self.llm = llm
        self.logger = getLogger(__name__)

    def exec(
        self,
        *,
        invariant: str,
        invariant_type: str,
        invariant_description: str,
        program_point: str,
        response_container_path: str,
        spec_excerpt: str,
        examples: Sequence[str],
        approx_number_of_operations: int,
        evidence_checks: Sequence[str] = (),
        log_debug: bool = False,
    ) -> InvariantClassificationResult:
        examples_block = self._format_examples(examples)
        evidence_checks_block = self._format_evidence_checks(evidence_checks)
        prompt = self.USER_PROMPT_TEMPLATE.format(
            invariant=invariant,
            invariant_type=invariant_type,
            invariant_description=invariant_description or "No invariant description available.",
            program_point=program_point,
            response_container_path=response_container_path or "<root>",
            spec_excerpt=spec_excerpt,
            examples_block=examples_block,
            approx_number_of_operations=approx_number_of_operations,
            evidence_checks_block=evidence_checks_block,
        )
        should_log_debug = log_debug or os.getenv(self.DEBUG_ENV_VAR) == "1"
        if should_log_debug:
            self.logger.debug("InvariantClassificationPrompt Prompt: %s", prompt)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        response, _ = self.llm.generate(
            prompt=messages,
            system_prompt=None,
            schema=None,
        )
        result = self.parse_response(response)
        if should_log_debug:
            self.logger.debug(
                "InvariantClassificationPrompt Response: %s",
                json.dumps(result.model_dump(), ensure_ascii=False, indent=2),
            )
        return result

    @staticmethod
    def _format_examples(examples: Sequence[str]) -> str:
        if not examples:
            return "- No concrete examples could be recovered from the cached test cases."

        return "\n".join(f"- {example}" for example in examples)

    @staticmethod
    def _format_evidence_checks(evidence_checks: Sequence[str]) -> str:
        checks = [check.strip() for check in evidence_checks if check and check.strip()]
        if not checks:
            return "- No deterministic evidence checks available."
        return "\n".join(f"- {check}" for check in checks)

    @classmethod
    def parse_response(cls, response) -> InvariantClassificationResult:
        """Parse, conservatively repair, and validate a model classification response."""
        if isinstance(response, InvariantClassificationResult):
            return response
        if isinstance(response, dict):
            return cls._validate_payload(response)

        text = str(response).strip()
        payload = cls._load_json_payload(text)
        return cls._validate_payload(payload)

    @staticmethod
    def _load_json_payload(text: str) -> dict:
        cleaned = text.strip()
        fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
        if fenced_match:
            cleaned = fenced_match.group(1).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise
            payload = json.loads(cleaned[start : end + 1])

        if not isinstance(payload, dict):
            raise ValueError("Invariant classification response must be a JSON object.")
        return payload

    @classmethod
    def _validate_payload(cls, payload: dict) -> InvariantClassificationResult:
        repaired_payload = dict(payload)
        if "confidence" in repaired_payload:
            repaired_payload["confidence"] = cls._repair_confidence(repaired_payload["confidence"])

        try:
            return InvariantClassificationResult.model_validate(repaired_payload)
        except ValidationError:
            raise

    @staticmethod
    def _repair_confidence(value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            confidence_labels = {
                "high": 0.8,
                "medium": 0.5,
                "low": 0.2,
            }
            if normalized in confidence_labels:
                return confidence_labels[normalized]
            try:
                return float(normalized)
            except ValueError:
                return value
        return value
