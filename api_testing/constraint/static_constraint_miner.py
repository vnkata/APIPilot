"""
Static constraint mining module.

Extracts constraints from API specifications without executing API calls.
Mines constraints from response schemas and request-response mappings.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple
from api_testing.dataset import SpecificationParser
from api_testing.models.base_model import (
    APITestingBaseEmbeddingModel,
    APITestingBaseLLMModel,
)
from api_testing.models.specification_model import ItemProperties, OperationProperties
from api_testing.constraint.config import ConstraintExtractionSettings
from api_testing.prompts.response_constraints import ResponsePropertyConstraintMiner
from api_testing.prompts.request_response_constraint.miner import (
    RequestResponseConstraintMiner,
)
from api_testing.utils import flatten_json_schema
from api_testing.utils.graph import is_nested_path_end_with
from common.logger import get_logger, LogLevel

from api_testing.constraint.ir.static_schemas import (
    OperationConstraintsData,
    StaticConstraintMinerOutput,
)


# Type aliases for constraint data structures
ConstraintDict = Dict[str, str]  # Maps attribute path to constraint description
OperationConstraints = Dict[str, ConstraintDict]  # Maps operation UUID to constraints
SchemaConstraints = Dict[str, ConstraintDict]  # Maps schema name to constraints
RequestResponseConstraintsDict = Dict[
    str, Dict[str, Dict[str, str]]
]  # Nested request-response constraints


class StaticConstraintMiner:
    """Mines constraints from API specifications statically.

    Extracts constraints from response schemas and identifies relationships
    between request parameters and response properties without executing
    API calls.

    Attributes:
        spec_parser: Parser for API specification
        model: LLM model for constraint extraction (deprecated, kept for compatibility)
        embedding_model: Embedding model (optional, for future use)
        cache_dir: Directory path for caching extracted constraints
        cache_file: Path to main cache file (static_constraint_miner.json)
        logger: Logger instance
        operations: Dictionary of operation UUIDs to OperationProperties
        schemas: Dictionary of schema names to ItemProperties
        response_constraint: ResponsePropertyConstraintMiner extractor instance
        request_response_constraint: RequestResponseConstraintMiner extractor instance

    Example:
        >>> miner = StaticConstraintMiner(
        ...     spec_parser=parser,
        ...     cache_dir="./cache"
        ... )
        >>> output = await miner.extract_all_constraints()
        >>> print(output.operations["get-/api/v1/holidays"].response_properties_constraints)
    """

    def __init__(
        self,
        spec_parser: Optional[SpecificationParser] = None,
        model: Optional[APITestingBaseLLMModel] = None,
        embedding_model: Optional[APITestingBaseEmbeddingModel] = None,
        cache_dir: Optional[str] = None,
        batch_size: int = 10,
        settings: Optional[ConstraintExtractionSettings] = None,
    ) -> None:
        """Initialize StaticConstraintMiner.

        Args:
            spec_parser: Parser containing parsed API specification
            model: Deprecated LLM model parameter (kept for backward compatibility)
            embedding_model: Optional embedding model for semantic analysis
            cache_dir: Directory path for caching extracted constraints
            batch_size: Number of schemas/operations to process in parallel (default: 10)
            settings: ConstraintExtractionSettings instance (optional, will use defaults if not provided)
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
        self.settings = settings  # Store settings to pass to builder
        self.cache_file = os.path.join(cache_dir, "static_constraint_miner.json")
        # Temp cache files for intermediate results
        self._response_cache_file = os.path.join(
            cache_dir, "_temp_response_constraints.json"
        )
        self._request_response_cache_file = os.path.join(
            cache_dir, "_temp_request_response_constraints.json"
        )
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
        self.request_response_constraint = RequestResponseConstraintMiner()

    async def _extract_single_operation_request_response_constraints(
        self, operation: OperationProperties
    ) -> Tuple[str, Optional[Dict[str, Dict[str, str]]]]:
        """Extract request-response constraints for a single operation.

        Args:
            operation: OperationProperties object

        Returns:
            Tuple of (operation_uuid, constraints_dict)
        """
        from common.llm.exceptions import LLMError

        try:
            self.logger.debug(f"Processing operation: {operation.uuid}")

            # Extract request parameters
            request_params: List[str] = []
            if operation.parameters:
                for param_name, param_props in operation.parameters.items():
                    param_desc = param_props.to_human_readable()
                    request_params.append(f"- {param_name}: {param_desc}")

            if not request_params:
                self.logger.debug(
                    f"Skipping operation with no request params: {operation.uuid}"
                )
                return (operation.uuid, None)

            # Extract response properties
            response_props: List[str] = []
            if operation.successful_responses:
                flattened_responses = flatten_json_schema(
                    operation.successful_responses.to_dict()
                )
                for prop_path, prop_data in flattened_responses.items():
                    if prop_data:
                        prop_desc = ItemProperties(**prop_data).to_human_readable()
                        response_props.append(f"- {prop_path}: {prop_desc}")

            if not response_props:
                self.logger.debug(
                    f"Skipping operation with no response props: {operation.uuid}"
                )
                return (operation.uuid, None)

            # Extract constraints
            result = await self.request_response_constraint.extract_constraints(
                operation_name=operation.uuid,
                method=operation.method,
                path=operation.path,
                request_params="\n".join(request_params),
                response_properties="\n".join(response_props),
            )

            constraints_dict = result.constraints

            self.logger.debug(
                f"Extracted request-response constraints: operation={operation.uuid}, "
                f"constraint_pairs={sum(len(v) for v in constraints_dict.values())}"
            )

            return (operation.uuid, constraints_dict)

        except LLMError as e:
            self.logger.error(
                f"Failed to extract request-response constraints: operation={operation.uuid}, "
                f"error={str(e)}"
            )
            return (operation.uuid, None)
        except Exception as e:
            self.logger.error(
                f"Unexpected error extracting request-response constraints: "
                f"operation={operation.uuid}, error={str(e)}, error_type={type(e).__name__}"
            )
            return (operation.uuid, None)

    async def _extract_request_response_constraints_batch(
        self, operations_batch: List[OperationProperties]
    ) -> Dict[str, Dict[str, Dict[str, str]]]:
        """Extract request-response constraints for a batch of operations.

        Args:
            operations_batch: List of operations to process

        Returns:
            Dictionary mapping operation UUIDs to request-response constraints
        """
        if not operations_batch:
            return {}

        self.logger.debug(
            f"Processing batch of {len(operations_batch)} operations: "
            f"{[op.uuid for op in operations_batch]}"
        )

        tasks = [
            self._extract_single_operation_request_response_constraints(op)
            for op in operations_batch
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        batch_constraints: Dict[str, Dict[str, Dict[str, str]]] = {}
        for i, result in enumerate(results):
            operation = operations_batch[i]

            if isinstance(result, Exception):
                self.logger.error(
                    f"Exception in batch processing: operation={operation.uuid}, "
                    f"error={str(result)}, error_type={type(result).__name__}"
                )
                continue

            op_uuid, constraints_dict = result
            if constraints_dict is not None:
                batch_constraints[op_uuid] = constraints_dict

        self.logger.debug(
            f"Batch completed: {len(batch_constraints)}/{len(operations_batch)} "
            "operations processed successfully"
        )

        return batch_constraints

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

    async def _extract_response_constraints_internal(
        self,
    ) -> OperationConstraints:
        """Internal method to extract response property constraints.

        Returns operation-level constraints (not wrapped in TypedDict).
        Uses temp cache file for intermediate results.

        Returns:
            Dictionary mapping operation UUIDs to response property constraints
        """
        # Load from temp cache if exists
        if os.path.exists(self._response_cache_file):
            self.logger.info(
                f"Loading response constraints from temp cache: {self._response_cache_file}"
            )
            try:
                with open(self._response_cache_file, "r", encoding="utf-8") as file:
                    cached_data = json.load(file)
                    return cached_data
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    f"Failed to load temp cache, will regenerate: error={str(e)}"
                )

        self.logger.info(
            f"Processing {len(self.schemas)} schemas for response properties constraints"
        )

        # Extract constraints for all schemas using batch processing
        schema_constraints: SchemaConstraints = {}
        schemas_list = list(self.schemas.items())
        total_schemas = len(schemas_list)

        # Process schemas in batches
        for batch_start in range(0, total_schemas, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_schemas)
            batch = schemas_list[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (total_schemas + self.batch_size - 1) // self.batch_size

            self.logger.info(
                f"Processing response constraints batch {batch_num}/{total_batches} "
                f"({batch_start + 1}-{batch_end} of {total_schemas} schemas)"
            )

            batch_results = await self._extract_schema_constraints_batch(batch)
            schema_constraints.update(batch_results)

            self.logger.info(
                f"Batch {batch_num}/{total_batches} completed: "
                f"{len(batch_results)} schemas processed successfully"
            )

        # Convert from schema-level to operation-level constraints
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

        # Save to temp cache
        try:
            with open(self._response_cache_file, "w", encoding="utf-8") as file:
                json.dump(final_constraints, file, ensure_ascii=False, indent=2)
            self.logger.info(
                f"Saved response constraints to temp cache: {self._response_cache_file}"
            )
        except IOError as e:
            self.logger.warning(
                f"Failed to write temp cache file: {self._response_cache_file}, error={str(e)}"
            )

        return final_constraints

    async def _extract_request_response_constraints_internal(
        self,
    ) -> RequestResponseConstraintsDict:
        """Internal method to extract request-response constraints.

        Returns nested dict mapping operation -> request_param -> response_property -> description.
        Uses temp cache file for intermediate results.

        Returns:
            Dictionary mapping operation UUIDs to request-response constraints
        """
        # Load from temp cache if exists
        if os.path.exists(self._request_response_cache_file):
            self.logger.info(
                f"Loading request-response constraints from temp cache: {self._request_response_cache_file}"
            )
            try:
                with open(
                    self._request_response_cache_file, "r", encoding="utf-8"
                ) as file:
                    return json.load(file)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    f"Failed to load temp cache, will regenerate: error={str(e)}"
                )

        self.logger.info(
            f"Processing {len(self.operations)} operations for request-response constraints"
        )

        # Process operations in batches
        all_constraints: RequestResponseConstraintsDict = {}
        operations_list = list(self.operations.values())
        total_operations = len(operations_list)

        for batch_start in range(0, total_operations, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_operations)
            batch = operations_list[batch_start:batch_end]
            batch_num = (batch_start // self.batch_size) + 1
            total_batches = (total_operations + self.batch_size - 1) // self.batch_size

            self.logger.info(
                f"Processing request-response constraints batch {batch_num}/{total_batches} "
                f"({batch_start + 1}-{batch_end} of {total_operations} operations)"
            )

            batch_results = await self._extract_request_response_constraints_batch(
                batch
            )
            all_constraints.update(batch_results)

            self.logger.info(
                f"Batch {batch_num}/{total_batches} completed: "
                f"{len(batch_results)} operations processed successfully"
            )

        # Save to temp cache
        try:
            with open(self._request_response_cache_file, "w", encoding="utf-8") as file:
                json.dump(all_constraints, file, ensure_ascii=False, indent=2)
            self.logger.info(
                f"Saved request-response constraints to temp cache: {self._request_response_cache_file}"
            )
        except IOError as e:
            self.logger.warning(
                f"Failed to write temp cache file: {self._request_response_cache_file}, error={str(e)}"
            )

        return all_constraints

    async def extract_all_constraints(
        self,
        force_refresh: bool = False,
    ) -> StaticConstraintMinerOutput:
        """Extract all constraints (response properties + request-response) and return unified output.

        This is the primary entry point that:
        1. Extracts response property constraints (with temp caching)
        2. Extracts request-response constraints (with temp caching)
        3. Merges both into unified operation-level structure
        4. Saves to main cache file (static_constraint_miner.json)

        Args:
            force_refresh: If True, ignore main cache and re-extract all constraints

        Returns:
            StaticConstraintMinerOutput with unified constraints grouped by operation

        Raises:
            IOError: If cache file cannot be written
        """
        # Load from main cache if exists and not forcing refresh
        if not force_refresh and os.path.exists(self.cache_file):
            self.logger.info(
                f"Loading all constraints from main cache: {self.cache_file}"
            )
            try:
                with open(self.cache_file, "r", encoding="utf-8") as file:
                    cached_data = json.load(file)
                    return StaticConstraintMinerOutput(**cached_data)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    f"Failed to load main cache, will regenerate: error={str(e)}"
                )

        self.logger.info("Starting extraction of all constraints")

        # Extract both types of constraints in parallel
        response_task = self._extract_response_constraints_internal()
        request_response_task = self._extract_request_response_constraints_internal()

        response_constraints, request_response_constraints = await asyncio.gather(
            response_task, request_response_task
        )

        # Merge into unified structure
        unified_output = StaticConstraintMinerOutput()

        for op_uuid in self.operations.keys():
            unified_output.operations[op_uuid] = OperationConstraintsData(
                response_properties_constraints=response_constraints.get(op_uuid, {}),
                request_response_constraints=request_response_constraints.get(
                    op_uuid, {}
                ),
            )

        # Save to main cache
        try:
            with open(self.cache_file, "w", encoding="utf-8") as file:
                json.dump(
                    unified_output.model_dump(), file, ensure_ascii=False, indent=2
                )

            total_ops = len(unified_output.operations)
            total_response_constraints = sum(
                len(op.response_properties_constraints)
                for op in unified_output.operations.values()
            )
            total_request_response = sum(
                sum(len(rp) for rp in op.request_response_constraints.values())
                for op in unified_output.operations.values()
            )

            self.logger.info(
                f"Saved unified constraints to main cache: {self.cache_file}, "
                f"operations={total_ops}, "
                f"response_constraints={total_response_constraints}, "
                f"request_response_pairs={total_request_response}"
            )
        except IOError as e:
            self.logger.error(
                f"Failed to write main cache file: {self.cache_file}, error={str(e)}"
            )
            raise

        return unified_output

    # Backward compatibility methods
    async def extract_response_property_constraints(self) -> Dict:
        """Backward compatible method for response property constraints.

        Returns old format wrapped in TypedDict for compatibility.
        Prefer using extract_all_constraints() for new code.
        """
        self.logger.warning(
            "extract_response_property_constraints() is deprecated. "
            "Use extract_all_constraints() instead."
        )

        response_constraints = await self._extract_response_constraints_internal()

        return {"response_properties_constraints": response_constraints}

    async def extract_request_response_constraints(
        self,
    ) -> RequestResponseConstraintsDict:
        """Backward compatible method for request-response constraints.

        Returns nested dict format for compatibility.
        Prefer using extract_all_constraints() for new code.
        """
        self.logger.warning(
            "extract_request_response_constraints() is deprecated. "
            "Use extract_all_constraints() instead."
        )

        return await self._extract_request_response_constraints_internal()

    async def extract_and_save_constraint_ir(self):
        """Primary entry point: Generate and save Constraint IR v2.

        This is the main entry point for the constraint extraction pipeline.
        It orchestrates all phases (structural, description, LLM coverage,
        LLM extraction, cross-field, request-response) and produces:

        1. Final constraint_ir.json
        2. Intermediate outputs for each phase (if save_intermediate=True)
        3. Summary.json with statistics and cache metrics

        Returns:
            ConstraintIRModel with all extracted constraints

        Raises:
            IOError: If constraint IR file cannot be written
        """
        from api_testing.constraint.ir import ConstraintIRBuilder

        self.logger.info(
            "Starting constraint extraction pipeline",
            operations_count=len(self.operations),
            schemas_count=len(self.schemas),
            use_llm=self.model is not None,
        )

        # Build Constraint IR v2 using enhanced builder
        builder = ConstraintIRBuilder(
            operations=self.operations,
            schemas=self.schemas,
            static_constraints_path=self.cache_file,
            cache_dir=os.path.dirname(self.cache_file),
            settings=self.settings,  # Pass settings to builder
        )

        ir = await builder.build()

        # Save final IR
        ir_file = os.path.join(os.path.dirname(self.cache_file), "constraint_ir.json")

        try:
            with open(ir_file, "w", encoding="utf-8") as f:
                json.dump(ir.model_dump(), f, indent=2, ensure_ascii=False)

            total_constraints = sum(
                len(oc.constraints) for oc in ir.operation_constraints.values()
            )

            self.logger.info(
                "Constraint IR extraction complete",
                ir_file=ir_file,
                version=ir.version,
                operations=len(ir.operation_constraints),
                total_constraints=total_constraints,
            )

            return ir

        except IOError as e:
            self.logger.error(
                "Failed to write constraint IR file",
                ir_file=ir_file,
                error=str(e),
            )
            raise
