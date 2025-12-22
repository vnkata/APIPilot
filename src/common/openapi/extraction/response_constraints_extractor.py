"""
Response property constraints extractor

Extracts constraints from response schemas in OpenAPI specifications.
Handles nested properties and array items using jsonschema keywords.
"""

from typing import Any, Optional

from common.logger.utils.helpers import get_logger
from common.openapi.extraction.models import PropertyConstraint
from common.openapi.models import SpecDict

logger = get_logger(__name__)


class ResponseConstraintsExtractor:
    """
    Extract property constraints from OpenAPI response schemas

    Features:
    - Extracts constraints using jsonschema keywords
    - Handles nested properties (e.g., user.profile.email)
    - Handles array item schemas (e.g., items[].id)
    - Logs warnings for problematic schemas
    """

    # Standard jsonschema keywords that represent constraints
    CONSTRAINT_KEYWORDS = {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minLength",
        "maxLength",
        "pattern",
        "enum",
        "default",
    }

    def __init__(self, spec_dict: SpecDict, spec_name: str) -> None:
        """
        Initialize extractor

        Args:
            spec_dict: Resolved OpenAPI spec as dict
            spec_name: Human-readable name for spec (for CSV output)
        """
        self.spec_dict = spec_dict
        self.spec_name = spec_name
        self.components = spec_dict.get("components", {})
        self.schemas = self.components.get("schemas", {})

    def extract_all_constraints(self) -> list[PropertyConstraint]:
        """
        Extract all property constraints from response schemas

        Returns:
            List of PropertyConstraint objects for all response schemas
        """
        constraints = []

        # Iterate through all schemas in components
        for schema_name, schema_def in self.schemas.items():
            if not isinstance(schema_def, dict):
                logger.warning(
                    f"Skipping non-dict schema: {schema_name} (type: {type(schema_def)})"
                )
                continue

            try:
                schema_constraints = self._extract_schema_constraints(
                    schema_name, schema_def
                )
                constraints.extend(schema_constraints)
            except Exception as e:
                logger.warning(
                    f"Error extracting constraints from {schema_name}: {e}",
                    extra={"error_type": type(e).__name__},
                )

        logger.info(
            f"Extracted {len(constraints)} property constraints from {self.spec_name}"
        )
        return constraints

    def _extract_schema_constraints(
        self, component_name: str, schema: dict[str, Any], parent_path: str = ""
    ) -> list[PropertyConstraint]:
        """
        Extract constraints from a single schema recursively

        Args:
            component_name: Name of the component/schema
            schema: Schema definition dict
            parent_path: Parent path for nested properties (for dot notation)

        Returns:
            List of PropertyConstraint objects
        """
        constraints = []

        # Handle allOf, oneOf, anyOf
        if "allOf" in schema:
            for sub_schema in schema["allOf"]:
                if isinstance(sub_schema, dict):
                    constraints.extend(
                        self._extract_schema_constraints(
                            component_name, sub_schema, parent_path
                        )
                    )

        if "oneOf" in schema or "anyOf" in schema:
            # For oneOf/anyOf, extract from first variant (limitation)
            variants = schema.get("oneOf") or schema.get("anyOf", [])
            if variants and isinstance(variants[0], dict):
                constraints.extend(
                    self._extract_schema_constraints(
                        component_name, variants[0], parent_path
                    )
                )

        # Extract properties
        if schema.get("type") == "object" and "properties" in schema:
            required_fields = schema.get("required", [])
            props = schema["properties"]

            for prop_name, prop_schema in props.items():
                if not isinstance(prop_schema, dict):
                    logger.warning(
                        f"Skipping non-dict property: {component_name}.{prop_name}"
                    )
                    continue

                # Build full property path (e.g., "user.profile.email")
                full_path = (
                    f"{parent_path}.{prop_name}"
                    if parent_path
                    else prop_name
                )

                # Handle $ref
                if "$ref" in prop_schema:
                    ref_name = prop_schema["$ref"].split("/")[-1]
                    if ref_name in self.schemas:
                        # Recursively extract from referenced schema
                        constraints.extend(
                            self._extract_schema_constraints(
                                ref_name,
                                self.schemas[ref_name],
                                full_path,
                            )
                        )
                    continue

                # Handle arrays
                if prop_schema.get("type") == "array":
                    item_schema = prop_schema.get("items", {})
                    if isinstance(item_schema, dict):
                        if "$ref" in item_schema:
                            # Reference to component
                            ref_name = item_schema["$ref"].split("/")[-1]
                            if ref_name in self.schemas:
                                constraints.extend(
                                    self._extract_schema_constraints(
                                        ref_name,
                                        self.schemas[ref_name],
                                        f"{full_path}[]",
                                    )
                                )
                        else:
                            # Inline schema
                            if item_schema.get("type") == "object":
                                constraints.extend(
                                    self._extract_schema_constraints(
                                        component_name,
                                        item_schema,
                                        f"{full_path}[]",
                                    )
                                )
                            else:
                                # Scalar array items
                                constraint = self._extract_property_constraint(
                                    component_name, f"{full_path}[]", item_schema
                                )
                                if constraint:
                                    constraints.append(constraint)
                    continue

                # Handle nested objects
                if prop_schema.get("type") == "object" and "properties" in prop_schema:
                    constraints.extend(
                        self._extract_schema_constraints(
                            component_name, prop_schema, full_path
                        )
                    )
                    continue

                # Handle scalar properties
                is_required = prop_name in required_fields
                constraint = self._extract_property_constraint(
                    component_name, full_path, prop_schema, is_required
                )
                if constraint:
                    constraints.append(constraint)

        # Handle array type at root
        if schema.get("type") == "array" and "items" in schema:
            item_schema = schema["items"]
            if isinstance(item_schema, dict):
                if "$ref" in item_schema:
                    ref_name = item_schema["$ref"].split("/")[-1]
                    if ref_name in self.schemas:
                        constraints.extend(
                            self._extract_schema_constraints(
                                ref_name,
                                self.schemas[ref_name],
                                "[]",
                            )
                        )

        return constraints

    def _extract_property_constraint(
        self,
        component_name: str,
        property_path: str,
        prop_schema: dict[str, Any],
        is_required: bool = False,
    ) -> Optional[PropertyConstraint]:
        """
        Extract constraint from a single property schema

        Args:
            component_name: Component name
            property_path: Full property path with dot notation
            prop_schema: Property schema dict
            is_required: Whether property is required

        Returns:
            PropertyConstraint or None if invalid
        """
        try:
            prop_name = property_path.split(".")[-1]  # Get last part after dots
            type_ = prop_schema.get("type", "unknown")
            format_ = prop_schema.get("format")
            description = prop_schema.get("description")
            default = prop_schema.get("default")

            # Extract numeric constraints
            minimum = prop_schema.get("minimum")
            maximum = prop_schema.get("maximum")
            exclusive_min = prop_schema.get("exclusiveMinimum")
            exclusive_max = prop_schema.get("exclusiveMaximum")

            # Extract string constraints
            min_length = prop_schema.get("minLength")
            max_length = prop_schema.get("maxLength")
            pattern = prop_schema.get("pattern")
            enum_values = prop_schema.get("enum")

            validation_notes = None
            if type_ not in ("string", "integer", "number", "boolean", "array"):
                validation_notes = f"Non-standard type: {type_}"

            return PropertyConstraint(
                spec_name=self.spec_name,
                component_name=component_name,
                property_name=prop_name,
                property_path=property_path,
                type_=type_,
                format_=format_,
                minimum=minimum,
                maximum=maximum,
                exclusive_minimum=exclusive_min,
                exclusive_maximum=exclusive_max,
                min_length=min_length,
                max_length=max_length,
                pattern=pattern,
                enum_values=enum_values,
                description=description,
                is_required=is_required,
                default_value=default,
                validation_notes=validation_notes,
            )
        except Exception as e:
            logger.warning(
                f"Failed to extract constraint for {component_name}.{property_path}: {e}"
            )
            return None


__all__ = ["ResponseConstraintsExtractor"]
