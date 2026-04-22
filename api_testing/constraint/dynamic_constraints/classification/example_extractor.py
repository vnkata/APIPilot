from __future__ import annotations

import json
from typing import Any, Sequence

from api_testing.constraint.dynamic_constraints.classification.models import (
    NormalizedInvariantContext,
    PathSegment,
    VariableReference,
)
from api_testing.constraint.dynamic_constraints.test_case import TestCase


MAX_EXAMPLE_SCAN = 50


class ExampleExtractor:
    """Recover best-effort request/response examples for classifier prompts."""

    def __init__(self, *, max_examples: int) -> None:
        self.max_examples = max_examples
        self._parsed_request_cache: dict[str, Any] = {}
        self._parsed_response_cache: dict[str, Any] = {}

    def extract_examples(
        self,
        context: NormalizedInvariantContext,
        test_cases: Sequence[TestCase],
    ) -> list[str]:
        """Return deduplicated concrete examples for variables referenced by an invariant.

        Extraction is best-effort: missing request/response values simply reduce
        available examples and do not fail classification.
        """
        examples: list[str] = []
        seen_examples: set[str] = set()

        relevant_test_cases = [
            test_case
            for test_case in test_cases
            if test_case.operation_id.lower() == context.parsed_program_point.operation_key.lower()
            and (
                not context.parsed_program_point.status_code
                or str(test_case.status_code) == context.parsed_program_point.status_code
            )
        ]

        for test_case in relevant_test_cases:
            input_example = self._build_input_example(test_case, context.input_variables)
            if context.input_variables and input_example is None:
                continue

            output_examples = self._build_output_examples(test_case, context)
            if context.output_variables and not output_examples:
                continue

            combined_examples = output_examples or [""]
            if input_example:
                combined_examples = [
                    f"{input_example}; {output_example}".strip("; ")
                    if output_example
                    else input_example
                    for output_example in combined_examples
                ]

            for example in combined_examples:
                normalized = example.strip()
                if not normalized or normalized in seen_examples:
                    continue
                seen_examples.add(normalized)
                examples.append(normalized)
                if len(examples) >= self.max_examples:
                    return examples
                if len(seen_examples) >= MAX_EXAMPLE_SCAN:
                    return examples

        return examples

    def _build_input_example(
        self,
        test_case: TestCase,
        input_variables: Sequence[VariableReference],
    ) -> str | None:
        if not input_variables:
            return None

        assignments: list[str] = []
        for variable in input_variables:
            value = self._extract_input_variable_value(test_case, variable)
            if value is None:
                return None
            assignments.append(self._format_assignment("input", variable, value))
        return "; ".join(assignments)

    def _build_output_examples(
        self,
        test_case: TestCase,
        context: NormalizedInvariantContext,
    ) -> list[str]:
        if not context.output_variables:
            return []

        response_json = self._parse_test_case_payload(
            cache=self._parsed_response_cache,
            test_case_id=f"{test_case.test_case_id}:response",
            payload=test_case.response_body,
        )
        if response_json is None:
            return []

        base_nodes = self._resolve_output_base_nodes(
            response_json,
            context.parsed_program_point.container_segments,
        )
        if not base_nodes:
            return []

        examples: list[str] = []
        for base_node in base_nodes:
            assignments: list[str] = []
            missing_value = False
            for variable in context.output_variables:
                value_source = self._select_output_value_source(
                    response_json=response_json,
                    base_node=base_node,
                    container_segments=context.parsed_program_point.container_segments,
                    variable=variable,
                )
                value = self._extract_output_variable_value(value_source, variable)
                if value is None:
                    missing_value = True
                    break
                assignments.append(self._format_assignment("return", variable, value))

            if not missing_value and assignments:
                examples.append("; ".join(assignments))

        return examples

    def _extract_input_variable_value(
        self,
        test_case: TestCase,
        variable: VariableReference,
    ) -> Any | None:
        if not variable.path_segments:
            return None

        leaf_segment = variable.path_segments[-1]
        candidate_name = leaf_segment.name or ""
        parameter_value = test_case.parameters.get(candidate_name)
        if parameter_value is not None:
            if variable.is_size:
                return self._coerce_size(parameter_value)
            return parameter_value

        request_json = self._parse_test_case_payload(
            cache=self._parsed_request_cache,
            test_case_id=f"{test_case.test_case_id}:request",
            payload=test_case.request_body,
        )
        if request_json is None:
            return None

        value = self._extract_path_value(request_json, variable.path_segments)
        if variable.is_size:
            return self._coerce_size(value)
        return value

    def _extract_output_variable_value(
        self,
        base_node: Any,
        variable: VariableReference,
    ) -> Any | None:
        value = self._extract_path_value(base_node, variable.path_segments)
        if variable.is_size:
            return self._coerce_size(value)
        return value

    def _resolve_output_base_nodes(
        self,
        response_json: Any,
        container_segments: Sequence[PathSegment],
    ) -> list[Any]:
        nodes = [response_json]
        if not container_segments:
            return nodes

        for segment in container_segments:
            next_nodes: list[Any] = []
            for node in nodes:
                next_nodes.extend(self._expand_segment(node, segment))
            nodes = next_nodes
            if not nodes:
                return []
        return nodes

    def _extract_path_value(
        self,
        node: Any,
        path_segments: Sequence[PathSegment],
    ) -> Any | None:
        if not path_segments:
            return node

        next_nodes = self._expand_segment(node, path_segments[0])
        if not next_nodes:
            return None

        if len(path_segments) == 1:
            if path_segments[0].is_array:
                return next_nodes
            return next_nodes if len(next_nodes) != 1 else next_nodes[0]

        collected: list[Any] = []
        for next_node in next_nodes:
            child_value = self._extract_path_value(next_node, path_segments[1:])
            if child_value is None:
                continue
            if isinstance(child_value, list):
                collected.extend(child_value)
            else:
                collected.append(child_value)

        if not collected:
            return None
        return collected if len(collected) != 1 else collected[0]

    @staticmethod
    def _select_output_value_source(
        *,
        response_json: Any,
        base_node: Any,
        container_segments: Sequence[PathSegment],
        variable: VariableReference,
    ) -> Any:
        if variable.is_size and tuple(variable.path_segments) == tuple(container_segments):
            return response_json
        return base_node

    def _expand_segment(self, node: Any, segment: PathSegment) -> list[Any]:
        if segment.name is None:
            if segment.is_array and isinstance(node, list):
                return list(node)
            return []

        if isinstance(node, list):
            expanded: list[Any] = []
            for item in node:
                expanded.extend(self._expand_segment(item, segment))
            return expanded

        if not isinstance(node, dict) or segment.name not in node:
            return []

        value = node[segment.name]
        if segment.is_array:
            if isinstance(value, list):
                return list(value)
            return [value]
        return [value]

    @staticmethod
    def _coerce_size(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple, dict, str)):
            return len(value)
        return None

    def _parse_test_case_payload(
        self,
        *,
        cache: dict[str, Any],
        test_case_id: str,
        payload: Any,
    ) -> Any | None:
        if test_case_id in cache:
            return cache[test_case_id]

        parsed_payload = None
        if isinstance(payload, (dict, list)):
            parsed_payload = payload
        elif isinstance(payload, str) and payload.strip():
            try:
                parsed_payload = json.loads(payload)
            except json.JSONDecodeError:
                parsed_payload = None

        cache[test_case_id] = parsed_payload
        return parsed_payload

    @staticmethod
    def _format_assignment(prefix: str, variable: VariableReference, value: Any) -> str:
        qualified_path = ExampleExtractor._qualify_variable_path(prefix, variable.display_path)
        label = f"size({qualified_path})" if variable.is_size else qualified_path
        return f"{label}={ExampleExtractor._format_value(value)}"

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, str):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, (list, dict, bool)) or value is None:
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _qualify_variable_path(prefix: str, display_path: str) -> str:
        if not display_path:
            return prefix
        if display_path.startswith("["):
            return f"{prefix}{display_path}"
        return f"{prefix}.{display_path}"
