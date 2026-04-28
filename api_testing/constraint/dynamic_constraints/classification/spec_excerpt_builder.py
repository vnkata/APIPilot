from __future__ import annotations

from dataclasses import asdict
import json
from types import SimpleNamespace
from typing import Any, Sequence

from api_testing.constraint.dynamic_constraints.classification.models import (
    ExcerptBuildResult,
    ExcerptBudgetProfile,
    ExcerptLine,
    InvariantExcerptShape,
    MatchedSchemaPath,
    NormalizedInvariantContext,
    PathSegment,
    ParsedProgramPoint,
    SchemaEntry,
    SchemaIndex,
    VariableReference,
)
from api_testing.constraint.dynamic_constraints.classification.schema_index import (
    SchemaIndexBuilder,
)
from api_testing.models.specification_model import (
    ItemProperties,
    OperationProperties,
    ParameterProperties,
    ResponseProperties,
)
from api_testing.utils import to_dict_helper


class SpecExcerptBuilder:
    """Build compact, container-aware API specification excerpts.

    The builder is intentionally local to invariant classification. It selects
    only the schema entries relevant to an invariant, applies a small line
    budget, and exposes selected paths for debug artifacts.
    """

    DEFAULT_BUDGETS: dict[InvariantExcerptShape, ExcerptBudgetProfile] = {
        "simple_scalar": ExcerptBudgetProfile(
            max_request_lines=1,
            max_response_lines=1,
            max_container_fields=0,
            max_fallback_paths=3,
        ),
        "nested_object": ExcerptBudgetProfile(
            max_request_lines=2,
            max_response_lines=2,
            max_container_fields=4,
            max_fallback_paths=3,
        ),
        "array_focused": ExcerptBudgetProfile(
            max_request_lines=2,
            max_response_lines=2,
            max_container_fields=4,
            max_fallback_paths=3,
        ),
        "mixed_container_scalar": ExcerptBudgetProfile(
            max_request_lines=2,
            max_response_lines=3,
            max_container_fields=3,
            max_fallback_paths=3,
        ),
    }

    def __init__(self, *, max_array_item_fields: int = 5, max_required_fields: int = 3) -> None:
        self._schema_index_builder = SchemaIndexBuilder(
            max_summary_fields=max_array_item_fields,
            max_required_fields=max_required_fields,
        )
        self._request_index_cache: dict[str, SchemaIndex] = {}
        self._response_index_cache: dict[tuple[str, str], SchemaIndex] = {}

    def build(self, context: NormalizedInvariantContext) -> str:
        """Return only the text excerpt for prompt construction."""
        return self.build_with_debug(context).excerpt

    def build_with_debug(self, context: NormalizedInvariantContext) -> ExcerptBuildResult:
        """Return the prompt excerpt with shape, budget, and selected schema paths."""
        operation = context.operation
        shape = self._classify_excerpt_shape(context)
        budget = self._budget_for_shape(shape)
        request_lines, request_matches = self._build_request_context_lines(context, budget)
        response_lines, response_matches = self._build_response_context_lines(context, budget)

        sections = [f"Endpoint: {operation.http_method.upper()} {operation.endpoint_path}"]
        if operation.summary:
            sections.append(f"Summary: {operation.summary}")
        if (
            shape != "simple_scalar"
            and operation.description
            and operation.description != operation.summary
        ):
            sections.append(f"Description: {operation.description}")

        sections.append("Relevant request inputs:")
        sections.extend(request_lines)
        sections.append(
            f"Relevant response fields for status {context.parsed_program_point.status_code or '2xx'}:"
        )
        sections.extend(response_lines)
        return ExcerptBuildResult(
            excerpt="\n".join(sections),
            shape=shape,
            budget_profile=budget,
            matched_schema_paths=self._matched_schema_paths(
                [*request_matches, *response_matches]
            ),
        )

    def _build_request_context_lines(
        self,
        context: NormalizedInvariantContext,
        budget: ExcerptBudgetProfile,
    ) -> tuple[list[str], list[ExcerptLine]]:
        if not context.input_variables:
            return ["- This invariant does not reference request inputs."], []

        operation = context.operation
        request_index = self._get_request_schema_index(operation)
        ranked_lines: list[ExcerptLine] = []
        required_lines: list[ExcerptLine] = []
        container_lines: list[ExcerptLine] = []
        missing_lines: list[str] = []

        for variable in context.input_variables:
            parameter_match = self._match_parameter(operation, variable, budget)
            if parameter_match is not None:
                ranked_lines.append(parameter_match)
                required_lines.append(parameter_match)
                continue

            variable_matches = self._match_container_and_leaf_entries(
                schema_index=request_index,
                variable=variable,
                container_segments=tuple(),
                source="request",
                source_label="requestBody",
                budget=budget,
            )
            if not variable_matches:
                missing_lines.append(
                    self._missing_request_variable_line(
                        operation=operation,
                        request_index=request_index,
                        variable=variable,
                        budget=budget,
                    )
                )
                continue

            ranked_lines.extend(variable_matches)
            required_lines.append(self._primary_request_line(variable_matches))
            container_lines.extend(line for line in variable_matches if line.is_container)

        selected_lines = self._select_request_entries(
            ranked_lines=ranked_lines,
            required_lines=required_lines,
            container_lines=container_lines,
            budget=budget,
        )
        if selected_lines:
            return [line.line for line in selected_lines] + missing_lines, selected_lines
        if missing_lines:
            return missing_lines, []

        if operation.parameters:
            available_parameters = ", ".join(
                sorted(parameter.name for parameter in operation.parameters.values())
            ) or "<none>"
            return [f"- No direct request input match found. Available parameters: {available_parameters}"], []

        if request_index.arrays or request_index.objects or request_index.leaves:
            nearby_paths = self._nearby_container_paths(
                schema_index=request_index,
                variables=context.input_variables,
                limit=budget.max_fallback_paths,
            )
            if nearby_paths:
                return [
                    "- No direct request body field match found. Nearby schema entries: "
                    + ", ".join(nearby_paths)
                ], []
            return [
                "- No direct request body field match found. Example available fields: "
                + ", ".join(request_index.available_paths(limit=budget.max_fallback_paths))
            ], []

        return ["- No request body schema is defined for this operation."], []

    def _select_request_entries(
        self,
        *,
        ranked_lines: Sequence[ExcerptLine],
        required_lines: Sequence[ExcerptLine],
        container_lines: Sequence[ExcerptLine],
        budget: ExcerptBudgetProfile,
    ) -> list[ExcerptLine]:
        required = self._dedupe_ranked_lines(required_lines)
        containers = self._dedupe_ranked_lines(container_lines)
        effective_max = max(budget.max_request_lines, len(required))
        if containers and required:
            effective_max = max(effective_max, min(len(required) + 1, len(required) + len(containers)))

        selected: list[ExcerptLine] = []
        for line in containers:
            if len(selected) >= effective_max - len(required):
                break
            selected.append(line)
        for line in required:
            if line.path not in {selected_line.path for selected_line in selected}:
                selected.append(line)

        if selected:
            return self._dedupe_ranked_lines(selected)[:effective_max]
        return self._select_ranked_entries(ranked_lines, budget.max_request_lines)

    @staticmethod
    def _primary_request_line(lines: Sequence[ExcerptLine]) -> ExcerptLine:
        for line in lines:
            if not line.is_container:
                return line
        return lines[0]

    @staticmethod
    def _missing_request_variable_line(
        *,
        operation: OperationProperties,
        request_index: SchemaIndex,
        variable: VariableReference,
        budget: ExcerptBudgetProfile,
    ) -> str:
        target = variable.display_path or variable.raw
        if operation.parameters:
            available_parameters = ", ".join(
                sorted(parameter.name for parameter in operation.parameters.values())
            ) or "<none>"
            return (
                f"- No direct request input match found for `{target}`. "
                f"Available parameters: {available_parameters}"
            )

        if request_index.arrays or request_index.objects or request_index.leaves:
            available_paths = ", ".join(request_index.available_paths(limit=budget.max_fallback_paths))
            return (
                f"- No direct request body field match found for `{target}`. "
                f"Example available fields: {available_paths}"
            )

        return f"- No request schema is defined for referenced input `{target}`."

    def _build_response_context_lines(
        self,
        context: NormalizedInvariantContext,
        budget: ExcerptBudgetProfile,
    ) -> tuple[list[str], list[ExcerptLine]]:
        if not context.output_variables:
            return ["- This invariant does not reference response fields."], []

        response_index = self._get_response_schema_index(
            context.operation,
            context.parsed_program_point.status_code,
        )
        ranked_lines: list[ExcerptLine] = []

        for variable in context.output_variables:
            ranked_lines.extend(
                self._match_container_and_leaf_entries(
                    schema_index=response_index,
                    variable=variable,
                    container_segments=context.parsed_program_point.container_segments,
                    source="response",
                    source_label="response",
                    budget=budget,
                )
            )

        selected_lines = self._select_ranked_entries(ranked_lines, budget.max_response_lines)
        if selected_lines:
            return [line.line for line in selected_lines], selected_lines

        if response_index.arrays or response_index.objects or response_index.leaves:
            nearby_paths = self._nearby_container_paths(
                schema_index=response_index,
                variables=context.output_variables,
                limit=budget.max_fallback_paths,
            )
            if nearby_paths:
                return [
                    "- No direct response field match found. Nearby schema entries: "
                    + ", ".join(nearby_paths)
                ], []
            return [
                "- No direct response field match found. Example available fields: "
                + ", ".join(response_index.available_paths(limit=budget.max_fallback_paths))
            ], []

        return ["- No successful response schema could be resolved for this operation."], []

    def _match_parameter(
        self,
        operation: OperationProperties,
        variable: VariableReference,
        budget: ExcerptBudgetProfile,
    ) -> ExcerptLine | None:
        if not variable.path_segments:
            return None

        target_name = variable.path_segments[-1].name or ""
        normalized_target = target_name.lower()

        for parameter in operation.parameters.values():
            if parameter.name.lower() != normalized_target:
                continue

            source_label = parameter.in_value or "parameter"
            return ExcerptLine(
                source="request",
                path=f"parameter:{parameter.name}",
                kind="parameter",
                line=(
                    f"- {source_label} parameter `{parameter.name}`: "
                    f"{self._summarize_parameter(parameter, budget)}"
                ),
                match_score=100,
                is_container=bool(
                    parameter.schema and parameter.schema.type in {"array", "object"}
                ),
                path_depth=1,
            )

        return None

    def _match_container_and_leaf_entries(
        self,
        *,
        schema_index: SchemaIndex,
        variable: VariableReference,
        container_segments: Sequence[PathSegment],
        source: str,
        source_label: str,
        budget: ExcerptBudgetProfile,
    ) -> list[ExcerptLine]:
        candidate_paths = self._candidate_paths(variable, container_segments)
        if not candidate_paths:
            return []

        fallback_tokens = self._path_tokens_from_segments(variable.path_segments)
        primary_path = candidate_paths[0]
        should_include_full_container = variable.is_size or self._path_is_array(primary_path)
        container_candidate_paths = self._container_candidate_paths(
            candidate_paths,
            include_full=should_include_full_container,
        )

        matched_lines: list[ExcerptLine] = []
        for desired_path in container_candidate_paths:
            mapping = schema_index.arrays if self._path_is_array(desired_path) else schema_index.objects
            entry, score = self._match_schema_mapping_entry(
                mapping=mapping,
                candidate_paths=(desired_path,),
                fallback_tokens=fallback_tokens,
            )
            if entry is None:
                continue
            matched_lines.append(
                ExcerptLine(
                    source=source,
                    path=entry.path,
                    kind=entry.kind,
                    line=self._format_schema_entry(source_label, entry, budget),
                    match_score=score,
                    is_container=True,
                    path_depth=self._path_depth(entry.path),
                )
            )

        if not variable.is_size and not self._path_is_array(primary_path):
            leaf_entry, leaf_score = self._match_schema_mapping_entry(
                mapping=schema_index.leaves,
                candidate_paths=tuple(candidate_paths),
                fallback_tokens=fallback_tokens,
            )
            if leaf_entry is not None:
                matched_lines.append(
                    ExcerptLine(
                        source=source,
                        path=leaf_entry.path,
                        kind=leaf_entry.kind,
                        line=self._format_schema_entry(source_label, leaf_entry, budget),
                        match_score=leaf_score,
                        is_container=False,
                        path_depth=self._path_depth(leaf_entry.path),
                    )
                )

        return self._dedupe_ranked_lines(matched_lines)

    def _match_schema_mapping_entry(
        self,
        *,
        mapping: dict[str, SchemaEntry],
        candidate_paths: Sequence[str],
        fallback_tokens: tuple[str, ...],
    ) -> tuple[SchemaEntry | None, int]:
        for candidate_path in candidate_paths:
            exact_match = mapping.get(candidate_path)
            if exact_match is not None:
                return exact_match, 100

        best_match: SchemaEntry | None = None
        best_score = -1
        candidate_tokens = [
            SchemaIndexBuilder.normalize_match_tokens(candidate_path)
            for candidate_path in candidate_paths
            if candidate_path
        ]

        for entry in mapping.values():
            score = max(
                (
                    self._score_match(entry.tokens, candidate_token, fallback_tokens)
                    for candidate_token in candidate_tokens
                ),
                default=0,
            )
            if score > best_score:
                best_score = score
                best_match = entry

        return (best_match, best_score) if best_score > 0 else (None, 0)

    @staticmethod
    def _candidate_paths(
        variable: VariableReference,
        container_segments: Sequence[PathSegment],
    ) -> list[str]:
        variable_path = SpecExcerptBuilder._path_from_segments(variable.path_segments)
        container_path = SpecExcerptBuilder._path_from_segments(container_segments)
        candidates: list[str] = []

        if variable.path_segments and tuple(variable.path_segments) == tuple(container_segments):
            if container_path:
                candidates.append(container_path)

        if variable_path:
            if container_path:
                separator = "" if variable_path.startswith("[") else "."
                candidates.append(f"{container_path}{separator}{variable_path}")
            candidates.append(variable_path)
        elif container_path:
            candidates.append(container_path)

        if variable.is_size and container_path and container_path not in candidates:
            candidates.append(container_path)

        return list(dict.fromkeys(candidate for candidate in candidates if candidate))

    @staticmethod
    def _container_candidate_paths(
        candidate_paths: Sequence[str],
        *,
        include_full: bool,
    ) -> list[str]:
        ordered_paths: list[str] = []
        for path in candidate_paths:
            segments = [segment for segment in path.split(".") if segment]
            if not segments:
                continue
            array_prefixes: list[str] = []
            object_prefixes: list[str] = []
            for index in range(1, len(segments) + 1):
                prefix = ".".join(segments[:index])
                is_last = index == len(segments)
                if is_last:
                    if include_full and SpecExcerptBuilder._path_is_array(prefix):
                        array_prefixes.append(prefix)
                    continue

                if SpecExcerptBuilder._path_is_array(prefix):
                    array_prefixes.append(prefix)
                else:
                    object_prefixes.append(prefix)

            ordered_paths.extend(array_prefixes)
            if object_prefixes:
                ordered_paths.append(object_prefixes[-1])
        return list(dict.fromkeys(ordered_paths))

    @staticmethod
    def _score_match(
        field_tokens: tuple[str, ...],
        preferred_tokens: tuple[str, ...],
        fallback_tokens: tuple[str, ...],
    ) -> int:
        if field_tokens and preferred_tokens and field_tokens == preferred_tokens:
            return 100
        if field_tokens and preferred_tokens and len(field_tokens) >= len(preferred_tokens):
            if field_tokens[-len(preferred_tokens):] == preferred_tokens:
                return 90
        if field_tokens and fallback_tokens and len(field_tokens) >= len(fallback_tokens):
            if field_tokens[-len(fallback_tokens):] == fallback_tokens:
                return 70
        if field_tokens and fallback_tokens and field_tokens[-1] == fallback_tokens[-1]:
            return 50
        return 0

    def _get_request_schema_index(self, operation: OperationProperties) -> SchemaIndex:
        cache_key = operation.uuid or f"{operation.http_method}-{operation.endpoint_path}"
        if cache_key in self._request_index_cache:
            return self._request_index_cache[cache_key]

        index = SchemaIndex()
        for item in (operation.request_body or {}).values():
            index.merge(self._schema_index_builder.build_from_item(item))

        self._request_index_cache[cache_key] = index
        return index

    def _get_response_schema_index(
        self,
        operation: OperationProperties,
        status_code: str,
    ) -> SchemaIndex:
        cache_key = (operation.uuid or f"{operation.http_method}-{operation.endpoint_path}", status_code or "")
        if cache_key in self._response_index_cache:
            return self._response_index_cache[cache_key]

        candidate_status_codes: list[str] = []
        if status_code:
            candidate_status_codes.append(status_code)

        if operation.responses:
            candidate_status_codes.extend(
                str(code)
                for code in operation.responses.keys()
                if str(code).startswith("2") and str(code) not in candidate_status_codes
            )

        index = SchemaIndex()
        for candidate_code in candidate_status_codes:
            for raw_status, response in (operation.responses or {}).items():
                if str(raw_status) != candidate_code:
                    continue
                for item in (response.content or {}).values():
                    index.merge(self._schema_index_builder.build_from_item(item))

        self._response_index_cache[cache_key] = index
        return index

    def _classify_excerpt_shape(
        self,
        context: NormalizedInvariantContext,
    ) -> InvariantExcerptShape:
        has_array_context = False
        has_nested_object = False
        has_top_level_scalar = False

        for variable in (*context.input_variables, *context.output_variables):
            container_segments = (
                context.parsed_program_point.container_segments
                if variable.role == "return"
                else tuple()
            )
            effective_segments = self._effective_segments(variable, container_segments)
            if not effective_segments:
                continue

            named_non_array_segments = [
                segment for segment in effective_segments if segment.name is not None and not segment.is_array
            ]

            if variable.is_size or any(segment.is_array for segment in effective_segments):
                has_array_context = True

            if (
                not variable.is_size
                and len(named_non_array_segments) >= 2
            ):
                has_nested_object = True

            if (
                not variable.is_size
                and len(named_non_array_segments) == 1
                and not any(segment.is_array for segment in effective_segments[:-1])
            ):
                has_top_level_scalar = True

        if (has_array_context and has_nested_object) or (
            has_top_level_scalar and (has_array_context or has_nested_object)
        ):
            return "mixed_container_scalar"
        if has_array_context:
            return "array_focused"
        if has_nested_object:
            return "nested_object"
        return "simple_scalar"

    def _budget_for_shape(self, shape: InvariantExcerptShape) -> ExcerptBudgetProfile:
        return self.DEFAULT_BUDGETS[shape]

    def _format_schema_entry(
        self,
        source_label: str,
        entry: SchemaEntry,
        budget: ExcerptBudgetProfile,
    ) -> str:
        if entry.kind == "array_container":
            summary = self._summarize_array_metadata(entry.metadata, budget)
        elif entry.kind == "object_container":
            summary = self._summarize_object_metadata(entry.metadata, budget)
        else:
            summary = self._summarize_field_metadata(entry.metadata)
        return f"- {source_label} `{entry.path}`: {summary}"

    @staticmethod
    def _summarize_parameter(
        parameter: ParameterProperties,
        budget: ExcerptBudgetProfile,
    ) -> str:
        schema = parameter.schema
        if schema is None:
            return parameter.description or "No schema details available."

        if schema.type == "array":
            metadata = {
                "type": "array",
                "description": parameter.description or schema.description,
                "itemsType": SpecExcerptBuilder._infer_schema_type(schema.items),
            }
            if schema.min_items is not None:
                metadata["minItems"] = schema.min_items
            if schema.max_items is not None:
                metadata["maxItems"] = schema.max_items
            if schema.unique_items is not None:
                metadata["uniqueItems"] = schema.unique_items
            if schema.items and schema.items.description:
                metadata["itemsDescription"] = schema.items.description
            item_fields = SpecExcerptBuilder._direct_child_fields(schema.items)
            if item_fields:
                metadata["itemFields"] = item_fields[: budget.max_container_fields]
            if schema.items and schema.items.enum:
                metadata["itemsEnum"] = schema.items.enum
            if schema.items and schema.items.pattern:
                metadata["itemsPattern"] = schema.items.pattern
            return SpecExcerptBuilder._summarize_array_metadata(metadata, budget)

        if schema.type == "object" or schema.properties or schema.allOf or schema.anyOf or schema.oneOf:
            metadata = {
                "type": "object",
                "description": parameter.description or schema.description,
                "childFields": SpecExcerptBuilder._direct_child_fields(schema)[
                    : budget.max_container_fields
                ],
                "requiredFields": (schema.required or [])[:3],
            }
            return SpecExcerptBuilder._summarize_object_metadata(metadata, budget)

        metadata = to_dict_helper(schema) | {"description": parameter.description or schema.description}
        return SpecExcerptBuilder._summarize_field_metadata(metadata)

    @staticmethod
    def _summarize_array_metadata(
        metadata: dict[str, Any],
        budget: ExcerptBudgetProfile,
    ) -> str:
        parts = [metadata.get("type") or "array"]
        description = metadata.get("description")
        if description:
            parts.append(str(description))

        items_type = metadata.get("itemsType")
        if items_type:
            parts.append(f"items={items_type}")

        item_fields = metadata.get("itemFields")
        if item_fields:
            parts.append(
                f"item fields={', '.join(item_fields[: budget.max_container_fields])}"
            )

        items_description = metadata.get("itemsDescription")
        if items_description:
            parts.append(f"item description={items_description}")

        if metadata.get("itemsEnum"):
            parts.append(f"item enum={metadata['itemsEnum']}")
        if metadata.get("itemsPattern"):
            parts.append(f"item pattern={metadata['itemsPattern']}")
        if metadata.get("minItems") is not None:
            parts.append(f"minItems={metadata['minItems']}")
        if metadata.get("maxItems") is not None:
            parts.append(f"maxItems={metadata['maxItems']}")
        if metadata.get("uniqueItems") is True:
            parts.append("uniqueItems=True")

        return "; ".join(str(part) for part in parts)

    @staticmethod
    def _summarize_object_metadata(
        metadata: dict[str, Any],
        budget: ExcerptBudgetProfile,
    ) -> str:
        parts = [metadata.get("type") or "object"]
        description = metadata.get("description")
        if description:
            parts.append(str(description))

        child_fields = metadata.get("childFields")
        if child_fields:
            parts.append(
                f"fields={', '.join(child_fields[: budget.max_container_fields])}"
            )

        required_fields = metadata.get("requiredFields")
        if required_fields:
            parts.append(f"required={', '.join(required_fields[:3])}")

        return "; ".join(str(part) for part in parts)

    @staticmethod
    def _summarize_field_metadata(metadata: dict[str, Any]) -> str:
        parts = [metadata.get("type") or "unknown"]
        description = metadata.get("description")
        if description:
            parts.append(str(description))
        if metadata.get("format"):
            parts.append(f"format={metadata['format']}")
        if metadata.get("enum"):
            parts.append(f"enum={metadata['enum']}")
        if metadata.get("minimum") is not None:
            parts.append(f"min={metadata['minimum']}")
        if metadata.get("maximum") is not None:
            parts.append(f"max={metadata['maximum']}")
        if metadata.get("pattern"):
            parts.append(f"pattern={metadata['pattern']}")
        return "; ".join(str(part) for part in parts)

    @staticmethod
    def _nearby_container_paths(
        *,
        schema_index: SchemaIndex,
        variables: Sequence[VariableReference],
        limit: int,
    ) -> list[str]:
        scored_paths: list[tuple[int, str]] = []
        for variable in variables:
            fallback_tokens = SpecExcerptBuilder._path_tokens_from_segments(variable.path_segments)
            for entry in list(schema_index.arrays.values()) + list(schema_index.objects.values()):
                score = SpecExcerptBuilder._score_match(entry.tokens, fallback_tokens, fallback_tokens)
                if score > 0:
                    scored_paths.append((score, entry.path))

        if not scored_paths:
            return schema_index.available_paths(limit=limit)

        ordered: list[str] = []
        for _, path in sorted(scored_paths, key=lambda item: (-item[0], item[1])):
            if path not in ordered:
                ordered.append(path)
            if len(ordered) >= limit:
                break
        return ordered

    @staticmethod
    def _effective_segments(
        variable: VariableReference,
        container_segments: Sequence[PathSegment],
    ) -> tuple[PathSegment, ...]:
        return tuple(container_segments) + tuple(variable.path_segments)

    @staticmethod
    def _path_from_segments(segments: Sequence[PathSegment]) -> str:
        return ".".join(segment.display() for segment in segments if segment.display())

    @staticmethod
    def _path_tokens_from_segments(segments: Sequence[PathSegment]) -> tuple[str, ...]:
        tokens = []
        for segment in segments:
            if segment.name:
                tokens.append(segment.name.lower())
        return tuple(tokens)

    @staticmethod
    def _path_is_array(path: str) -> bool:
        return path == "[]" or path.endswith("[]")

    @staticmethod
    def _path_depth(path: str) -> int:
        return len([segment for segment in path.split(".") if segment])

    @staticmethod
    def _dedupe_ranked_lines(lines: Sequence[ExcerptLine]) -> list[ExcerptLine]:
        best_by_path: dict[str, ExcerptLine] = {}
        order: list[str] = []
        for line in lines:
            if line.path not in best_by_path:
                order.append(line.path)
                best_by_path[line.path] = line
                continue
            if line.match_score > best_by_path[line.path].match_score:
                best_by_path[line.path] = line
        return [best_by_path[path] for path in order]

    def _select_ranked_entries(
        self,
        lines: Sequence[ExcerptLine],
        max_lines: int,
    ) -> list[ExcerptLine]:
        if max_lines <= 0:
            return []
        deduped = self._dedupe_ranked_lines(lines)
        return deduped[:max_lines]

    def _select_ranked_lines(
        self,
        lines: Sequence[ExcerptLine],
        max_lines: int,
    ) -> list[str]:
        return [line.line for line in self._select_ranked_entries(lines, max_lines)]

    @staticmethod
    def _matched_schema_paths(lines: Sequence[ExcerptLine]) -> tuple[MatchedSchemaPath, ...]:
        return tuple(
            MatchedSchemaPath(
                source=line.source,
                path=line.path,
                kind=line.kind,
                match_score=line.match_score,
            )
            for line in lines
        )

    @staticmethod
    def _infer_schema_type(schema: ItemProperties | None) -> str | None:
        if schema is None:
            return None
        if schema.type:
            return schema.type
        if schema.properties:
            return "object"
        if schema.items:
            return "array"
        if schema.allOf or schema.anyOf or schema.oneOf:
            return "object"
        return None

    @staticmethod
    def _direct_child_fields(schema: ItemProperties | None) -> list[str]:
        if schema is None:
            return []
        if schema.allOf:
            names: list[str] = []
            for item in schema.allOf:
                names.extend(SpecExcerptBuilder._direct_child_fields(item))
            return sorted(dict.fromkeys(names))
        if not schema.properties:
            return []
        names = []
        for key, value in schema.properties.items():
            suffix = "[]" if value and value.type == "array" else ""
            names.append(f"{key}{suffix}")
        return sorted(names)


