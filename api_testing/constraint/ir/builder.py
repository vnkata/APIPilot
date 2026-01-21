"""
Constraint IR Builder.

Orchestrates the complete extraction pipeline and builds the final IR document.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.ir.models import (
    ConstraintModel,
    OperationConstraintsModel,
    ConstraintIRModel,
    PredicateModel,
    ProvenanceModel,
    ScopeModel,
    SelectorModel,
)
from api_testing.constraint.ir.merge import merge_duplicate_constraints
from api_testing.constraint.extractors import (
    CrossFieldResponseAnalyzer,
    RequestResponseAnalyzer,
)
from api_testing.constraint.cache import SchemaConstraintCache
from api_testing.constraint.config import (
    ConstraintExtractionSettings,
    get_constraint_settings,
)
from api_testing.utils import flatten_json_schema
from api_testing.validation.selectors import (
    detect_array_paths_from_schema,
    convert_to_jsonpath_with_arrays,
)
from common.logger import get_logger

logger = get_logger(__name__)


class ConstraintIRBuilder:
    """Build Constraint IR v2 from API operations.

    Orchestrates multi-phase extraction pipeline:
    1. Structural extraction (deterministic)
    2. Description extraction (pattern catalog + LLM fallback)
    3. LLM coverage check (diff-based)
    4. LLM extraction (for missing constraints)

    Outputs complete IR with Scope, Provenance, and Selectors.
    """

    def __init__(
        self,
        operations: Dict[str, OperationProperties],
        schemas: Dict[str, ItemProperties],
        static_constraints_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
        settings: Optional[ConstraintExtractionSettings] = None,
    ):
        """Initialize IR builder.

        Args:
            operations: Dictionary of operation UUID to OperationProperties
            schemas: Dictionary of schema name to ItemProperties
            static_constraints_path: Path to static_constraint_miner.json for filtering
            cache_dir: Cache directory path
            settings: ConstraintExtractionSettings instance (recommended)
        """
        self.operations = operations
        self.schemas = schemas
        self.cache_dir = cache_dir

        # Load or use provided settings (immutable)
        self.settings = settings or get_constraint_settings()

        # Validate LLM availability
        if self.settings.requires_llm():
            logger.info(
                "LLM features enabled - ensure LLM model is configured",
                requires_llm=True,
            )
        else:
            logger.info("Running in heuristic-only mode (no LLM)", requires_llm=False)

        # Setup intermediate output directory
        if self.settings.save_intermediate and cache_dir:
            self.intermediate_dir = Path(cache_dir) / "intermediate"
            self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.intermediate_dir = None

        # Initialize schema-level cache
        self.schema_cache = (
            SchemaConstraintCache() if self.settings.use_schema_cache else None
        )

        # Initialize analyzers based on settings
        from api_testing.constraint.extractors.response_property.single import (
            SingleFieldResponseAnalyzer,
        )

        # Single-field analyzer
        if self.settings.single_field.enabled:
            self.single_field_analyzer = SingleFieldResponseAnalyzer(
                settings=self.settings.single_field,
                intermediate_dir=self.intermediate_dir,
                schema_cache=self.schema_cache,
            )
            logger.info(
                "Single-field analyzer enabled",
                heuristic=self.settings.single_field.heuristic.enabled,
                coverage=self.settings.single_field.coverage_check.enabled,
                llm=self.settings.single_field.llm_extraction.enabled,
            )
        else:
            self.single_field_analyzer = None
            logger.info("Single-field analyzer disabled")

        # Cross-field analyzer
        if self.settings.crossfield_response.enabled:
            self.crossfield_response_analyzer = CrossFieldResponseAnalyzer(
                settings=self.settings.crossfield_response,
                intermediate_dir=self.intermediate_dir,
            )
            logger.info(
                "Cross-field analyzer enabled",
                heuristic=self.settings.crossfield_response.heuristic,
                coverage=self.settings.crossfield_response.coverage_check,
                llm=self.settings.crossfield_response.llm_extraction,
            )
        else:
            self.crossfield_response_analyzer = None
            logger.info("Cross-field analyzer disabled")

        # Request-response analyzer
        if self.settings.request_response.enabled:
            self.request_response_analyzer = RequestResponseAnalyzer(
                settings=self.settings.request_response,
                intermediate_dir=self.intermediate_dir,
            )
            logger.info(
                "Request-response analyzer enabled",
                heuristic=self.settings.request_response.heuristic,
                coverage=self.settings.request_response.coverage_check,
                llm=self.settings.request_response.llm_extraction,
            )
        else:
            self.request_response_analyzer = None
            logger.info("Request-response analyzer disabled")

        # Load allowed fields from static miner
        self.allowed_fields_by_op = self._load_static_constraints(
            static_constraints_path
        )

        # Statistics
        self.stats = {
            "operations_processed": 0,
            "constraints_created": 0,
            "structural_extractions": 0,
            "description_extractions": 0,
            "llm_coverage_checks": 0,
            "llm_extractions": 0,
            "skipped_no_static": 0,
            "schema_cache_hits": 0,
            "schema_cache_misses": 0,
        }

        # Phase-specific stats
        self.phase_stats = {
            "phase_1_structural": {
                "predicates_extracted": 0,
                "fields_processed": 0,
                "errors": 0,
            },
            "phase_2_description": {
                "predicates_extracted": 0,
                "llm_calls": 0,
                "pattern_matches": 0,
                "errors": 0,
            },
            "phase_3_llm_coverage": {"gaps_found": 0, "llm_calls": 0, "errors": 0},
            "phase_4_llm_extraction": {
                "predicates_extracted": 0,
                "llm_calls": 0,
                "failures": 0,
                "errors": 0,
            },
            "phase_5_crossfield_response": {
                "heuristic_found": 0,
                "llm_needed": 0,
                "predicates_suggested": 0,
                "relationships_analyzed": 0,
                "constraints_created": 0,
                "llm_calls": 0,
                "errors": 0,
            },
            "phase_6_request_response": {
                "heuristic_found": 0,
                "unmatched_params": 0,
                "llm_extracted": 0,
                "predicates_suggested": 0,
                "candidates_extracted": 0,
                "constraints_created": 0,
                "heuristic_matches": 0,
                "errors": 0,
            },
        }

    def _load_static_constraints(self, path: Optional[str]) -> Dict[str, Set[str]]:
        """Load static_constraint_miner.json to filter fields.

        Args:
            path: Path to static_constraint_miner.json

        Returns:
            Dictionary mapping operation UUID to set of allowed field paths
        """
        if not path or not os.path.exists(path):
            logger.warning(
                "static_constraint_miner not found, will process all fields", path=path
            )
            return {}

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            result = {}
            for op_uuid, constraints in data.get(
                "response_properties_constraints", {}
            ).items():
                if isinstance(constraints, dict):
                    result[op_uuid] = set(constraints.keys())

            logger.info(
                "Loaded static constraints filter",
                operations=len(result),
                total_fields=sum(len(v) for v in result.values()),
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to load static_constraint_miner", path=path, error=str(e)
            )
            return {}

    def _save_summary_report(self) -> None:
        """Save summary report with all statistics.

        Creates summary.json with phase statistics, cache stats, and error summary.
        """
        if not self.intermediate_dir:
            return

        try:
            # Get cache statistics
            cache_stats = self.schema_cache.get_stats()

            # Calculate error totals
            error_summary = {
                "total_errors": sum(
                    phase.get("errors", 0) for phase in self.phase_stats.values()
                ),
                "by_phase": {
                    phase_name: phase.get("errors", 0)
                    for phase_name, phase in self.phase_stats.items()
                },
            }

            # Create summary
            summary = {
                "created_at": datetime.utcnow().isoformat() + "Z",
                "tool": "ConstraintIRBuilder",
                "phases": self.phase_stats,
                "overall_stats": self.stats,
                "cache_stats": cache_stats,
                "error_summary": error_summary,
                "configuration": self.settings.get_summary(),
            }

            # Save summary
            summary_file = self.intermediate_dir / "summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info(
                "Saved summary report",
                file=str(summary_file),
                total_errors=error_summary["total_errors"],
                cache_hit_rate=cache_stats.get("hit_rate", 0),
            )

        except Exception as e:
            logger.error("Failed to save summary report", error=str(e))

    async def build(self) -> ConstraintIRModel:
        """Build complete Constraint IR v2.

        Returns:
            ConstraintIRModel with all constraints
        """
        logger.info(
            "Building Constraint IR v2",
            operations_count=len(self.operations),
            requires_llm=self.settings.requires_llm(),
        )

        operation_constraints = {}

        # Process each operation - Phase 1-4: Single-field constraints
        for op_uuid, operation in self.operations.items():
            try:
                constraints = await self._build_operation_constraints(operation)
                if constraints:
                    operation_constraints[op_uuid] = OperationConstraintsModel(
                        constraints=constraints
                    )
                self.stats["operations_processed"] += 1

            except Exception as e:
                logger.error(
                    "Error building constraints for operation",
                    op_uuid=op_uuid,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Phase 5: Cross-field response constraints
        if self.crossfield_response_analyzer:
            await self._add_crossfield_response_constraints(operation_constraints)

        # Phase 6: Request-response constraints
        if self.request_response_analyzer:
            await self._add_request_response_constraints(operation_constraints)

        # Build IR model with detailed statistics
        all_stats = {**self.stats, **self.phase_stats}

        # Add cache statistics
        cache_stats = self.schema_cache.get_stats()
        all_stats["cache_statistics"] = cache_stats

        ir = ConstraintIRModel(
            version="v2",
            operation_constraints=operation_constraints,
            metadata={
                "created_at": datetime.utcnow().isoformat() + "Z",
                "tool": "ConstraintIRBuilder",
                "requires_llm": self.settings.requires_llm(),
                "configuration": self.settings.get_summary(),
                "statistics": all_stats,
            },
        )

        # Log statistics
        logger.info(
            "Constraint IR v2 built successfully",
            **self.stats,
            total_constraints=sum(
                len(operation_constraint.constraints)
                for operation_constraint in operation_constraints.values()
            ),
        )

        # Save summary report if enabled
        if self.settings.save_intermediate:
            self._save_summary_report()

        # Generate CSV reports at the end
        if self.settings.save_intermediate and self.intermediate_dir:
            from api_testing.constraint.reporting import CSVReporter

            logger.info("Generating CSV reports")
            reporter = CSVReporter(
                intermediate_dir=self.intermediate_dir,
                output_dir=self.intermediate_dir / "reports",
            )
            reporter.generate_all_reports(ir)

        return ir

    async def _build_operation_constraints(
        self, operation: OperationProperties
    ) -> List[ConstraintModel]:
        """Build constraints for a single operation.

        Args:
            operation: OperationProperties

        Returns:
            List of ConstraintModel objects
        """
        constraints = []

        # Get successful response schema
        successful_response = operation.successful_responses
        if not successful_response:
            logger.debug("No successful responses", op_uuid=operation.uuid)
            return []

        # Get allowed fields for this operation
        allowed_fields = self.allowed_fields_by_op.get(operation.uuid, set())
        if not allowed_fields:
            self.stats["skipped_no_static"] += 1
            logger.debug("No static constraints, skipping", op_uuid=operation.uuid)
            return []

        # Detect array paths from schema
        schema_dict = successful_response.to_dict()
        array_paths = detect_array_paths_from_schema(schema_dict)

        # Flatten schema
        flattened_schema = flatten_json_schema(schema_dict)
        if not flattened_schema:
            return []

        # Process each allowed field
        for field_path in allowed_fields:
            if field_path not in flattened_schema:
                continue

            field_props_dict = flattened_schema.get(field_path)
            if not field_props_dict or field_props_dict.get("type") in [
                "object",
                "array",
                None,
            ]:
                continue

            try:
                # Convert to ItemProperties
                item_props = ItemProperties(**field_props_dict)

                # Extract CandidateConstraint instances through pipeline
                candidate_constraints = await self._extract_predicates_pipeline(
                    item_props, field_path, operation.uuid, array_paths
                )

                if not candidate_constraints:
                    continue

                # Convert CandidateConstraint to ConstraintModel
                for candidate in candidate_constraints:
                    constraint = candidate.to_constraint_model()
                    constraints.append(constraint)
                    self.stats["constraints_created"] += 1

            except Exception as e:
                logger.error(
                    "Error processing field",
                    op_uuid=operation.uuid,
                    field_path=field_path,
                    error=str(e),
                    error_type=type(e).__name__,
                )

        # Deduplicate constraints before returning
        if constraints:
            constraints = merge_duplicate_constraints(constraints)

        return constraints

    async def _extract_predicates_pipeline(
        self,
        item_props: ItemProperties,
        field_path: str,
        op_uuid: str,
        array_paths: Optional[List[str]] = None,
    ) -> List:
        """Run complete extraction pipeline for a field.

        Uses schema-level caching to avoid redundant extraction when
        multiple operations use the same schema.

        Args:
            item_props: ItemProperties
            field_path: Field path
            op_uuid: Operation UUID
            array_paths: List of array paths for JSONPath conversion

        Returns:
            List of CandidateConstraint instances
        """
        from api_testing.constraint.extractors.common import CandidateConstraint

        # Skip if single-field analyzer is disabled
        if not self.single_field_analyzer:
            return []

        # Use SingleFieldResponseAnalyzer which handles:
        # - Caching (checks and sets cache internally)
        # - Heuristic extraction (structural + description)
        # - Coverage check
        # - LLM extraction
        # - Intermediate output saving (per operation_id)
        all_candidates: List[CandidateConstraint] = (
            await self.single_field_analyzer.analyze(
                item_props, field_path, op_uuid, array_paths
            )
        )

        # Update stats
        if all_candidates:
            # Count by tag type
            structural_count = len(
                [c for c in all_candidates if "structural" in c.tags]
            )
            description_count = len(
                [c for c in all_candidates if "description" in c.tags]
            )
            llm_count = len([c for c in all_candidates if "llm" in c.tags])

            if structural_count > 0:
                self.stats["structural_extractions"] += 1
                self.phase_stats["phase_1_structural"][
                    "predicates_extracted"
                ] += structural_count
                self.phase_stats["phase_1_structural"]["fields_processed"] += 1

            if description_count > 0:
                self.stats["description_extractions"] += 1
                self.phase_stats["phase_2_description"][
                    "predicates_extracted"
                ] += description_count

            if llm_count > 0:
                self.stats["llm_extractions"] += 1
                self.phase_stats["phase_4_llm_extraction"][
                    "predicates_extracted"
                ] += llm_count

        return all_candidates

    async def _add_crossfield_response_constraints(
        self,
        operation_constraints: Dict[str, OperationConstraintsModel],
    ) -> None:
        """Add cross-field response constraints using refactored analyzer.

        Args:
            operation_constraints: Dictionary of operation constraints to augment
        """
        logger.info("Analyzing cross-field response relationships")

        for op_uuid, operation in self.operations.items():
            try:
                # Get successful response schema
                response_schema = operation.get_success_response_schema()
                if not response_schema:
                    continue

                # Analyze using refactored analyzer
                candidates = await self.crossfield_response_analyzer.analyze(
                    operation, response_schema
                )

                if not candidates:
                    continue

                # Convert candidates to ConstraintModel
                constraints = []
                for candidate in candidates:
                    constraint = candidate.to_constraint_model()
                    constraints.append(constraint)

                # Count heuristic vs LLM
                heuristic_count = sum(
                    1
                    for c in candidates
                    if "heuristic" in [e.source for e in c.evidence]
                )
                llm_count = sum(
                    1 for c in candidates if "llm" in [e.source for e in c.evidence]
                )

                self.phase_stats["phase_5_crossfield_response"][
                    "heuristic_found"
                ] += heuristic_count
                self.phase_stats["phase_5_crossfield_response"][
                    "llm_needed"
                ] += llm_count
                self.phase_stats["phase_5_crossfield_response"][
                    "relationships_analyzed"
                ] += len(candidates)
                self.phase_stats["phase_5_crossfield_response"][
                    "constraints_created"
                ] += len(constraints)

                # Add to operation constraints
                if op_uuid in operation_constraints:
                    operation_constraints[op_uuid].constraints.extend(constraints)
                elif constraints:
                    operation_constraints[op_uuid] = OperationConstraintsModel(
                        constraints=constraints
                    )

                if constraints:
                    logger.info(
                        "Added cross-field response constraints",
                        operation=op_uuid,
                        count=len(constraints),
                    )

            except Exception as e:
                logger.error(
                    "Error analyzing cross-field response for operation",
                    op_uuid=op_uuid,
                    error=str(e),
                )

    async def _add_request_response_constraints(
        self,
        operation_constraints: Dict[str, OperationConstraintsModel],
    ) -> None:
        """Add request-response constraints using new analyzer.

        Args:
            operation_constraints: Dictionary of operation constraints to augment
        """
        logger.info("Analyzing request-response relationships")

        for op_uuid, operation in self.operations.items():
            try:
                # Analyze using request-response analyzer (now async)
                candidates = await self.request_response_analyzer.analyze(operation)

                if not candidates:
                    continue

                # Convert candidates to ConstraintModel
                constraints = []
                for candidate in candidates:
                    constraint = candidate.to_constraint_model()
                    constraints.append(constraint)

                self.phase_stats["phase_6_request_response"][
                    "candidates_extracted"
                ] += len(candidates)
                self.phase_stats["phase_6_request_response"][
                    "constraints_created"
                ] += len(constraints)

                # Count heuristic vs LLM
                heuristic_count = sum(
                    1
                    for c in candidates
                    if "heuristic" in [e.source for e in c.evidence]
                )
                llm_count = sum(
                    1 for c in candidates if "llm" in [e.source for e in c.evidence]
                )

                self.phase_stats["phase_6_request_response"][
                    "heuristic_found"
                ] += heuristic_count
                self.phase_stats["phase_6_request_response"][
                    "llm_extracted"
                ] += llm_count

                # Add to operation constraints
                if op_uuid in operation_constraints:
                    operation_constraints[op_uuid].constraints.extend(constraints)
                elif constraints:
                    operation_constraints[op_uuid] = OperationConstraintsModel(
                        constraints=constraints
                    )

                if constraints:
                    logger.info(
                        "Added request-response constraints",
                        operation=op_uuid,
                        count=len(constraints),
                        heuristic=heuristic_count,
                    )

            except Exception as e:
                logger.error(
                    "Error analyzing request-response for operation",
                    op_uuid=op_uuid,
                    error=str(e),
                )


__all__ = ["ConstraintIRBuilder"]
