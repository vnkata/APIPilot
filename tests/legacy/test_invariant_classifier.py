from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner
from api_testing.constraint.dynamic_constraints.classified_invariant_reader import (
    CLASSIFIED_INVARIANTS_HEADER,
    ClassifiedInvariantReader,
)
from api_testing.constraint.dynamic_constraints.invariant_classifier import (
    InvariantClassifier,
)
from api_testing.constraint.dynamic_constraints.classification.evidence_checker import (
    analyze_observed_examples,
)
from api_testing.constraint.dynamic_constraints.invariant_extractor import (
    EXPECTED_INVARIANTS_HEADER,
)
from api_testing.constraint.dynamic_constraints.invariant_reader import InvariantReader
from api_testing.models.llms.openai_model import OpenAIModel
from api_testing.prompts.invariant_classification import InvariantClassificationPrompt
from api_testing.models.specification_model import (
    ItemProperties,
    OperationProperties,
    ParameterProperties,
    ResponseProperties,
)
from api_testing.dataset.specification_parser import SpecificationParser


class StaticClassificationModel:
    def __init__(self, payload: dict | None = None, *, should_raise: Exception | None = None):
        self.payload = payload or {
            "verdict": "true-positive",
            "confidence": 0.88,
            "reason": "The invariant aligns with the specification and observed examples.",
        }
        self.should_raise = should_raise
        self.calls = 0

    def generate(self, prompt, system_prompt=None, schema=None):
        if self.should_raise is not None:
            raise self.should_raise
        self.calls += 1
        if schema is None:
            return json.dumps(self.payload), 0
        return schema.model_validate(self.payload), 0

    def get_model_name(self) -> str:
        return "static-test-model"


class InvalidPayloadModel:
    def generate(self, prompt, system_prompt=None, schema=None):
        return "not-a-structured-response", 0

    def get_model_name(self) -> str:
        return "invalid-payload-model"


class TestInvariantClassificationPrompt:
    def test_parse_response_accepts_valid_json(self):
        result = InvariantClassificationPrompt.parse_response(
            '{"verdict":"true-positive","confidence":0.9,"reason":"ok"}'
        )

        assert result.verdict.value == "true-positive"
        assert result.confidence == pytest.approx(0.9)

    def test_parse_response_accepts_fenced_json(self):
        result = InvariantClassificationPrompt.parse_response(
            '```json\n{"verdict":"false-positive","confidence":0.75,"reason":"overfit"}\n```'
        )

        assert result.verdict.value == "false-positive"
        assert result.confidence == pytest.approx(0.75)

    def test_parse_response_extracts_json_from_extra_text(self):
        result = InvariantClassificationPrompt.parse_response(
            'Here is the result: {"verdict":"inconclusive","confidence":0.4,"reason":"weak spec"}'
        )

        assert result.verdict.value == "inconclusive"
        assert result.confidence == pytest.approx(0.4)

    def test_parse_response_repairs_clear_confidence_labels(self):
        result = InvariantClassificationPrompt.parse_response(
            '{"verdict":"true-positive","confidence":"high","reason":"ok"}'
        )

        assert result.confidence == pytest.approx(0.8)

    def test_parse_response_rejects_invalid_verdict(self):
        with pytest.raises(Exception):
            InvariantClassificationPrompt.parse_response(
                '{"verdict":"probably","confidence":0.7,"reason":"bad"}'
            )


class TestObservedEvidenceAnalysis:
    def test_one_of_scalar_treats_json_booleans_as_daikon_zero_one_values(self):
        analysis = analyze_observed_examples(
            "return.isAct one of { 0, 1 }",
            ["return.isAct=false", "return.isAct=true"],
        )

        assert analysis.status == "evaluated"
        assert analysis.support_count == 2
        assert analysis.contradiction_count == 0


