"""
Constraint IR builder.

Orchestrates the extraction pipeline to build complete Constraint IR from API specifications.
Combines deterministic extraction and LLM normalization (fallback).
Filters fields by static_constraint_miner.json to ensure only validated constraints are processed.
"""

import os
import json
from typing import Dict, List, Optional, Set, Any
from api_testing.models.base_model import (
    APITestingBaseLLMModel,
    APITestingBaseEmbeddingModel,
)
from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.validation.models import (
    ConstraintIRModel,
    OperationConstraintModel,
    CheckModel,
    PredicateModel,
)
from api_testing.validation.selectors import (
    detect_array_paths_from_schema,
    is_array_field,
    convert_to_jsonpath_with_arrays,
)
from api_testing.constraint.deterministic_extractor import DeterministicExtractor
from api_testing.constraint.llm_normalizer import LLMNormalizer
from api_testing.utils import flatten_json_schema
from common.logger import get_logger

logger = get_logger(__name__)


class ConstraintIRBuilder:
    """Build Constraint IR from API operations, filtered by static_constraint_miner.

    Orchestrates extraction pipeline:
    1. Load static_constraint_miner.json to filter allowed fields
    2. Detect array paths from schema structure
    3. Process only fields validated by static constraint miner
    4. Use deterministic extractor (priority)
    5. Fall back to LLM normalizer if deterministic fails
    6. Convert dot notation to JSONPath with array notation
    7. Build and return ConstraintIRModel

    Example:
        >>> builder = ConstraintIRBuilder(
        ...     operations=parser.operations,
        ...     schemas={"Holiday": holiday_schema},
        ...     static_constraints_path=".cache/static_constraint_miner.json",
        ...     llm_client=llm,
        ...     cache_dir=".cache/My API"
        ... )
        >>> ir = await builder.build()
    """

    def __init__(
        self,
        operations: Dict[str, OperationProperties],
        schemas: Dict[str, ItemProperties],
        static_constraints_path: Optional[str] = None,
        llm_client: Optional[APITestingBaseLLMModel] = None,
        embedding_model: Optional[APITestingBaseEmbeddingModel] = None,
        cache_dir: Optional[str] = None,
        logger_instance=None,
    ):
        """Initialize constraint IR builder.

        Args:
            operations: Dictionary of operation UUID to OperationProperties
            schemas: Dictionary of schema name to ItemProperties
            static_constraints_path: Path to static_constraint_miner.json for filtering
            llm_client: LLM client for fallback normalization (optional)
            embedding_model: Embedding model (unused for now, for future)
            cache_dir: Cache directory path (optional, for metadata)
            logger_instance: Logger instance (optional)
        """
        self.operations = operations
        self.schemas = schemas
        self.llm_client = llm_client
        self.embedding_model = embedding_model
        self.cache_dir = cache_dir
        self.logger = logger_instance or logger

        # Initialize extractors
        self.deterministic_extractor = DeterministicExtractor()
        self.llm_normalizer = LLMNormalizer(llm_client=llm_client)

        # Load static_constraint_miner for filtering
        self.allowed_fields_by_op = self._load_static_constraints(
            static_constraints_path
        )

        # Statistics
        self.stats = {
            "operations_processed": 0,
            "schemas_processed": 0,
            "checks_created": 0,
            "deterministic_extractions": 0,
            "llm_normalizations": 0,
            "skipped_no_constraints": 0,
            "skipped_not_mined": 0,
        }

    def _load_static_constraints(self, path: Optional[str]) -> Dict[str, Set[str]]:
        """Load static_constraint_miner.json to get allowed fields per operation.

        Args:
            path: Path to static_constraint_miner.json

        Returns:
            Dictionary mapping operation UUID to set of allowed field paths
        """
        if not path or not os.path.exists(path):
            self.logger.warning(
                "static_constraint_miner not found, will process all fields", path=path
            )
            return {}

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            # Extract field paths from response_properties_constraints
            result = {}
            for op_uuid, constraints in data.get(
                "response_properties_constraints", {}
            ).items():
                if isinstance(constraints, dict):
                    result[op_uuid] = set(constraints.keys())

            self.logger.info(
                "Loaded static constraints filter",
                operations=len(result),
                total_fields=sum(len(v) for v in result.values()),
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to load static_constraint_miner", path=path, error=str(e)
            )
            return {}

    async def build(self) -> ConstraintIRModel:
        """Build complete Constraint IR.

        Returns:
            ConstraintIRModel with all operation constraints
        """
        self.logger.info(
            "Building Constraint IR",
            operations_count=len(self.operations),
            schemas_count=len(self.schemas),
        )

        operation_constraints = {}

        # Process each operation
        for op_uuid, operation in self.operations.items():
            self.logger.debug(
                "Processing operation",
                op_uuid=op_uuid,
                method=operation.http_method,
                path=operation.endpoint_path,
            )

            try:
                op_constraints = await self._build_operation_constraints(operation)
                if op_constraints.checks:  # Only add if there are checks
                    operation_constraints[op_uuid] = op_constraints
                self.stats["operations_processed"] += 1

            except Exception as e:
                self.logger.error(
                    "Error building constraints for operation",
                    op_uuid=op_uuid,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Build final IR model
        ir = ConstraintIRModel(
            version="v1", operation_constraints=operation_constraints
        )

        # Log statistics
        self.logger.info(
            "Constraint IR built successfully",
            **self.stats,
            total_checks=sum(len(oc.checks) for oc in operation_constraints.values()),
        )

        return ir

    async def _build_operation_constraints(
        self, operation: OperationProperties
    ) -> OperationConstraintModel:
        """Build constraints for a single operation, filtered by static_miner.

        Args:
            operation: OperationProperties to extract constraints from

        Returns:
            OperationConstraintModel with checks
        """
        checks = []

        try:
            # Get successful response schema
            successful_response = operation.successful_responses
            self.logger.debug(
                "Got successful_response",
                op_uuid=operation.uuid,
                has_response=successful_response is not None,
                response_type=(
                    type(successful_response).__name__
                    if successful_response
                    else "None"
                ),
            )

            if not successful_response:
                self.logger.debug(
                    "No successful responses for operation",
                    op_uuid=operation.uuid,
                )
                return OperationConstraintModel(checks=[])

            # Get allowed fields for this operation
            allowed_fields = self.allowed_fields_by_op.get(operation.uuid, set())
            self.logger.debug(
                "Got allowed_fields",
                op_uuid=operation.uuid,
                allowed_fields_count=len(allowed_fields),
            )

            if not allowed_fields:
                self.logger.debug(
                    "No static constraints for operation, skipping",
                    op_uuid=operation.uuid,
                )
                return OperationConstraintModel(checks=[])

            # Detect array paths from schema structure
            schema_dict = successful_response.to_dict()
            self.logger.debug(
                "Got schema_dict",
                op_uuid=operation.uuid,
                schema_dict_type=(
                    type(schema_dict).__name__ if schema_dict is not None else "None"
                ),
                has_schema=schema_dict is not None,
            )

            if not schema_dict:
                self.logger.debug(
                    "Schema dict is empty for operation",
                    op_uuid=operation.uuid,
                )
                return OperationConstraintModel(checks=[])

        except Exception as e:
            self.logger.error(
                "Error in pre-processing phase",
                op_uuid=operation.uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        try:
            array_paths = detect_array_paths_from_schema(schema_dict)
            self.logger.debug(
                "Detected array paths",
                op_uuid=operation.uuid,
                array_paths=list(array_paths),
            )
        except Exception as e:
            self.logger.error(
                "Error detecting array paths",
                op_uuid=operation.uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        # Flatten response schema
        try:
            flattened_schema = flatten_json_schema(schema_dict)
            self.logger.debug(
                "Flattened schema",
                op_uuid=operation.uuid,
                flattened_keys_count=len(flattened_schema) if flattened_schema else 0,
            )
        except Exception as e:
            self.logger.error(
                "Error flattening schema",
                op_uuid=operation.uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        if not flattened_schema:
            self.logger.debug(
                "Flattened schema is empty for operation",
                op_uuid=operation.uuid,
            )
            return OperationConstraintModel(checks=[])

        # Process ONLY fields in allowed_fields
        for field_path in allowed_fields:
            try:
                if field_path not in flattened_schema:
                    self.logger.warning(
                        "Field in static_miner but not in schema",
                        op_uuid=operation.uuid,
                        field_path=field_path,
                    )
                    continue

                field_props = flattened_schema.get(field_path)
                if not field_props:
                    self.logger.warning(
                        "Field props is None",
                        op_uuid=operation.uuid,
                        field_path=field_path,
                    )
                    continue

                # Skip object/array types (validate their properties instead)
                if not isinstance(field_props, dict):
                    self.logger.warning(
                        "Field props is not a dict",
                        op_uuid=operation.uuid,
                        field_path=field_path,
                        field_props_type=type(field_props).__name__,
                    )
                    continue

                if field_props.get("type") in ["object", "array", None]:
                    continue

                # Convert dict to ItemProperties
                item_props = ItemProperties(**field_props)

                # Extract predicates
                predicates = await self._extract_predicates(item_props, field_path)

                if not predicates:
                    self.stats["skipped_no_constraints"] += 1
                    continue

                # Convert to JSONPath WITH array detection
                jsonpath_selector = convert_to_jsonpath_with_arrays(
                    field_path, array_paths
                )

                self.logger.debug(
                    "Generated JSONPath selector",
                    field_path=field_path,
                    jsonpath=jsonpath_selector,
                    is_array=is_array_field(field_path, array_paths),
                )

                # Create check
                check = CheckModel(
                    id=f"{operation.uuid}.{field_path}",
                    selector=jsonpath_selector,
                    predicates=predicates,
                    severity="error",
                )

                checks.append(check)
                self.stats["checks_created"] += 1

            except Exception as e:
                self.logger.error(
                    "Error processing field",
                    op_uuid=operation.uuid,
                    field_path=field_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                continue

        return OperationConstraintModel(checks=checks)

    async def _extract_predicates(
        self, item_props: ItemProperties, field_path: str
    ) -> List[PredicateModel]:
        """Extract predicates for a field.

        Tries deterministic extraction first, falls back to LLM if needed.

        Args:
            item_props: ItemProperties for the field
            field_path: Dot notation path to field

        Returns:
            List of PredicateModel objects
        """
        # Try deterministic extraction first
        if self.deterministic_extractor.can_extract(item_props):
            predicates = self.deterministic_extractor.extract_predicates(
                item_props, field_path
            )

            if predicates:
                self.stats["deterministic_extractions"] += 1
                self.logger.debug(
                    "Deterministic extraction succeeded",
                    field_path=field_path,
                    predicates_count=len(predicates),
                )
                return predicates

        # Fall back to LLM normalizer if:
        # 1. Deterministic extraction returned no predicates
        # 2. LLM client is available
        # 3. Field has description that might contain constraints
        if self.llm_client and item_props.description:
            # Use to_human_readable() to get constraint description
            constraint_text = item_props.to_human_readable(ingore_type=False)

            if constraint_text:
                self.logger.debug(
                    "Attempting LLM normalization",
                    field_path=field_path,
                    constraint_text=constraint_text[:100],
                )

                predicates = await self.llm_normalizer.normalize_async(
                    constraint_text=constraint_text,
                    item_props=item_props,
                    field_path=field_path,
                )

                if predicates:
                    self.stats["llm_normalizations"] += 1
                    return predicates

        return []


__all__ = ["ConstraintIRBuilder"]
