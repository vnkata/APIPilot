import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

from api_testing.prompts.constraint_combination import ConstraintCombination
from api_testing.utils.log import getLogger


class ConstraintCombiner:
    """Combine static and dynamic constraints by normalized endpoint property."""

    MAIN_CACHE = "combine_constraint_miners.json"

    def __init__(
        self,
        cache_dir: str | Path,
        model: Optional[Any] = None,
        prompt_factory: Optional[Any] = None,
        max_test_cases: int = 5,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.logger = getLogger(__name__)
        self.combination_prompt = None
        self.prompt_failure: Optional[str] = None
        self.max_test_cases = max(1, max_test_cases)
        if prompt_factory:
            self.combination_prompt = prompt_factory.create(ConstraintCombination)
        elif model:
            self.combination_prompt = ConstraintCombination(llm=model)

    @staticmethod
    def _canonical_property(property_name: str) -> str:
        """Treat array-element spelling differences as the same property path."""
        return re.sub(r"\[\]", "", property_name or "").strip()

    @staticmethod
    def _normalize_expression(expression: Optional[str]) -> str:
        if not expression:
            return ""
        return re.sub(r"\s+", "", expression).replace("[]", "")

    @staticmethod
    def _index_constraints(
        constraints: Dict[str, str],
    ) -> Dict[str, Dict[str, str]]:
        indexed: Dict[str, Dict[str, str]] = {}
        duplicates: Dict[str, list[str]] = defaultdict(list)
        for property_name, expression in (constraints or {}).items():
            canonical = ConstraintCombiner._canonical_property(property_name)
            if canonical in indexed:
                duplicates[canonical].append(expression)
                continue
            indexed[canonical] = {
                "property": property_name,
                "constraint": expression,
            }

        for canonical, expressions in duplicates.items():
            values = [indexed[canonical]["constraint"], *expressions]
            indexed[canonical]["constraint"] = "and(" + ",".join(values) + ")"
        return indexed

    def _combine_pair(
        self,
        endpoint: str,
        property_name: str,
        static_constraint: str,
        dynamic_constraint: str,
    ) -> Dict[str, Any]:
        if self._normalize_expression(static_constraint) == self._normalize_expression(
            dynamic_constraint
        ):
            return {
                "status": "COMBINED_EQUIVALENT",
                "final_constraint": static_constraint,
                "reason": (
                    "EQUIVALENT: Static and dynamic constraints are identical after "
                    "normalizing array-path notation and whitespace."
                ),
            }

        if self.combination_prompt:
            try:
                verdict = self.combination_prompt.exec(
                    endpoint=endpoint,
                    property=property_name,
                    static_constraint=static_constraint,
                    dynamic_constraint=dynamic_constraint,
                    test_case_count=self.max_test_cases,
                )
                if verdict.status == "COMBINED_EQUIVALENT":
                    return {
                        "status": "COMBINED_EQUIVALENT",
                        "final_constraint": static_constraint,
                        "reason": verdict.reason,
                        "counter_example": None,
                    }
                return {
                    "status": "NOT_COMBINED",
                    "final_constraint": None,
                    "reason": verdict.reason,
                    "counter_example": (
                        verdict.counter_example.model_dump()
                        if verdict.counter_example is not None
                        else None
                    ),
                }
            except Exception as exc:
                self.prompt_failure = str(exc)
                self.combination_prompt = None
                self.logger.warning(
                    "LLM constraint combination failed for %s %s; remaining conflicts "
                    "will be retained as pending without additional LLM calls: %s",
                    endpoint,
                    property_name,
                    exc,
                )

        staging_detail = (
            f" Counter-example staging failed: {self.prompt_failure}"
            if self.prompt_failure
            else ""
        )
        return {
            "status": "NOT_COMBINED",
            "final_constraint": None,
            "reason": (
                "CONFLICT_PENDING: Rules differ and require counter-example staging "
                f"and runtime verification before they can be resolved.{staging_detail}"
            ),
            "counter_example": None,
        }

    def combine(
        self,
        static_constraints: Dict[str, Dict[str, str]],
        dynamic_constraints: Dict[str, Dict[str, str]],
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        results: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for endpoint in sorted(set(static_constraints) | set(dynamic_constraints)):
            static_index = self._index_constraints(static_constraints.get(endpoint, {}))
            dynamic_index = self._index_constraints(dynamic_constraints.get(endpoint, {}))
            endpoint_results: Dict[str, Dict[str, Any]] = {}

            for canonical in sorted(set(static_index) | set(dynamic_index)):
                static_item = static_index.get(canonical)
                dynamic_item = dynamic_index.get(canonical)
                property_name = (
                    static_item["property"] if static_item else dynamic_item["property"]
                )
                static_rule = static_item["constraint"] if static_item else None
                dynamic_rule = dynamic_item["constraint"] if dynamic_item else None

                record: Dict[str, Any] = {
                    "endpoint": endpoint,
                    "property": property_name,
                    "static_constraint": static_rule,
                    "dynamic_constraint": dynamic_rule,
                    "status": "",
                    "final_constraint": None,
                    "reason": "",
                    "counter_example": None,
                }
                if static_rule is None:
                    record.update(
                        {
                            "status": "UNIQUE_DYNAMIC",
                            "final_constraint": dynamic_rule,
                            "reason": "UNIQUE: Constraint exists exclusively in dynamic mining output.",
                        }
                    )
                elif dynamic_rule is None:
                    record.update(
                        {
                            "status": "UNIQUE_STATIC",
                            "final_constraint": static_rule,
                            "reason": "UNIQUE: Constraint exists exclusively in static mining output.",
                        }
                    )
                else:
                    record.update(
                        self._combine_pair(
                            endpoint, property_name, static_rule, dynamic_rule
                        )
                    )
                endpoint_results[property_name] = record
            results[endpoint] = endpoint_results

        self._save(results)
        return results

    def _save(self, data: Dict[str, Any]) -> None:
        cache_file = self.cache_dir / self.MAIN_CACHE
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with cache_file.open("w", encoding="utf-8") as output:
            json.dump(data, output, ensure_ascii=False, indent=4)
        self.logger.debug("Combined constraints saved to %s", cache_file)