def _build_widget_operation() -> OperationProperties:
    return OperationProperties(
        uuid="get-/widgets",
        operation_id="listWidgets",
        endpoint_path="/widgets",
        http_method="get",
        summary="List widgets",
        description="Returns widgets that match the provided filters.",
        parameters={
            "category": ParameterProperties(
                name="category",
                in_value="query",
                description="Widget category filter",
                required=False,
                schema=ItemProperties(type="string", enum=["books", "games"]),
            ),
            "ids": ParameterProperties(
                name="ids",
                in_value="query",
                description="Widget identifier filters",
                required=False,
                schema=ItemProperties(
                    type="array",
                    min_items=1,
                    max_items=10,
                    items=ItemProperties(type="integer"),
                ),
            ),
            "Take": ParameterProperties(
                name="Take",
                in_value="query",
                description="Maximum number of widgets to return",
                required=False,
                schema=ItemProperties(type="integer", minimum=1, maximum=100),
            ),
        },
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
                                        "id": ItemProperties(type="integer", description="Widget identifier"),
                                        "category": ItemProperties(
                                            type="string",
                                            description="Widget category",
                                            enum=["books", "games"],
                                        ),
                                        "owner": ItemProperties(
                                            type="object",
                                            description="Widget owner",
                                            required=["id", "name"],
                                            properties={
                                                "id": ItemProperties(
                                                    type="integer",
                                                    description="Owner identifier",
                                                ),
                                                "name": ItemProperties(
                                                    type="string",
                                                    description="Owner display name",
                                                ),
                                                "role": ItemProperties(
                                                    type="string",
                                                    description="Owner role",
                                                ),
                                            },
                                        ),
                                        "tags": ItemProperties(
                                            type="array",
                                            description="Widget tags",
                                            items=ItemProperties(type="string"),
                                        ),
                                    },
                                ),
                            ),
                            "totalResults": ItemProperties(type="integer", description="Total widgets"),
                            "itemsPerPage": ItemProperties(type="integer", description="Returned item count"),
                            "pagination": ItemProperties(
                                type="object",
                                description="Pagination metadata",
                                required=["page", "totalPages"],
                                properties={
                                    "page": ItemProperties(
                                        type="integer",
                                        description="Current page",
                                    ),
                                    "totalPages": ItemProperties(
                                        type="integer",
                                        description="Total pages",
                                    ),
                                },
                            ),
                        },
                    )
                },
            )
        },
    )


def _build_widget_search_operation() -> OperationProperties:
    return OperationProperties(
        uuid="post-/widgets/search",
        operation_id="searchWidgets",
        endpoint_path="/widgets/search",
        http_method="post",
        summary="Search widgets",
        description="Search widgets with nested filter criteria.",
        request_body={
            "application/json": ItemProperties(
                type="object",
                properties={
                    "filters": ItemProperties(
                        type="object",
                        description="Widget search filters",
                        properties={
                            "dateRange": ItemProperties(
                                type="object",
                                description="Inclusive date range filter",
                                required=["start", "end"],
                                properties={
                                    "start": ItemProperties(
                                        type="string",
                                        format="date-time",
                                        description="Range start",
                                    ),
                                    "end": ItemProperties(
                                        type="string",
                                        format="date-time",
                                        description="Range end",
                                    ),
                                },
                            ),
                            "status": ItemProperties(
                                type="string",
                                description="Widget status filter",
                            ),
                        },
                    )
                },
            )
        },
        responses={
            "200": ResponseProperties(
                status_code="200",
                description="Search results",
                content={
                    "application/json": ItemProperties(
                        type="object",
                        properties={
                            "items": ItemProperties(
                                type="array",
                                items=ItemProperties(
                                    type="object",
                                    properties={
                                        "id": ItemProperties(type="integer", description="Widget identifier"),
                                    },
                                ),
                            )
                        },
                    )
                },
            )
        },
    )


def _build_projects_operation() -> OperationProperties:
    return OperationProperties(
        uuid="get-/projects",
        operation_id="listProjects",
        endpoint_path="/projects",
        http_method="get",
        summary="List projects",
        description="Returns visible projects.",
        responses={
            "200": ResponseProperties(
                status_code="200",
                description="Projects",
                content={
                    "application/json": ItemProperties(
                        type="array",
                        items=ItemProperties(
                            type="object",
                            properties={
                                "id": ItemProperties(type="integer", description="Project identifier"),
                                "name": ItemProperties(type="string", description="Project name"),
                            },
                        ),
                    )
                },
            )
        },
    )


def _build_spec_parser() -> SimpleNamespace:
    widgets = _build_widget_operation()
    widget_search = _build_widget_search_operation()
    projects = _build_projects_operation()
    return SimpleNamespace(
        operations={
            widgets.uuid: widgets,
            widget_search.uuid: widget_search,
            projects.uuid: projects,
        }
    )


