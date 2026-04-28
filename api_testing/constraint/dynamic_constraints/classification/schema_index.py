from __future__ import annotations

from typing import Any

from api_testing.constraint.dynamic_constraints.classification.models import (
    SchemaEntry,
    SchemaIndex,
)
from api_testing.models.specification_model import ItemProperties
from api_testing.utils import flatten_json_schema, to_dict_helper


class SchemaIndexBuilder:
    """Build array/object-aware schema indexes for compact spec excerpts."""

    def __init__(self, *, max_summary_fields: int = 5, max_required_fields: int = 3) -> None:
        self.max_summary_fields = max_summary_fields
        self.max_required_fields = max_required_fields

    def build_from_item(self, schema: ItemProperties | dict[str, Any] | None) -> SchemaIndex:
        """Index array containers, object containers, and leaf fields from one schema item."""
        if schema is None:
            return SchemaIndex()

        schema_dict = schema if isinstance(schema, dict) else to_dict_helper(schema)
        if not schema_dict:
            return SchemaIndex()

        arrays: dict[str, SchemaEntry] = {}
        objects: dict[str, SchemaEntry] = {}
        self._collect_array_entries(schema_dict, parent_key="", target=arrays)
        self._collect_object_entries(schema_dict, parent_key="", target=objects)
        leaves = {
            path: SchemaEntry(
                path=path,
                tokens=self.normalize_match_tokens(path),
                kind="leaf",
                metadata=metadata,
            )
            for path, metadata in flatten_json_schema(schema_dict).items()
        }
        return SchemaIndex(arrays=arrays, objects=objects, leaves=leaves)

    def _collect_array_entries(
        self,
        schema: dict[str, Any],
        *,
        parent_key: str,
        target: dict[str, SchemaEntry],
    ) -> None:
        if not schema:
            return

        for composition_key in ("allOf", "anyOf", "oneOf"):
            if schema.get(composition_key):
                for child in schema[composition_key]:
                    self._collect_array_entries(child, parent_key=parent_key, target=target)
                return

        if schema.get("properties"):
            for key, value in schema["properties"].items():
                if not value:
                    continue
                next_key = f"{parent_key}.{key}" if parent_key else key
                self._collect_array_entries(value, parent_key=next_key, target=target)
            return

        if schema.get("type") != "array":
            return

        array_path = f"{parent_key}[]" if parent_key else "[]"
        target[array_path] = SchemaEntry(
            path=array_path,
            tokens=self.normalize_match_tokens(array_path),
            kind="array_container",
            metadata=self._build_array_metadata(schema),
        )

        items = schema.get("items") or {}
        if isinstance(items, dict) and items:
            self._collect_array_entries(items, parent_key=array_path, target=target)

    def _collect_object_entries(
        self,
        schema: dict[str, Any],
        *,
        parent_key: str,
        target: dict[str, SchemaEntry],
    ) -> None:
        if not schema:
            return

        for composition_key in ("allOf", "anyOf", "oneOf"):
            if schema.get(composition_key):
                for child in schema[composition_key]:
                    self._collect_object_entries(child, parent_key=parent_key, target=target)
                return

        if schema.get("type") == "array":
            items = schema.get("items") or {}
            if isinstance(items, dict) and items:
                array_path = f"{parent_key}[]" if parent_key else "[]"
                self._collect_object_entries(items, parent_key=array_path, target=target)
            return

        properties = schema.get("properties") or {}
        if not properties:
            return

        if parent_key:
            target[parent_key] = SchemaEntry(
                path=parent_key,
                tokens=self.normalize_match_tokens(parent_key),
                kind="object_container",
                metadata=self._build_object_metadata(schema),
            )

        for key, value in properties.items():
            if not value:
                continue
            next_key = f"{parent_key}.{key}" if parent_key else key
            self._collect_object_entries(value, parent_key=next_key, target=target)

    def _build_array_metadata(self, schema: dict[str, Any]) -> dict[str, Any]:
        items = schema.get("items") or {}
        metadata: dict[str, Any] = {
            "type": "array",
            "description": schema.get("description"),
        }

        min_items = schema.get("min_items", schema.get("minItems"))
        if min_items is not None:
            metadata["minItems"] = min_items

        max_items = schema.get("max_items", schema.get("maxItems"))
        if max_items is not None:
            metadata["maxItems"] = max_items

        unique_items = schema.get("unique_items", schema.get("uniqueItems"))
        if unique_items is not None:
            metadata["uniqueItems"] = unique_items

        item_type = self._infer_schema_type(items)
        if item_type:
            metadata["itemsType"] = item_type

        item_description = items.get("description") if isinstance(items, dict) else None
        if item_description:
            metadata["itemsDescription"] = item_description

        item_fields = self._collect_direct_item_fields(items)
        if item_fields:
            metadata["itemFields"] = item_fields[: self.max_summary_fields]

        item_enum = items.get("enum") if isinstance(items, dict) else None
        if item_enum:
            metadata["itemsEnum"] = item_enum

        item_pattern = items.get("pattern") if isinstance(items, dict) else None
        if item_pattern:
            metadata["itemsPattern"] = item_pattern

        return metadata

    def _build_object_metadata(self, schema: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "type": "object",
            "description": schema.get("description"),
        }

        child_fields = self._collect_direct_item_fields(schema)
        if child_fields:
            metadata["childFields"] = child_fields[: self.max_summary_fields]

        required_fields = schema.get("required") or []
        if required_fields:
            metadata["requiredFields"] = required_fields[: self.max_required_fields]

        return metadata

    def _collect_direct_item_fields(self, schema: dict[str, Any]) -> list[str]:
        if not schema:
            return []

        for composition_key in ("allOf", "anyOf", "oneOf"):
            if schema.get(composition_key):
                names: list[str] = []
                for child in schema[composition_key]:
                    names.extend(self._collect_direct_item_fields(child))
                return sorted(dict.fromkeys(names))

        if not schema.get("properties"):
            return []

        names: list[str] = []
        for key, value in schema["properties"].items():
            if not value:
                continue
            suffix = "[]" if value.get("type") == "array" else ""
            names.append(f"{key}{suffix}")
        return sorted(names)

    @staticmethod
    def _infer_schema_type(schema: dict[str, Any]) -> str | None:
        if not schema:
            return None
        if schema.get("type"):
            return schema["type"]
        if schema.get("properties"):
            return "object"
        if schema.get("items"):
            return "array"
        for composition_key in ("allOf", "anyOf", "oneOf"):
            if schema.get(composition_key):
                for child in schema[composition_key]:
                    child_type = SchemaIndexBuilder._infer_schema_type(child)
                    if child_type:
                        return child_type
        return None

    @staticmethod
    def normalize_match_tokens(path: str) -> tuple[str, ...]:
        tokens = []
        for raw_segment in path.split("."):
            cleaned = raw_segment.replace("[..]", "[]").replace("[]", "").replace("()", "")
            cleaned = cleaned.replace("%array", "").strip()
            if cleaned:
                tokens.append(cleaned.lower())
        return tuple(tokens)
