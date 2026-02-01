"""Response property constraint extractor.

Extracts constraints from API response schemas and converts them
to operation-level constraints.
"""

import os

from api_testing.constraint.static.extractors.base_extractor import (
    BaseStaticExtractor,
    handle_extraction_error,
)
from api_testing.constraint.static.extractors.models import (
    OperationConstraints,
    SchemaConstraints,
)
from api_testing.dataset import SpecificationParser
from api_testing.models.base_model import APITestingBaseLLMModel
from api_testing.models.specification_model import ItemProperties, OperationProperties
from api_testing.prompts.response_constraints import ResponsePropertyConstraintMiner
from api_testing.utils import flatten_json_schema
from api_testing.utils.graph import is_nested_path_end_with
from common.logger import Logger


class ResponsePropertyExtractor(
    BaseStaticExtractor[tuple[str, ItemProperties], SchemaConstraints]
):
    """Extracts response property constraints from API schemas.

    Processes schemas to extract property-level constraints using LLM validation,
    then converts schema-level constraints to operation-level constraints.

    Example:
        >>> extractor = ResponsePropertyExtractor(
        ...     spec_parser=parser,
        ...     cache_dir="./cache",
        ...     batch_size=10
        ... )
        >>> result = await extractor.extract_all(schemas_list)
        >>> operation_constraints = extractor.convert_to_operation_level(result.successful)
    """

    def __init__(
        self,
        spec_parser: SpecificationParser,
        cache_dir: str,
        model: APITestingBaseLLMModel | None = None,
        batch_size: int = 10,
        logger: Logger | None = None,
    ) -> None:
        """Initialize ResponsePropertyExtractor.

        Args:
            spec_parser: Parser containing parsed API specification
            cache_dir: Directory path for caching extracted constraints
            model: LLM model instance (passed to miner, uses factory default if None)
            batch_size: Number of schemas to process in parallel (default: 10)
            logger: Logger instance (shared from parent)

        Raises:
            ValueError: If spec_parser or cache_dir is None
        """
        if spec_parser is None:
            raise ValueError("spec_parser is required")

        super().__init__(cache_dir=cache_dir, batch_size=batch_size, logger=logger)

        self.spec_parser = spec_parser
        self.operations: dict[str, OperationProperties] = spec_parser.operations
        self.response_constraint_miner = ResponsePropertyConstraintMiner(model=model)

    @property
    def cache_file(self) -> str:
        """Path to response constraints cache file."""
        return os.path.join(self.cache_dir, "_temp_response_constraints.json")

    @handle_extraction_error(return_value=(None, None))
    async def _extract_single(
        self, item: tuple[str, ItemProperties]
    ) -> tuple[str, SchemaConstraints | None]:
        """Extract constraints for a single schema.

        Args:
            item: Tuple of (schema_name, schema)

        Returns:
            Tuple of (schema_name, SchemaConstraints or None if failed)
        """
        schema_name, schema = item

        self.logger.debug(f"Processing schema: {schema_name}")

        # Flatten schema to extract all fields
        flattened_schema = {
            field: values
            for field, values in flatten_json_schema(schema.to_dict()).items()
            if (
                (schema.xrefs is None and values.get("xrefs") is None)
                or (schema.xrefs is not None and values.get("xrefs") == schema.xrefs)
            )
        }

        # Convert to human-readable format
        flatten_texts = [
            f"- {k}: {ItemProperties(**v).to_human_readable()}"
            for k, v in flattened_schema.items()
            if v is not None
        ]

        if not flatten_texts:
            self.logger.debug(f"Schema '{schema_name}' has no attributes, skipping")
            return (schema_name, None)

        # Extract constraints using LLM validation
        result = (
            await self.response_constraint_miner.extract_response_property_constraints(
                schema=schema_name,
                attributes="\n".join(flatten_texts),
                flattened_schema=flattened_schema,
            )
        )

        constraints = SchemaConstraints(
            schema_name=schema_name,
            constraints=result.constraints,
        )

        self.logger.debug(
            f"Extracted constraints for schema: {schema_name}, "
            f"constraint_count={len(constraints.constraints)}"
        )

        return (schema_name, constraints)

    def _parse_cached_items(self, cached_data: list[dict]) -> list[SchemaConstraints]:
        """Parse cached schema constraints.

        Args:
            cached_data: List of cached constraint dictionaries

        Returns:
            List of SchemaConstraints instances
        """
        return [SchemaConstraints(**item) for item in cached_data]

    def convert_to_operation_level(
        self, schema_constraints: list[SchemaConstraints]
    ) -> dict[str, OperationConstraints]:
        """Convert schema-level constraints to operation-level constraints.

        Maps each schema's constraints to operations that use them in responses,
        preserving xrefs matching for accurate attribute mapping.

        Args:
            schema_constraints: List of extracted schema constraints

        Returns:
            Dictionary mapping operation UUIDs to OperationConstraints

        Example:
            >>> schema_constraints = [
            ...     SchemaConstraints(schema_name="Holiday", constraints={"date": "ISO date"}),
            ...     SchemaConstraints(schema_name="Province", constraints={"id": "Province ID"})
            ... ]
            >>> operation_constraints = extractor.convert_to_operation_level(schema_constraints)
            >>> print(operation_constraints["get-/api/v1/holidays"].constraints)
            {"holidays.date": "ISO date"}
        """
        self.logger.info(
            f"Converting {len(schema_constraints)} schema constraints to operation-level"
        )

        # Build lookup dictionary for fast access
        schema_lookup: dict[str, dict[str, str]] = {
            sc.schema_name: sc.constraints for sc in schema_constraints
        }

        operation_constraints: dict[str, OperationConstraints] = {}

        for operation in self.operations.values():
            operation_uuid = operation.uuid
            operation_constraints[operation_uuid] = OperationConstraints(
                operation_uuid=operation_uuid,
                constraints={},
            )

            # Get successful responses for this operation
            successful_responses = operation.successful_responses
            if not successful_responses:
                self.logger.debug(
                    f"Operation '{operation_uuid}' has no successful responses, skipping"
                )
                continue

            # Flatten response schema for attribute matching
            flatten_responses = flatten_json_schema(successful_responses.to_dict())

            # Map schema constraints to operation response attributes
            for schema_name, rules in schema_lookup.items():
                for attribute_name, constraint_desc in rules.items():
                    # Find matching attributes in operation's response
                    # Match by: 1) nested path ending, 2) xrefs match
                    matching_attributes = {
                        response_attr: constraint_desc
                        for response_attr, props in flatten_responses.items()
                        if is_nested_path_end_with(response_attr, attribute_name)
                        and props.get("xrefs") == schema_name
                    }

                    # Add matched attributes to operation constraints
                    operation_constraints[operation_uuid].constraints.update(
                        matching_attributes
                    )

            self.logger.debug(
                f"Converted schema constraints for operation '{operation_uuid}': "
                f"{len(operation_constraints[operation_uuid].constraints)} attributes"
            )

        self.logger.info(
            f"Conversion completed: {len(operation_constraints)} operations processed"
        )

        return operation_constraints


__all__ = ["ResponsePropertyExtractor"]