def main() -> None:
    """Print a self-contained spec excerpt demo without calling an LLM."""
    operation = OperationProperties(
        uuid="get-/widgets",
        operation_id="listWidgets",
        endpoint_path="/widgets",
        http_method="get",
        summary="List widgets",
        description="Returns widgets with owner metadata.",
        responses={
            "200": ResponseProperties(
                status_code="200",
                description="Widget list",
                content={
                    "application/json": ItemProperties(
                        type="object",
                        properties={
                            "items": ItemProperties(
                                type="array",
                                description="Collection of widgets",
                                items=ItemProperties(
                                    type="object",
                                    properties={
                                        "owner": ItemProperties(
                                            type="object",
                                            description="Widget owner",
                                            required=["id", "name"],
                                            properties={
                                                "id": ItemProperties(type="integer"),
                                                "name": ItemProperties(
                                                    type="string",
                                                    description="Owner display name",
                                                ),
                                            },
                                        )
                                    },
                                ),
                            ),
                            "totalResults": ItemProperties(
                                type="integer",
                                description="Total matching widgets",
                            ),
                        },
                    )
                },
            )
        },
    )
    context = NormalizedInvariantContext(
        record=SimpleNamespace(),
        parsed_program_point=ParsedProgramPoint(
            raw="get-/widgets&get-/widgets&200&items():::EXIT",
            operation_key="get-/widgets",
            http_method="get",
            endpoint_path="/widgets",
            status_code="200",
            program_point="EXIT",
            container_segments=(PathSegment(name="items", is_array=True),),
        ),
        operation=operation,
        invariant_description="Demo invariant",
        input_variables=tuple(),
        output_variables=(
            VariableReference(
                raw="return.owner.name",
                role="return",
                is_size=False,
                path_segments=(
                    PathSegment(name="owner"),
                    PathSegment(name="name"),
                ),
                display_path="owner.name",
            ),
        ),
    )

    result = SpecExcerptBuilder().build_with_debug(context)
    print(
        json.dumps(
            {
                "excerpt": result.excerpt,
                "shape": result.shape,
                "budget_profile": asdict(result.budget_profile),
                "matched_schema_paths": [
                    asdict(matched_path)
                    for matched_path in result.matched_schema_paths
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
