"""
Static constraint mining module.

Extracts constraints from API specifications without executing API calls.
Mines constraints from response schemas and request-response mappings.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple, TypedDict
from api_testing.dataset import SpecificationParser
from api_testing.models.base_model import (
    APITestingBaseEmbeddingModel,
    APITestingBaseLLMModel,
)
from api_testing.models.specification_model import ItemProperties, OperationProperties
from api_testing.prompts.response_constraints import ResponsePropertyConstraintMiner
from api_testing.utils import flatten_json_schema
from api_testing.utils.graph import is_nested_path_end_with
from common.logger import get_logger, LogLevel


# Type aliases for constraint data structures
ConstraintDict = Dict[str, str]  # Maps attribute path to constraint description
OperationConstraints = Dict[str, ConstraintDict]  # Maps operation UUID to constraints
SchemaConstraints = Dict[str, ConstraintDict]  # Maps schema name to constraints


class ResponsePropertiesConstraintsOutput(TypedDict):
    """Output format for response properties constraints."""

    response_properties_constraints: OperationConstraints


class StaticConstraintMiner:
    """Mines constraints from API specifications statically.

    Extracts constraints from response schemas and identifies relationships
    between request parameters and response properties without executing
    API calls.

    Attributes:
        spec_parser: Parser for API specification
        model: LLM model for constraint extraction (deprecated, kept for compatibility)
        embedding_model: Embedding model (optional, for future use)
        cache_file: Path to cache file for storing extracted constraints
        logger: Logger instance
        operations: Dictionary of operation UUIDs to OperationProperties
        schemas: Dictionary of schema names to ItemProperties
        response_constraint: ResponsePropertyConstraintMiner extractor instance

    Example:
        >>> miner = StaticConstraintMiner(
        ...     spec_parser=parser,
        ...     cache_dir="./cache"
        ... )
        >>> await miner.response_properties_constraints()
    """

    def __init__(
        self,
        spec_parser: Optional[SpecificationParser] = None,
        model: Optional[APITestingBaseLLMModel] = None,
        embedding_model: Optional[APITestingBaseEmbeddingModel] = None,
        cache_dir: Optional[str] = None,
        batch_size: int = 10,
    ) -> None:
        """Initialize StaticConstraintMiner.

        Args:
            spec_parser: Parser containing parsed API specification
            model: Deprecated LLM model parameter (kept for backward compatibility)
            embedding_model: Optional embedding model for semantic analysis
            cache_dir: Directory path for caching extracted constraints
            batch_size: Number of schemas to process in parallel (default: 10)
        """
        if spec_parser is None:
            raise ValueError("spec_parser is required")
        if cache_dir is None:
            raise ValueError("cache_dir is required")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        self.spec_parser: SpecificationParser = spec_parser
        self.model: Optional[APITestingBaseLLMModel] = model
        self.embedding_model: Optional[APITestingBaseEmbeddingModel] = embedding_model
        self.batch_size: int = batch_size
        self.cache_file = os.path.join(cache_dir, "static_constraint_miner.json")
        self.logger = get_logger(
            "static_constraint_miner",
            level=LogLevel.DEBUG,
            console_level=LogLevel.DEBUG,
        )

        self.operations: Dict[str, OperationProperties] = self.spec_parser.operations
        self.schemas: Dict[str, ItemProperties] = {
            k: v for opt in self.operations.values() for k, v in opt.schemas.items()
        }
        self.response_constraint = ResponsePropertyConstraintMiner()

    async def extract_request_response_constraints(self) -> None:
        """Implement mining constraints between request and response.

        This method is a placeholder for future implementation of
        request-response constraint mining.

        Raises:
            NotImplementedError: This method is not yet implemented
        """
        raise NotImplementedError("request_response_constraints not yet implemented")

    async def _extract_single_schema_constraints(
        self, schema_name: str, schema: ItemProperties
    ) -> Tuple[str, Optional[ConstraintDict]]:
        """Extract constraints for a single schema.

        Args:
            schema_name: Name of the schema to extract constraints from
            schema: ItemProperties object representing the schema

        Returns:
            Tuple of (schema_name, constraints_dict) where constraints_dict is None
            if extraction failed or schema has no attributes
        """
        from common.llm.exceptions import LLMError

        try:
            self.logger.debug(f"Processing schema: {schema_name}")

            # Flatten schema to extract all fields
            flattened_schema = {
                field: values
                for field, values in flatten_json_schema(schema.to_dict()).items()
                if (
                    (schema.xrefs is None and values.get("xrefs") is None)
                    or (
                        schema.xrefs is not None and values.get("xrefs") == schema.xrefs
                    )
                )
            }

            # Convert to human-readable format
            flatten_texts = [
                f"- {k}: {ItemProperties(**v).to_human_readable()}"
                for k, v in flattened_schema.items()
                if v is not None
            ]

            if not flatten_texts:
                self.logger.debug(f"Skipping schema with no attributes: {schema_name}")
                return (schema_name, None)

            # Extract constraints using LLM (validation-based approach)
            # Pass flattened_schema for potential future use (e.g., using ItemProperties.to_human_readable())
            result = (
                await self.response_constraint.extract_response_property_constraints(
                    schema=schema_name,
                    attributes="\n".join(flatten_texts),
                    flattened_schema=flattened_schema,
                )
            )
            constraints_dict = result.constraints

            self.logger.debug(
                f"Extracted constraints for schema: {schema_name}, constraint_count={len(constraints_dict)}"
            )
            return (schema_name, constraints_dict)

        except LLMError as e:
            self.logger.error(
                f"Failed to extract constraints for schema: {schema_name}, error={str(e)}"
            )
            # Return None to indicate failure, but don't raise to allow batch to continue
            return (schema_name, None)
        except Exception as e:
            self.logger.error(
                f"Unexpected error extracting constraints for schema: {schema_name}, error={str(e)}, error_type={type(e).__name__}"
            )
            return (schema_name, None)

    async def _extract_schema_constraints_batch(
        self, schemas_batch: List[Tuple[str, ItemProperties]]
    ) -> SchemaConstraints:
        """Extract constraints for a batch of schemas in parallel.

        Args:
            schemas_batch: List of (schema_name, schema) tuples to process

        Returns:
            Dictionary mapping schema names to constraint dictionaries
        """
        if not schemas_batch:
            return {}

        self.logger.debug(
            f"Processing batch of {len(schemas_batch)} schemas: {[name for name, _ in schemas_batch]}"
        )

        # Create tasks for parallel execution
        tasks = [
            self._extract_single_schema_constraints(schema_name, schema)
            for schema_name, schema in schemas_batch
        ]

        # Execute all tasks in parallel with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        batch_constraints: SchemaConstraints = {}
        for i, result in enumerate(results):
            schema_name, schema = schemas_batch[i]

            if isinstance(result, Exception):
                self.logger.error(
                    f"Exception in batch processing for schema: {schema_name}, "
                    f"error={str(result)}, error_type={type(result).__name__}"
                )
                # Skip this schema, continue with others
                continue

            schema_name_result, constraints_dict = result
            if constraints_dict is not None:
                batch_constraints[schema_name_result] = constraints_dict

        self.logger.debug(
            f"Batch completed: {len(batch_constraints)}/{len(schemas_batch)} schemas processed successfully"
        )

        return batch_constraints

    async def extract_response_property_constraints(
        self,
    ) -> ResponsePropertiesConstraintsOutput:
        """Extract constraints among response properties.

        Analyzes response schemas to identify constraints, rules, and
        limitations that can be programmatically validated. Maps schema-level
        constraints to operation-level constraints.

        Returns:
            Dictionary with "response_properties_constraints" key containing
            operation UUIDs mapped to constraint dictionaries

        Raises:
            LLMError: If constraint extraction fails
            IOError: If cache file cannot be written
        """

        self.logger.info(
            f"Processing {len(self.schemas)} schemas for response properties constraints"
        )

        # Load from cache if exists
        if os.path.exists(self.cache_file):
            self.logger.info(f"Loading constraints from cache: {self.cache_file}")
            try:
                with open(self.cache_file, "r", encoding="utf-8") as file:
                    cached_data = json.load(file)
                    return cached_data  # type: ignore
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    "Failed to load cache, will regenerate",
                    error=str(e),
                    cache_file=self.cache_file,
                )

        # Extract constraints for all schemas using batch processing
        schema_constraints: SchemaConstraints = {}
        schemas_list = list(self.schemas.items())
        total_schemas = len(schemas_list)

        self.logger.info(
            f"Processing {total_schemas} schemas in batches of {self.batch_size}"
        )

        # Process schemas in batches
        for batch_start in range(0, total_schemas, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_schemas)
            batch = schemas_list[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (total_schemas + self.batch_size - 1) // self.batch_size

            self.logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({batch_start + 1}-{batch_end} of {total_schemas} schemas)"
            )

            # Extract constraints for this batch in parallel
            batch_results = await self._extract_schema_constraints_batch(batch)
            schema_constraints.update(batch_results)

            self.logger.info(
                f"Batch {batch_num}/{total_batches} completed: "
                f"{len(batch_results)} schemas processed successfully"
            )

        self.logger.info(
            f"Completed processing all schemas: {len(schema_constraints)}/{total_schemas} "
            "schemas extracted successfully"
        )

        # Convert from schema-level constraints to operation-level constraints
        final_constraints: OperationConstraints = {}
        for opt in self.operations.values():
            final_constraints[opt.uuid] = {}
            successful_responses = opt.successful_responses
            if not successful_responses:
                continue

            flatten_responses = flatten_json_schema(successful_responses.to_dict())
            for schema_name, rules in schema_constraints.items():
                if rules is None:
                    continue
                attribute_rules = rules.keys()
                for attribute_name in attribute_rules:
                    attributes = {
                        att: rules.get(attribute_name, "")
                        for att, props in flatten_responses.items()
                        if is_nested_path_end_with(att, attribute_name)
                        and props.get("xrefs", None) == schema_name
                    }
                    final_constraints[opt.uuid].update(attributes)

        # Save to cache
        output: ResponsePropertiesConstraintsOutput = {
            "response_properties_constraints": final_constraints
        }
        try:
            with open(self.cache_file, "w", encoding="utf-8") as file:
                json.dump(output, file, ensure_ascii=False, indent=4)
            self.logger.info(
                f"Saved constraints to cache: cache_file={self.cache_file}, operations_count={len(final_constraints)}"
            )
        except IOError as e:
            self.logger.error(
                f"Failed to write cache file: cache_file={self.cache_file}, error={str(e)}"
            )
            raise

        return output

    async def extract_and_save_constraint_ir(self) -> None:
        """Generate Constraint IR and save to cache (non-breaking extension).

        This method builds a Constraint IR document from operations and schemas,
        then saves it to cache alongside the existing static_constraint_miner.json.

        The Constraint IR is used by the validation engine for runtime constraint validation.
        """
        from api_testing.constraint.constraint_ir_builder import ConstraintIRBuilder

        self.logger.info("Building Constraint IR from operations")

        # Build Constraint IR using builder
        builder = ConstraintIRBuilder(
            operations=self.operations,
            schemas=self.schemas,
            static_constraints_path=self.cache_file,  # Pass path to static_miner
            llm_client=self.model,
            embedding_model=self.embedding_model,
            cache_dir=os.path.dirname(self.cache_file),
            logger_instance=self.logger,
        )

        ir = await builder.build()

        # Save to cache (separate file from static_constraint_miner.json)
        ir_file = os.path.join(os.path.dirname(self.cache_file), "constraint_ir.json")

        try:
            with open(ir_file, "w", encoding="utf-8") as f:
                json.dump(ir.model_dump(), f, indent=2, ensure_ascii=False)

            self.logger.info(
                "Constraint IR saved successfully",
                file=ir_file,
                operations_count=len(ir.operation_constraints),
                total_checks=sum(
                    len(oc.checks) for oc in ir.operation_constraints.values()
                ),
            )
        except IOError as e:
            self.logger.error(
                f"Failed to write constraint IR file: {ir_file}, error={str(e)}"
            )
            raise
