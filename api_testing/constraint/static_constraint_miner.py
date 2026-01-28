"""
Static constraint mining module.

Extracts constraints from API specifications without executing API calls.
Mines constraints from response schemas and request-response mappings.
"""

import asyncio
import json
import os
from typing import TYPE_CHECKING, Dict, Optional

from api_testing.constraint.static.assembler import ConstraintAssembler
from api_testing.constraint.ir.config import ConstraintExtractionSettings
from api_testing.constraint.static.extractors.models import (
    OperationConstraintsData,
    StaticConstraintMinerOutput,
)
from api_testing.dataset import SpecificationParser
from api_testing.models.base_model import (
    APITestingBaseEmbeddingModel,
    APITestingBaseLLMModel,
)
from api_testing.models.specification_model import ItemProperties, OperationProperties
from common.logger import LogLevel, get_logger

# Lazy imports to avoid circular dependency
if TYPE_CHECKING:
    from api_testing.constraint.static.extractors.request_response_extractor import (
        RequestResponseExtractor,
    )
    from api_testing.constraint.static.extractors.response_property_extractor import (
        ResponsePropertyExtractor,
    )


class StaticConstraintMiner:
    """Mines constraints from API specifications statically.

    Orchestrates extraction of constraints from response schemas and
    request-response relationships using specialized extractors.

    Attributes:
        spec_parser: Parser for API specification
        cache_dir: Directory path for caching extracted constraints
        cache_file: Path to main cache file (static_constraint_miner.json)
        logger: Logger instance
        operations: Dictionary of operation UUIDs to OperationProperties
        schemas: Dictionary of schema names to ItemProperties
        response_extractor: ResponsePropertyExtractor instance
        request_response_extractor: RequestResponseExtractor instance
        constraint_assembler: ConstraintAssembler instance

    Example:
        >>> miner = StaticConstraintMiner(
        ...     spec_parser=parser,
        ...     cache_dir="ir/cache"
        ... )
        >>> output = await miner.extract_all_constraints()
        >>> print(output.operations["get-/api/v1/holidays"].unified_constraints)
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

        Raises:
            ValueError: If required parameters are missing or invalid
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
        self.settings = settings
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "static_constraint_miner.json")

        # Setup logger
        self.logger = get_logger(
            "static_constraint_miner",
            level=LogLevel.DEBUG,
            console_level=LogLevel.DEBUG,
        )

        # Extract operations and schemas from spec
        self.operations: Dict[str, OperationProperties] = self.spec_parser.operations
        self.schemas: Dict[str, ItemProperties] = {
            k: v for opt in self.operations.values() for k, v in opt.schemas.items()
        }

        # Import extractors here to avoid circular dependency
        from api_testing.constraint.static.extractors.request_response_extractor import (
            RequestResponseExtractor,
        )
        from api_testing.constraint.static.extractors.response_property_extractor import (
            ResponsePropertyExtractor,
        )

        # Initialize specialized extractors with shared logger
        self.response_extractor = ResponsePropertyExtractor(
            spec_parser=spec_parser,
            cache_dir=cache_dir,
            batch_size=batch_size,
            logger=self.logger,
        )

        self.request_response_extractor = RequestResponseExtractor(
            spec_parser=spec_parser,
            cache_dir=cache_dir,
            batch_size=batch_size,
            logger=self.logger,
        )

        # Initialize constraint assembler
        self.constraint_assembler = ConstraintAssembler()

    async def extract_all_constraints(
        self,
        force_refresh: bool = False,
    ) -> StaticConstraintMinerOutput:
        """Extract all constraints (response properties + request-response) and return unified output.

        This is the primary entry point that:
        1. Extracts response property constraints (with temp caching in extractors)
        2. Extracts request-response constraints (with temp caching in extractors)
        3. Merges both into unified operation-level structure
        4. Saves to main cache file (static_constraint_miner.json)

        Args:
            force_refresh: If True, ignore all caches and re-extract all constraints

        Returns:
            StaticConstraintMinerOutput with unified constraints grouped by operation

        Raises:
            IOError: If main cache file cannot be written
        """
        # Load from main cache if exists and not forcing refresh
        if not force_refresh and os.path.exists(self.cache_file):
            self.logger.info(f"Loading from main cache: {self.cache_file}")
            try:
                with open(self.cache_file, "r", encoding="utf-8") as file:
                    cached_data = json.load(file)
                    output = StaticConstraintMinerOutput(**cached_data)
                    self.logger.info(
                        f"Loaded {len(output.operations)} operations from main cache"
                    )
                    return output
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(
                    f"Failed to load main cache: {self.cache_file}, error={str(e)}"
                )

        self.logger.info("Starting extraction of all constraints")

        # Prepare data for extractors
        schemas_list = list(self.schemas.items())
        operations_list = list(self.operations.values())

        # Extract both types of constraints in parallel
        self.logger.info(
            "Running parallel extraction of response and request-response constraints"
        )

        response_task = self.response_extractor.extract_all(
            items=schemas_list,
            force_refresh=force_refresh,
            item_identifier=lambda item: item[0],  # schema_name
        )

        request_response_task = self.request_response_extractor.extract_all(
            items=operations_list,
            force_refresh=force_refresh,
            item_identifier=lambda op: op.uuid,
        )

        response_result, request_response_result = await asyncio.gather(
            response_task, request_response_task
        )

        # Convert schema-level to operation-level constraints
        self.logger.info("Converting schema constraints to operation-level")
        operation_constraints_dict = self.response_extractor.convert_to_operation_level(
            response_result.successful
        )

        # Build lookup dictionaries
        request_response_dict = {
            rr.operation_uuid: rr.constraints
            for rr in request_response_result.successful
        }

        # Merge into unified structure using ConstraintAssembler
        self.logger.info("Assembling unified constraints for all operations")
        unified_output = StaticConstraintMinerOutput()

        for op_uuid, operation in self.operations.items():
            # Get constraints for this operation
            response_properties_constraints = (
                operation_constraints_dict.get(op_uuid).constraints
                if op_uuid in operation_constraints_dict
                else {}
            )

            request_response_constraints = request_response_dict.get(op_uuid, {})

            # Assemble unified constraints
            unified_constraints = (
                self.constraint_assembler.assemble_operation_constraints(
                    operation=operation,
                    response_properties_constraints=response_properties_constraints,
                    request_response_constraints=request_response_constraints,
                )
            )

            # Add to output (note: field name is 'constraints', not 'unified_constraints')
            unified_output.operations[op_uuid] = OperationConstraintsData(
                response_properties_constraints=response_properties_constraints,
                request_response_constraints=request_response_constraints,
                constraints=unified_constraints.to_dict(),
            )

        # Log statistics
        self.logger.info(
            f"Constraint extraction completed: "
            f"{len(unified_output.operations)} operations, "
            f"response_success_rate={response_result.success_rate:.1%}, "
            f"request_response_success_rate={request_response_result.success_rate:.1%}"
        )

        # Save to main cache
        try:
            cache_data = unified_output.model_dump(mode="json")
            with open(self.cache_file, "w", encoding="utf-8") as file:
                json.dump(cache_data, file, ensure_ascii=False, indent=2)

            self.logger.info(
                f"Saved {len(unified_output.operations)} operations to main cache: {self.cache_file}"
            )
        except IOError as e:
            error_msg = (
                f"Failed to write main cache file: {self.cache_file}, error={str(e)}"
            )
            self.logger.error(error_msg)
            raise IOError(error_msg) from e

        return unified_output

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
        from api_testing.constraint.ir.core import ConstraintIRBuilder

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
            settings=self.settings,
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
