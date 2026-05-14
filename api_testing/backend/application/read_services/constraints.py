"""Static and dynamic constraint read services."""

from __future__ import annotations

from pydantic import JsonValue

from api_testing.backend.application.ports import ArtifactRepositoryProtocol
from api_testing.backend.application.querying import (
    ConstraintEntryQuery,
    InvariantQuery,
    QuerySpec,
    query_items,
)
from api_testing.backend.application.read_services.utils import (
    constraint_entries,
    invariant_groups,
    invariant_record,
    operation_id_from_pptname,
)
from api_testing.backend.domain.errors import ArtifactNotFound
from api_testing.backend.domain.models import (
    ConstraintEntryDetail,
    ConstraintSection,
    DynamicConstraints,
    GroupedPage,
    InvariantDetail,
    InvariantRecord,
    StaticConstraints,
)


class StaticConstraintQueryService:
    """Builds aggregate and detailed static constraint read models."""

    _entry_spec = QuerySpec[ConstraintEntryDetail](
        sort_fields={
            "operation_id": lambda item: item.operation_id,
            "property_path": lambda item: item.property_path,
            "section": lambda item: item.section,
        },
        group_fields={
            "operation_id": lambda item: item.operation_id,
            "section": lambda item: item.section,
        },
        search_fields=[
            lambda item: item.operation_id,
            lambda item: item.property_path,
            lambda item: item.expression,
            lambda item: item.section,
        ],
        default_sort=("operation_id", "property_path", "section"),
    )

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def get_static_constraints(self, run_name: str) -> StaticConstraints:
        raw = self.repository.read_json_artifact(run_name, "static_constraint_miner")
        payload = raw if isinstance(raw, dict) else {}
        sections = [
            self._constraint_section("common", payload.get("common", {})),
            self._constraint_section(
                "request_response", payload.get("request_response", {})
            ),
            self._constraint_section(
                "response_properties", payload.get("response_properties", {})
            ),
        ]
        return StaticConstraints(
            run_name=run_name,
            sections=sections,
            constraint_count=sum(len(section.constraints) for section in sections),
        )

    def list_static_constraint_entries(
        self,
        run_name: str,
        query: ConstraintEntryQuery,
    ) -> GroupedPage[ConstraintEntryDetail]:
        records = [
            detail
            for detail in self._static_constraint_details(run_name)
            if (query.operation_id is None or detail.operation_id == query.operation_id)
            and (query.section is None or detail.section == query.section)
        ]
        return query_items(records, spec=self._entry_spec, options=query.options)

    def _constraint_section(self, name: str, value: JsonValue) -> ConstraintSection:
        return ConstraintSection(name=name, constraints=constraint_entries(value))

    def _static_constraint_details(self, run_name: str) -> list[ConstraintEntryDetail]:
        return [
            ConstraintEntryDetail(
                operation_id=entry.operation_id,
                property_path=entry.property_path,
                expression=entry.expression,
                section=section.name,
            )
            for section in self.get_static_constraints(run_name).sections
            for entry in section.constraints
        ]


class DynamicConstraintQueryService:
    """Builds aggregate and detailed dynamic constraint and invariant read models."""

    _entry_spec = StaticConstraintQueryService._entry_spec
    _invariant_spec = QuerySpec[InvariantDetail](
        sort_fields={
            "operation_id": lambda item: item.operation_id,
            "invariant_type": lambda item: item.invariant_type,
            "pptname": lambda item: item.pptname,
            "invariant": lambda item: item.invariant,
        },
        group_fields={
            "operation_id": lambda item: item.operation_id,
            "invariant_type": lambda item: item.invariant_type,
        },
        search_fields=[
            lambda item: item.operation_id,
            lambda item: item.pptname,
            lambda item: item.invariant,
            lambda item: item.invariant_type,
            lambda item: item.variables,
            lambda item: item.postman_assertion,
        ],
        default_sort=("operation_id", "invariant_type", "pptname", "invariant"),
    )

    def __init__(self, repository: ArtifactRepositoryProtocol) -> None:
        self.repository = repository

    def get_dynamic_constraints(self, run_name: str) -> DynamicConstraints:
        raw = self.repository.read_json_artifact(run_name, "dynamic_constraint_miner")
        payload = raw if isinstance(raw, dict) else {}
        constraints = constraint_entries(payload.get("constraints", {}))
        groups = invariant_groups(payload.get("group_invariants", {}))
        invariants = self._invariant_records(run_name)
        return DynamicConstraints(
            run_name=run_name,
            constraints=constraints,
            groups=groups,
            invariants=invariants,
            constraint_count=len(constraints),
            invariant_count=len(invariants),
        )

    def list_dynamic_constraint_entries(
        self,
        run_name: str,
        query: ConstraintEntryQuery,
    ) -> GroupedPage[ConstraintEntryDetail]:
        records = [
            detail
            for detail in self._dynamic_constraint_details(run_name)
            if (query.operation_id is None or detail.operation_id == query.operation_id)
            and (query.section is None or detail.section == query.section)
        ]
        return query_items(records, spec=self._entry_spec, options=query.options)

    def list_invariants(
        self,
        run_name: str,
        query: InvariantQuery,
    ) -> GroupedPage[InvariantDetail]:
        records = [
            detail
            for detail in self._invariant_details(run_name)
            if (query.operation_id is None or detail.operation_id == query.operation_id)
            and (
                query.invariant_type is None
                or detail.invariant_type == query.invariant_type
            )
        ]
        return query_items(records, spec=self._invariant_spec, options=query.options)

    def _dynamic_constraint_details(self, run_name: str) -> list[ConstraintEntryDetail]:
        return [
            ConstraintEntryDetail(
                operation_id=entry.operation_id,
                property_path=entry.property_path,
                expression=entry.expression,
                section=None,
            )
            for entry in self.get_dynamic_constraints(run_name).constraints
        ]

    def _invariant_details(self, run_name: str) -> list[InvariantDetail]:
        return [
            InvariantDetail(
                operation_id=operation_id_from_pptname(record.pptname),
                pptname=record.pptname,
                invariant=record.invariant,
                invariant_type=record.invariant_type,
                variables=record.variables,
                postman_assertion=record.postman_assertion,
            )
            for record in self._invariant_records(run_name)
        ]

    def _invariant_records(self, run_name: str) -> list[InvariantRecord]:
        try:
            rows = self.repository.read_csv_rows(run_name, "invariants_csv")
        except ArtifactNotFound:
            return []
        return [invariant_record(row) for row in rows]
