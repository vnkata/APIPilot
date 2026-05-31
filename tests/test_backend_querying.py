from __future__ import annotations

import pytest

from api_testing.backend.domain.errors import InvalidArtifactRequest


def test_query_engine_filters_searches_sorts_groups_before_pagination():
    from api_testing.backend.application.querying import (
        QueryOptions,
        QuerySpec,
        SortOrder,
        query_items,
    )
    from api_testing.backend.domain.models import ConstraintEntryDetail

    records = [
        ConstraintEntryDetail(
            operation_id="post-/items",
            property_path="return.item.id",
            expression="return.item.id >= 1",
            section="response_properties",
        ),
        ConstraintEntryDetail(
            operation_id="get-/items",
            property_path="input.limit",
            expression="input.limit >= 1",
            section="request_response",
        ),
        ConstraintEntryDetail(
            operation_id="get-/items",
            property_path="return.items[].name",
            expression="required",
            section="response_properties",
        ),
    ]
    spec = QuerySpec[ConstraintEntryDetail](
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

    page = query_items(
        records,
        spec=spec,
        options=QueryOptions(
            q="item",
            limit=1,
            offset=0,
            sort_by="property_path",
            sort_order=SortOrder.DESC,
            group_by="operation_id",
        ),
    )

    assert page.pagination.total == 3
    assert [group.key for group in page.groups] == ["get-/items", "post-/items"]
    assert [group.count for group in page.groups] == [2, 1]
    assert [item.property_path for item in page.items] == ["return.items[].name"]


def test_query_engine_rejects_invalid_sort_and_group_fields():
    from api_testing.backend.application.querying import (
        QueryOptions,
        QuerySpec,
        query_items,
    )
    from api_testing.backend.domain.models import ConstraintEntryDetail

    records = [
        ConstraintEntryDetail(
            operation_id="get-/items",
            property_path="input.limit",
            expression="input.limit >= 1",
            section="request_response",
        )
    ]
    spec = QuerySpec[ConstraintEntryDetail](
        sort_fields={"operation_id": lambda item: item.operation_id},
        group_fields={"operation_id": lambda item: item.operation_id},
        search_fields=[lambda item: item.operation_id],
        default_sort=("operation_id",),
    )

    with pytest.raises(InvalidArtifactRequest, match="sort_by"):
        query_items(records, spec=spec, options=QueryOptions(sort_by="missing"))

    with pytest.raises(InvalidArtifactRequest, match="group_by"):
        query_items(records, spec=spec, options=QueryOptions(group_by="missing"))