def _write_test_cases_json(cache_dir: Path) -> None:
    payload = [
        {
            "test_case_id": "case-1",
            "operation_id": "get-/widgets",
            "path": "/widgets",
            "http_method": "GET",
            "parameters": {"category": "books", "Take": 20},
            "request_body": {},
            "status_code": 200,
            "response_body": json.dumps(
                {
                    "items": [
                        {
                            "id": 1,
                            "category": "books",
                            "owner": {"id": 10, "name": "alice", "role": "maintainer"},
                            "tags": ["featured", "sale"],
                        },
                        {
                            "id": 2,
                            "category": "books",
                            "owner": {"id": 11, "name": "bob", "role": "editor"},
                            "tags": ["new"],
                        },
                    ],
                    "totalResults": 2,
                    "itemsPerPage": 20,
                    "pagination": {"page": 1, "totalPages": 3},
                }
            ),
        }
    ]
    (cache_dir / "test_cases.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_projects_test_cases_json(cache_dir: Path) -> None:
    payload = [
        {
            "test_case_id": "projects-1",
            "operation_id": "get-/projects",
            "path": "/projects",
            "http_method": "GET",
            "parameters": {},
            "request_body": {},
            "status_code": 200,
            "response_body": json.dumps(
                [
                    {"id": 1, "name": "alpha"},
                    {"id": 2, "name": "beta"},
                ]
            ),
        }
    ]
    (cache_dir / "test_cases.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _section_lines(excerpt: str, header: str) -> list[str]:
    lines = excerpt.splitlines()
    try:
        start_index = lines.index(header) + 1
    except ValueError as exc:
        raise AssertionError(f"Missing excerpt section header: {header}") from exc

    collected: list[str] = []
    for line in lines[start_index:]:
        if line.endswith(":") and not line.startswith("- "):
            break
        if line.startswith("- "):
            collected.append(line)
    return collected


def _write_invariants_csv(cache_dir: Path, row: str) -> Path:
    path = cache_dir / "invariants.csv"
    path.write_text(
        EXPECTED_INVARIANTS_HEADER + "\n" + row + "\n",
        encoding="utf-8",
    )
    return path


class TestInvariantClassifier:
    def test_parse_pptname_supports_nested_and_root_array_program_points(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )

        nested = classifier._parse_pptname("get-/widgets&get-/widgets&200&items():::EXIT")
        root_array = classifier._parse_pptname("get-/projects&get-/projects&200%array():::EXIT")

        assert nested.operation_key == "get-/widgets"
        assert nested.status_code == "200"
        assert nested.response_container_path == "items[]"

        assert root_array.operation_key == "get-/projects"
        assert root_array.status_code == "200"
        assert root_array.response_container_path == "[]"

    def test_build_spec_excerpt_includes_relevant_parameter_and_response_fields(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200&items():::EXIT;"
            "input.category == return.category;"
            "daikon.inv.binary.twoString.StringEqual;"
            "(input.category, return.category);"
            "pm.expect(input_category).to.eql(return_category)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "GET /widgets" in excerpt
        assert "query parameter `category`" in excerpt
        assert "response `items[].category`" in excerpt
        assert "response `items[].category`: string; Widget category" in excerpt

    def test_build_spec_excerpt_includes_all_referenced_request_parameters(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::ENTER;"
            "input.category == input.Take;"
            "daikon.inv.binary.twoString.StringEqual;"
            "(input.category, input.Take);"
            "pm.expect(category).to.eql(take)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt_result = classifier.spec_excerpt_builder.build_with_debug(context)
        excerpt = excerpt_result.excerpt
        matched_paths = {
            (matched.source, matched.path, matched.kind)
            for matched in excerpt_result.matched_schema_paths
        }

        assert "query parameter `category`" in excerpt
        assert "query parameter `Take`" in excerpt
        assert ("request", "parameter:category", "parameter") in matched_paths
        assert ("request", "parameter:Take", "parameter") in matched_paths

    def test_build_spec_excerpt_reports_missing_referenced_request_parameter(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::ENTER;"
            "input.category == input.membership;"
            "daikon.inv.binary.twoString.StringEqual;"
            "(input.category, input.membership);"
            "pm.expect(category).to.eql(membership)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "query parameter `category`" in excerpt
        assert "No direct request input match found for `membership`" in excerpt
        assert "Available parameters: Take, category, ids" in excerpt

    def test_build_spec_excerpt_includes_request_array_parameter_semantics(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::EXIT;"
            "size(input.ids[]) >= 1;"
            "daikon.inv.unary.scalar.LowerBound;"
            "(size(input.ids[..]));"
            "pm.expect(ids_length).to.be.at.least(1)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "query parameter `ids`" in excerpt
        assert "array" in excerpt
        assert "items=integer" in excerpt
        assert "minItems=1" in excerpt
        assert "maxItems=10" in excerpt

    def test_build_spec_excerpt_includes_response_array_container_semantics(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::EXIT;"
            "size(return.items[]) one of { 2 };"
            "daikon.inv.unary.scalar.OneOfScalar;"
            "(size(return.items[..]));"
            "pm.expect(items_length).to.eql(2)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "response `items[]`" in excerpt
        assert "array; Collection of widgets" in excerpt
        assert "items=object" in excerpt
        assert "item fields=category, id, owner, tags[]" in excerpt

    def test_build_spec_excerpt_includes_nested_response_array_semantics(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200&items():::EXIT;"
            "size(return.tags[]) >= 1;"
            "daikon.inv.unary.scalar.LowerBound;"
            "(size(return.tags[..]));"
            "pm.expect(tags_length).to.be.at.least(1)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "response `items[].tags[]`" in excerpt
        assert "array; Widget tags" in excerpt
        assert "items=string" in excerpt

    def test_build_spec_excerpt_includes_root_array_semantics(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/projects&get-/projects&200%array():::EXIT;"
            "size(return[]) one of { 2 };"
            "daikon.inv.unary.scalar.OneOfScalar;"
            "(size(return[..]));"
            "pm.expect(projects_length).to.eql(2)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_projects_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "response `[]`" in excerpt
        assert "array" in excerpt
        assert "items=object" in excerpt
        assert "item fields=id, name" in excerpt

    def test_build_spec_excerpt_includes_mixed_scalar_and_array_semantics(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::EXIT;"
            "return.totalResults >= size(return.items[]);"
            "daikon.inv.binary.twoScalar.IntGreaterEqual;"
            "(return.totalResults, size(return.items[..]));"
            "pm.expect(total_results).to.be.at.least(items_length)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "response `totalResults`: integer; Total widgets" in excerpt
        assert "response `items[]`" in excerpt

    def test_build_spec_excerpt_includes_nested_response_object_context(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::EXIT;"
            "return.pagination.totalPages >= 1;"
            "daikon.inv.unary.scalar.LowerBound;"
            "(return.pagination.totalPages);"
            "pm.expect(total_pages).to.be.at.least(1)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)
        response_lines = _section_lines(excerpt, "Relevant response fields for status 200:")

        assert "response `pagination`: object; Pagination metadata; fields=page, totalPages; required=page, totalPages" in excerpt
        assert "response `pagination.totalPages`: integer; Total pages" in excerpt
        assert len(response_lines) <= 2

    def test_build_spec_excerpt_includes_nested_request_object_context(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "post-/widgets/search&post-/widgets/search&200():::EXIT;"
            "input.filters.dateRange.start != input.filters.dateRange.end;"
            "daikon.inv.binary.twoString.StringNotEqual;"
            "(input.filters.dateRange.start, input.filters.dateRange.end);"
            "pm.expect(start_date).to.not.eql(end_date)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)
        request_lines = _section_lines(excerpt, "Relevant request inputs:")

        assert "requestBody `filters.dateRange`: object; Inclusive date range filter; fields=end, start; required=start, end" in excerpt
        assert "requestBody `filters.dateRange.start`: string; Range start; format=date-time" in excerpt
        assert "requestBody `filters.dateRange.end`: string; Range end; format=date-time" in excerpt
        assert len(request_lines) <= 3

    def test_build_spec_excerpt_includes_object_context_inside_array(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200&items():::EXIT;"
            "return.owner.name != \"\";"
            "daikon.inv.unary.stringsequence.OneOfStringSequence;"
            "(return.owner.name);"
            "pm.expect(owner_name).to.not.eql('')"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt_result = classifier.spec_excerpt_builder.build_with_debug(context)
        excerpt = excerpt_result.excerpt
        response_lines = _section_lines(excerpt, "Relevant response fields for status 200:")
        matched_paths = {
            (matched.source, matched.path, matched.kind)
            for matched in excerpt_result.matched_schema_paths
        }

        assert "response `items[]`: array; Collection of widgets; items=object; item fields=category, id, owner" in excerpt
        assert "response `items[].owner`: object; Widget owner; fields=id, name, role; required=id, name" in excerpt
        assert "response `items[].owner.name`: string; Owner display name" in excerpt
        assert ("response", "items[]", "array_container") in matched_paths
        assert ("response", "items[].owner", "object_container") in matched_paths
        assert ("response", "items[].owner.name", "leaf") in matched_paths
        assert len(response_lines) <= 3

    def test_build_spec_excerpt_limits_mixed_scalar_and_nested_object_budget(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/widgets&get-/widgets&200():::EXIT;"
            "return.totalResults >= return.pagination.totalPages;"
            "daikon.inv.binary.twoScalar.IntGreaterEqual;"
            "(return.totalResults, return.pagination.totalPages);"
            "pm.expect(total_results).to.be.at.least(total_pages)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)
        response_lines = _section_lines(excerpt, "Relevant response fields for status 200:")

        assert "response `totalResults`: integer; Total widgets" in excerpt
        assert "response `pagination`: object; Pagination metadata; fields=page, totalPages; required=page, totalPages" in excerpt
        assert "response `pagination.totalPages`: integer; Total pages" in excerpt
        assert len(response_lines) <= 3

    def test_build_spec_excerpt_omits_placeholder_summary_for_simple_scalar_shape(self, tmp_path: Path):
        operation = OperationProperties(
            uuid="get-/scalar-only",
            operation_id="scalarOnly",
            endpoint_path="/scalar-only",
            http_method="get",
            summary=None,
            description="Scalar-only endpoint.",
            responses={
                "200": ResponseProperties(
                    status_code="200",
                    content={
                        "application/json": ItemProperties(
                            type="object",
                            properties={
                                "totalResults": ItemProperties(
                                    type="integer",
                                    description="Total widgets",
                                )
                            },
                        )
                    },
                )
            },
        )
        spec_parser = SimpleNamespace(operations={operation.uuid: operation})
        classifier = InvariantClassifier(
            spec_parser=spec_parser,
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        record_row = (
            "get-/scalar-only&get-/scalar-only&200():::EXIT;"
            "return.totalResults >= 1;"
            "daikon.inv.unary.scalar.LowerBound;"
            "(return.totalResults);"
            "pm.expect(total_results).to.be.at.least(1)"
        )
        _write_invariants_csv(tmp_path, record_row)
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        excerpt = classifier._build_spec_excerpt(context)

        assert "Summary:" not in excerpt

    def test_classify_invariants_writes_csv_and_reader_returns_typed_records(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "input.category == return.category;"
                "daikon.inv.binary.twoString.StringEqual;"
                "(input.category, return.category);"
                "pm.expect(input_category).to.eql(return_category)"
            ),
        )
        _write_test_cases_json(tmp_path)

        output_path = classifier.classify_invariants()
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)

        assert output_path.exists()
        assert len(records) == 1
        assert records[0].verdict == "true-positive"
        assert records[0].confidence == pytest.approx(0.88)
        assert records[0].examples_count >= 1
        assert records[0].approx_number_of_operations == 1
        assert records[0].model == "static-test-model"

    def test_classify_invariants_resumes_existing_output_and_writes_summary(self, tmp_path: Path):
        model = StaticClassificationModel()
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=model,
            cache_dir=tmp_path,
        )
        rows = [
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "input.category == return.category;"
                "daikon.inv.binary.twoString.StringEqual;"
                "(input.category, return.category);"
                "pm.expect(input_category).to.eql(return_category)"
            ),
            (
                "get-/widgets&get-/widgets&200():::EXIT;"
                "return.id >= 1;"
                "daikon.inv.unary.scalar.LowerBound;"
                "(return.id);"
                "pm.expect(return_id).to.be.at.least(1)"
            ),
        ]
        (tmp_path / "invariants.csv").write_text(
            EXPECTED_INVARIANTS_HEADER + "\n" + "\n".join(rows) + "\n",
            encoding="utf-8",
        )
        _write_test_cases_json(tmp_path)
        output_path = tmp_path / "classified_invariants.live.csv"
        output_path.write_text(
            CLASSIFIED_INVARIANTS_HEADER
            + "\n"
            + (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "input.category == return.category;"
                "daikon.inv.binary.twoString.StringEqual;"
                "(input.category, return.category);"
                "pm.expect(input_category).to.eql(return_category);"
                "false-positive;0.2500;preexisting row;old-model;old-prompt;1;1"
            )
            + "\n",
            encoding="utf-8",
        )
        summary_json_path = tmp_path / "summary.json"
        summary_csv_path = tmp_path / "summary.csv"

        classifier.classify_invariants(
            output_path=output_path,
            resume=True,
            max_workers=2,
            summary_json_path=summary_json_path,
            summary_csv_path=summary_csv_path,
        )
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)
        summary = json.loads(summary_json_path.read_text(encoding="utf-8"))

        assert len(records) == 2
        assert records[0].verdict == "false-positive"
        assert records[0].model == "old-model"
        assert records[1].verdict == "true-positive"
        assert model.calls == 1
        assert summary["skipped_records"] == 1
        assert summary["processed_records"] == 1
        assert summary["max_workers"] == 2
        assert summary_csv_path.exists()

    def test_classify_invariants_corrects_impossible_observed_contradiction_reason(
        self,
        tmp_path: Path,
    ):
        model = StaticClassificationModel(
            payload={
                "verdict": "false-positive",
                "confidence": 0.8,
                "reason": (
                    "The invariant is contradicted by the presence of negative "
                    "input.Take values while return.itemsPerPage is positive."
                ),
            }
        )
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=model,
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200():::EXIT;"
                "input.Take <= return.itemsPerPage;"
                "daikon.inv.binary.twoScalar.IntLessEqual;"
                "(input.Take, return.itemsPerPage);"
                "pm.expect(take).to.be.at.most(items_per_page)"
            ),
        )
        _write_test_cases_json(tmp_path)

        output_path = classifier.classify_invariants()
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)

        assert records[0].verdict == "true-positive"
        assert "deterministic observed-evidence check" in records[0].reason.lower()
        assert "no observed contradiction" in records[0].reason.lower()

    def test_classify_invariants_corrects_exact_spec_enum_hallucination(self, tmp_path: Path):
        model = StaticClassificationModel(
            payload={
                "verdict": "false-positive",
                "confidence": 0.8,
                "reason": (
                    "The API specification only documents the enum value 'books', "
                    "so 'games' contradicts the spec."
                ),
            }
        )
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=model,
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                'return.category one of { "books", "games" };'
                "daikon.inv.unary.string.OneOfString;"
                "(return.category);"
                "pm.expect(category).to.be.oneOf(['books', 'games'])"
            ),
        )
        _write_test_cases_json(tmp_path)

        output_path = classifier.classify_invariants()
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)

        assert records[0].verdict == "true-positive"
        assert "deterministic spec check" in records[0].reason.lower()
        assert "match the documented enum" in records[0].reason.lower()

    def test_classify_invariants_preserves_broader_spec_enum_false_positive(self, tmp_path: Path):
        model = StaticClassificationModel(
            payload={
                "verdict": "true-positive",
                "confidence": 0.9,
                "reason": "The observed examples support the invariant.",
            }
        )
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=model,
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                'return.category one of { "books" };'
                "daikon.inv.unary.string.OneOfString;"
                "(return.category);"
                "pm.expect(category).to.be.oneOf(['books'])"
            ),
        )
        _write_test_cases_json(tmp_path)

        output_path = classifier.classify_invariants()
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)

        assert records[0].verdict == "false-positive"
        assert "spec enum allows additional value(s)" in records[0].reason.lower()

    def test_classify_invariants_falls_back_to_inconclusive_when_model_output_is_invalid(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=InvalidPayloadModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "input.category == return.category;"
                "daikon.inv.binary.twoString.StringEqual;"
                "(input.category, return.category);"
                "pm.expect(input_category).to.eql(return_category)"
            ),
        )
        _write_test_cases_json(tmp_path)

        output_path = classifier.classify_invariants()
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)

        assert records[0].verdict == "inconclusive"
        assert records[0].confidence == 0.0
        assert "JSONDecodeError" in records[0].reason

    def test_classify_invariants_falls_back_to_inconclusive_when_context_resolution_fails(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/unknown&get-/unknown&200():::EXIT;"
                "return.id >= 1;"
                "daikon.inv.unary.scalar.LowerBound;"
                "(return.id);"
                "pm.expect(return_id).to.be.at.least(1)"
            ),
        )
        _write_test_cases_json(tmp_path)

        output_path = classifier.classify_invariants()
        records = ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(output_path)

        assert records[0].verdict == "inconclusive"
        assert "Unable to resolve operation" in records[0].reason

    def test_classify_invariants_persists_debug_artifacts_when_enabled(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "input.category == return.category;"
                "daikon.inv.binary.twoString.StringEqual;"
                "(input.category, return.category);"
                "pm.expect(input_category).to.eql(return_category)"
            ),
        )
        _write_test_cases_json(tmp_path)

        classifier.classify_invariants(persist_debug_artifacts=True)

        debug_files = list((tmp_path / "classification_debug").glob("*.json"))
        assert debug_files
        debug_payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
        assert "spec_excerpt" in debug_payload
        assert debug_payload["spec_excerpt_debug"]["shape"] == "mixed_container_scalar"
        assert debug_payload["spec_excerpt_debug"]["budget_profile"]["max_request_lines"] == 2
        assert debug_payload["spec_excerpt_debug"]["budget_profile"]["max_response_lines"] == 3
        matched_paths = {
            (matched["source"], matched["path"], matched["kind"])
            for matched in debug_payload["spec_excerpt_debug"]["matched_schema_paths"]
        }
        assert ("request", "parameter:category", "parameter") in matched_paths
        assert ("response", "items[]", "array_container") in matched_paths
        assert ("response", "items[].category", "leaf") in matched_paths

    def test_classify_invariants_persists_excerpt_debug_even_when_model_call_fails(
        self,
        tmp_path: Path,
    ):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(should_raise=RuntimeError("model exploded")),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200():::EXIT;"
                "return.totalResults >= size(return.items[]);"
                "daikon.inv.binary.twoScalar.IntGreaterEqual;"
                "(return.totalResults, size(return.items[..]));"
                "pm.expect(total_results).to.be.at.least(items_length)"
            ),
        )
        _write_test_cases_json(tmp_path)

        classifier.classify_invariants(persist_debug_artifacts=True)

        debug_files = list((tmp_path / "classification_debug").glob("*.json"))
        assert debug_files
        debug_payload = json.loads(debug_files[0].read_text(encoding="utf-8"))
        assert debug_payload["spec_excerpt_debug"]["shape"] == "mixed_container_scalar"
        assert debug_payload["spec_excerpt_debug"]["budget_profile"]["max_response_lines"] == 3
        matched_paths = {
            (matched["source"], matched["path"], matched["kind"])
            for matched in debug_payload["spec_excerpt_debug"]["matched_schema_paths"]
        }
        assert ("response", "totalResults", "leaf") in matched_paths
        assert ("response", "items[]", "array_container") in matched_paths
        assert "spec_excerpt" in debug_payload
        assert "RuntimeError: model exploded" == debug_payload["error"]

    def test_build_with_debug_returns_excerpt_and_metadata(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200():::EXIT;"
                "return.totalResults >= 1;"
                "daikon.inv.unary.scalar.LowerBound;"
                "(return.totalResults);"
                "pm.expect(total_results).to.be.at.least(1)"
            ),
        )
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)

        excerpt_result = classifier.spec_excerpt_builder.build_with_debug(context)
        excerpt = classifier._build_spec_excerpt(context)

        assert excerpt_result.excerpt == excerpt
        assert excerpt_result.shape == "simple_scalar"
        assert excerpt_result.budget_profile.max_request_lines == 1
        assert excerpt_result.budget_profile.max_response_lines == 1
        assert (
            "response",
            "totalResults",
            "leaf",
        ) in {
            (matched.source, matched.path, matched.kind)
            for matched in excerpt_result.matched_schema_paths
        }

    def test_extract_examples_supports_response_array_size_invariants(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200():::EXIT;"
                "size(return.items[]) one of { 2 };"
                "daikon.inv.unary.scalar.OneOfScalar;"
                "(size(return.items[..]));"
                "pm.expect(items_length).to.eql(2)"
            ),
        )
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        examples = classifier._extract_examples(context, classifier._load_test_cases())

        assert "size(return.items[])=2" in examples

    def test_extract_examples_supports_mixed_scalar_and_response_array_size_invariants(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200():::EXIT;"
                "return.totalResults >= size(return.items[]);"
                "daikon.inv.binary.twoScalar.IntGreaterEqual;"
                "(return.totalResults, size(return.items[..]));"
                "pm.expect(total_results).to.be.at.least(items_length)"
            ),
        )
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        examples = classifier._extract_examples(context, classifier._load_test_cases())

        assert "return.totalResults=2; size(return.items[])=2" in examples

    def test_extract_examples_supports_nested_array_size_invariants(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "size(return.tags[]) >= 1;"
                "daikon.inv.unary.scalar.LowerBound;"
                "(size(return.tags[..]));"
                "pm.expect(tags_length).to.be.at.least(1)"
            ),
        )
        _write_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        examples = classifier._extract_examples(context, classifier._load_test_cases())

        assert "size(return.tags[])=2" in examples
        assert "size(return.tags[])=1" in examples

    def test_extract_examples_supports_root_array_size_invariants(self, tmp_path: Path):
        classifier = InvariantClassifier(
            spec_parser=_build_spec_parser(),
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        _write_invariants_csv(
            tmp_path,
            (
                "get-/projects&get-/projects&200%array():::EXIT;"
                "size(return[]) one of { 2 };"
                "daikon.inv.unary.scalar.OneOfScalar;"
                "(size(return[..]));"
                "pm.expect(projects_length).to.eql(2)"
            ),
        )
        _write_projects_test_cases_json(tmp_path)

        record = InvariantReader(cache_dir=tmp_path).read_invariants()[0]
        context = classifier._normalize_invariant(record)
        examples = classifier._extract_examples(context, classifier._load_test_cases())

        assert examples == ["size(return[])=2"]

    def test_classified_invariant_reader_validates_header(self, tmp_path: Path):
        path = tmp_path / "classified_invariants.csv"
        path.write_text("bad_header\nrow\n", encoding="utf-8")

        with pytest.raises(RuntimeError, match="Unexpected classified invariants CSV header"):
            ClassifiedInvariantReader(cache_dir=tmp_path).read_invariants(path)


class TestDynamicConstraintMinerClassification:
    def test_classify_invariants_requires_model(self, tmp_path: Path):
        spec_parser = _build_spec_parser()
        miner = DynamicConstraintMiner(spec_parser=spec_parser, model=None, cache_dir=tmp_path)
        _write_invariants_csv(
            tmp_path,
            (
                "get-/widgets&get-/widgets&200&items():::EXIT;"
                "return.id >= 1;"
                "daikon.inv.unary.scalar.LowerBound;"
                "(return.id);"
                "pm.expect(return_id).to.be.at.least(1)"
            ),
        )

        with pytest.raises(RuntimeError, match="model is required"):
            miner.classify_invariants()

    def test_mine_and_classify_dynamic_constraints_returns_artifact_paths(self, tmp_path: Path):
        spec_parser = _build_spec_parser()
        miner = DynamicConstraintMiner(
            spec_parser=spec_parser,
            model=StaticClassificationModel(),
            cache_dir=tmp_path,
        )
        expected_paths = {
            "decls_path": tmp_path / "test_cases.decls",
            "dtrace_path": tmp_path / "test_cases.dtrace",
            "invariants_path": tmp_path / "invariants.csv",
            "classified_invariants_path": tmp_path / "classified_invariants.csv",
        }

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(miner, "mine_dynamic_constraints", lambda: {
                "decls_path": expected_paths["decls_path"],
                "dtrace_path": expected_paths["dtrace_path"],
                "invariants_path": expected_paths["invariants_path"],
            })
            mp.setattr(
                miner,
                "classify_invariants",
                lambda persist_debug_artifacts=False: expected_paths["classified_invariants_path"],
            )
            result = miner.mine_and_classify_dynamic_constraints()

        assert result == expected_paths


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_INVARIANT_CLASSIFIER") != "1",
    reason="Set RUN_LIVE_INVARIANT_CLASSIFIER=1 to run the live OpenAI invariant classification test.",
)
def test_live_openai_invariant_classification_on_small_real_fixture(tmp_path: Path):
    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required for live invariant classification.")

    repo_root = Path(__file__).resolve().parents[1]
    source_cache_dir = repo_root / ".cache" / "Bills API_3"
    source_invariants = source_cache_dir / "invariants.csv"
    source_test_cases = source_cache_dir / "test_cases.json"
    if not source_invariants.exists() or not source_test_cases.exists():
        pytest.skip("Bills API_3 invariants/test cases are not available.")

    output_dir = tmp_path / "cache"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "test_cases.json").write_text(
        source_test_cases.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    lines = source_invariants.read_text(encoding="utf-8").splitlines()
    sample_invariants_path = output_dir / "sample_invariants.csv"
    sample_invariants_path.write_text(
        "\n".join(lines[:2]) + "\n",
        encoding="utf-8",
    )

    spec = SpecificationParser(spec_path=str(repo_root / "datasets" / "Bills-api.json"))
    spec.parse_specification()
    model = OpenAIModel(model="gpt-4.1-mini")
    classifier = InvariantClassifier(
        spec_parser=spec,
        model=model,
        cache_dir=output_dir,
    )

    output_path = classifier.classify_invariants(
        input_path=sample_invariants_path,
        output_path=output_dir / "classified_invariants.live.csv",
    )
    records = ClassifiedInvariantReader(cache_dir=output_dir).read_invariants(output_path)

    assert output_path.exists()
    assert len(records) == 1
    assert records[0].verdict in {"true-positive", "false-positive", "inconclusive"}
    assert 0.0 <= records[0].confidence <= 1.0
