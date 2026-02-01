"""
Single-field response property analyzer.

Implements unified 3-phase pipeline for extracting constraints on individual response fields.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from api_testing.constraint.ir.cache import SchemaConstraintCache
from api_testing.constraint.ir.config.settings import SingleFieldAnalyzerSettings
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from api_testing.constraint.ir.extractors.response_property.single.coverage_checker import (
    ResPropSingleCoverageChecker,
)
from api_testing.constraint.ir.extractors.response_property.single.heuristic_description import (
    ResPropSingleDescriptionExtractor,
)
from api_testing.constraint.ir.extractors.response_property.single.heuristic_structural import (
    ResPropSingleStructuralExtractor,
)
from api_testing.constraint.ir.extractors.response_property.single.llm_extractor import (
    ResPropSingleLLMExtractor,
)
from api_testing.models.specification_model import ItemProperties
from common.logger import get_logger

logger = get_logger(__name__)


class SingleFieldResponseAnalyzer:
    """Unified analyzer for single-field response constraints.

    Implements 3-phase pipeline matching CrossFieldResponseAnalyzer
    and RequestResponseAnalyzer:
    1. extract_heuristic() - Structural + Description patterns
    2. check_coverage() - LLM-based gap detection
    3. extract_llm() - LLM extraction for missing constraints

    Intermediate outputs are saved per operation_id:
        intermediate/1_respropsingle/{operation_id}/heuristic.json
        intermediate/1_respropsingle/{operation_id}/coverage.json
        intermediate/1_respropsingle/{operation_id}/llm.json
        intermediate/1_respropsingle/{operation_id}/final.json

    Attributes:
        use_llm: Whether to use LLM extractors
        structural_extractor: Extractor for structural constraints
        description_extractor: Extractor for description-based constraints
        coverage_checker: LLM-based coverage checker (if use_llm=True)
        llm_extractor: LLM-based constraint extractor (if use_llm=True)
    """

    def __init__(
        self,
        settings: SingleFieldAnalyzerSettings,
        intermediate_dir: Path | None = None,
        schema_cache: SchemaConstraintCache | None = None,
    ):
        """Initialize analyzer with extractors.

        Args:
            settings: SingleFieldAnalyzerSettings instance
            intermediate_dir: Directory for intermediate outputs
            schema_cache: Schema-level cache for reusing results
        """
        self.settings = settings
        self.intermediate_dir = intermediate_dir
        self.schema_cache = schema_cache

        # Base output dir (operation subfolders created dynamically)
        self.base_output_dir = None
        if self.intermediate_dir:
            self.base_output_dir = self.intermediate_dir / "1_respropsingle"
            self.base_output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize extractors based on settings
        self.structural_extractor = (
            ResPropSingleStructuralExtractor()
            if self.settings.heuristic.enabled and self.settings.heuristic.structural
            else None
        )

        self.description_extractor = (
            ResPropSingleDescriptionExtractor(
                use_llm_fallback=self.settings.heuristic.use_llm_for_description
            )
            if self.settings.heuristic.enabled and self.settings.heuristic.description
            else None
        )

        self.coverage_checker = (
            ResPropSingleCoverageChecker()
            if self.settings.coverage_check.enabled
            else None
        )

        self.llm_extractor = (
            ResPropSingleLLMExtractor()
            if self.settings.llm_extraction.enabled
            else None
        )

        # Track results per operation for aggregated saving
        self._operation_results: dict = defaultdict(list)

        logger.debug(
            "Initialized SingleFieldResponseAnalyzer",
            settings_enabled=self.settings.enabled,
            heuristic_enabled=self.settings.heuristic.enabled,
            coverage_enabled=self.settings.coverage_check.enabled,
            llm_enabled=self.settings.llm_extraction.enabled,
            has_intermediate_dir=intermediate_dir is not None,
            has_cache=schema_cache is not None,
        )

    def _get_operation_output_dir(self, operation_id: str) -> Path | None:
        """Get output directory for a specific operation.

        Args:
            operation_id: Operation UUID

        Returns:
            Path to operation output directory or None
        """
        if not self.base_output_dir:
            return None

        # Sanitize operation_id for filesystem
        safe_op_id = operation_id.replace("/", "_").replace("\\", "_")
        op_dir = self.base_output_dir / safe_op_id
        op_dir.mkdir(parents=True, exist_ok=True)
        return op_dir

    def _save_intermediate(
        self,
        operation_id: str,
        phase_name: str,
        data: list[CandidateConstraint],
        stats: dict,
    ) -> None:
        """Save intermediate output with metadata wrapper.

        Args:
            operation_id: Operation UUID
            phase_name: Name of the phase (e.g., 'heuristic', 'coverage', 'llm', 'final')
            data: List of CandidateConstraint instances
            stats: Statistics dictionary
        """
        output_dir = self._get_operation_output_dir(operation_id)
        if not output_dir:
            return

        # Serialize CandidateConstraint instances
        serialized_data = [c.model_dump() for c in data]

        output = {
            "phase": f"1_{phase_name}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation_id": operation_id,
            "data": serialized_data,
            "stats": stats,
            "success": True,
        }

        filepath = output_dir / f"{phase_name}.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved intermediate output: {operation_id}/{phase_name}.json")
        except Exception as e:
            logger.error(
                f"Failed to save intermediate output: {phase_name}.json", error=str(e)
            )

    def _save_coverage_intermediate(
        self,
        operation_id: str,
        missing: list[str],
        field_path: str,
        description: str | None,
    ) -> None:
        """Save coverage check intermediate output.

        Args:
            operation_id: Operation UUID
            missing: List of missing constraint descriptions
            field_path: Field path
            description: Field description
        """
        output_dir = self._get_operation_output_dir(operation_id)
        if not output_dir:
            return

        output = {
            "phase": "1_coverage",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation_id": operation_id,
            "data": {
                "missing_constraints": missing,
                "field_path": field_path,
                "field_description": description,
            },
            "stats": {
                "is_sufficient": len(missing) == 0,
                "missing_count": len(missing),
            },
            "success": True,
        }

        filepath = output_dir / "coverage.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to save coverage output", error=str(e))

    async def analyze(
        self,
        item_props: ItemProperties,
        field_path: str,
        operation_id: str,
        array_paths: list[str] | set[str] | None = None,
    ) -> list[CandidateConstraint]:
        """Run complete 3-phase pipeline with intermediate saving.

        Args:
            item_props: ItemProperties object
            field_path: Dot-notation field path
            operation_id: Operation UUID for scope
            array_paths: Array paths for JSONPath conversion (List or Set)

        Returns:
            List of CandidateConstraint instances
        """
        # Normalize array_paths to list for downstream compatibility
        array_paths_list: list[str] = list(array_paths) if array_paths else []
        logger.debug(
            "Analyzing single field",
            field_path=field_path,
            operation_id=operation_id,
        )

        # Check cache first (using schema name as key)
        schema_name = item_props.xrefs
        if schema_name and self.schema_cache:
            cached = self.schema_cache.get(schema_name)
            if cached is not None:
                logger.debug(f"Using cached results for schema: {schema_name}")
                # Update operation_id in cached results
                for c in cached:
                    if hasattr(c, "operation_id"):
                        c.operation_id = operation_id
                return cached

        try:
            # Phase 1: Heuristic extraction (if enabled)
            predicates: list[CandidateConstraint] = []
            if self.settings.heuristic.enabled:
                predicates = await self.extract_heuristic(
                    item_props, field_path, operation_id, array_paths_list
                )

                # Calculate stats
                structural_count = len(
                    [c for c in predicates if "structural" in c.tags]
                )
                description_count = len(
                    [c for c in predicates if "description" in c.tags]
                )

                self._save_intermediate(
                    operation_id,
                    "heuristic",
                    predicates,
                    {
                        "structural_count": structural_count,
                        "description_count": description_count,
                        "total_count": len(predicates),
                        "field_path": field_path,
                    },
                )
            else:
                logger.debug(
                    "Heuristic extraction disabled, skipping",
                    field_path=field_path,
                    operation_id=operation_id,
                )

            # Phase 2: Coverage check (if enabled and description exists)
            missing: list[str] = []
            if self.settings.coverage_check.enabled and item_props.description:
                missing = await self.check_coverage(
                    item_props, field_path, predicates, operation_id
                )
                self._save_coverage_intermediate(
                    operation_id, missing, field_path, item_props.description
                )
            elif not self.settings.coverage_check.enabled:
                logger.debug(
                    "Coverage check disabled, skipping",
                    field_path=field_path,
                    operation_id=operation_id,
                )

            # Phase 3: LLM extraction for gaps (if enabled)
            if self.settings.llm_extraction.enabled and missing and self.llm_extractor:
                llm_preds = await self.extract_llm(
                    item_props, field_path, missing, operation_id, array_paths_list
                )
                predicates.extend(llm_preds)
                self._save_intermediate(
                    operation_id,
                    "llm",
                    llm_preds,
                    {"extracted_count": len(llm_preds), "field_path": field_path},
                )
            elif not self.settings.llm_extraction.enabled:
                logger.debug(
                    "LLM extraction disabled, skipping",
                    field_path=field_path,
                    operation_id=operation_id,
                )

            # Save final results
            self._save_intermediate(
                operation_id,
                "final",
                predicates,
                {"total_predicates": len(predicates), "field_path": field_path},
            )

            # Update cache
            if schema_name and self.schema_cache:
                self.schema_cache.set(schema_name, predicates)
                logger.debug(f"Cached results for schema: {schema_name}")

            logger.debug(
                "Single field analysis complete",
                field_path=field_path,
                operation_id=operation_id,
                predicates_count=len(predicates),
            )

            return predicates

        except Exception as e:
            self._save_error(operation_id, field_path, e)
            logger.error(
                "Single field analysis failed",
                field_path=field_path,
                operation_id=operation_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _save_error(self, operation_id: str, field_path: str, error: Exception) -> None:
        """Save error output.

        Args:
            operation_id: Operation UUID
            field_path: Field path
            error: Exception that occurred
        """
        output_dir = self._get_operation_output_dir(operation_id)
        if not output_dir:
            return

        error_output = {
            "phase": "1_error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation_id": operation_id,
            "success": False,
            "field_path": field_path,
            "error": {
                "message": str(error),
                "type": type(error).__name__,
            },
            "data": [],
            "stats": {},
        }

        error_filepath = output_dir / "error.json"
        try:
            with open(error_filepath, "w", encoding="utf-8") as f:
                json.dump(error_output, f, indent=2, ensure_ascii=False)
        except Exception as save_error:
            logger.error("Failed to save error output", error=str(save_error))

    async def extract_heuristic(
        self,
        item_props: ItemProperties,
        field_path: str,
        operation_id: str,
        array_paths: list[str] | None = None,
    ) -> list[CandidateConstraint]:
        """Phase 1: Structural + Description heuristics.

        Args:
            item_props: ItemProperties object
            field_path: Dot-notation field path
            operation_id: Operation UUID
            array_paths: List of array paths for JSONPath conversion

        Returns:
            List of CandidateConstraint instances
        """
        predicates: list[CandidateConstraint] = []
        errors = []

        # Structural constraints (if enabled)
        if self.structural_extractor:
            try:
                structural_preds = self.structural_extractor.extract(
                    item_props, field_path, operation_id, array_paths
                )
                predicates.extend(structural_preds)
            except Exception as e:
                error_msg = f"Structural extraction failed: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    error_msg,
                    field_path=field_path,
                    operation_id=operation_id,
                    error_type=type(e).__name__,
                    exc_info=True,
                )

        # Description-based constraints (if enabled and description exists)
        if self.description_extractor and item_props.description:
            try:
                desc_preds = await self.description_extractor.extract(
                    item_props, field_path, operation_id, array_paths
                )
                predicates.extend(desc_preds)
            except Exception as e:
                error_msg = f"Description extraction failed: {str(e)}"
                errors.append(error_msg)
                logger.warning(
                    error_msg,
                    field_path=field_path,
                    operation_id=operation_id,
                    error_type=type(e).__name__,
                )

        logger.debug(
            "Heuristic extraction complete",
            field_path=field_path,
            operation_id=operation_id,
            structural_count=len([c for c in predicates if "structural" in c.tags]),
            description_count=len([c for c in predicates if "description" in c.tags]),
            error_count=len(errors),
        )

        return predicates

    async def check_coverage(
        self,
        item_props: ItemProperties,
        field_path: str,
        existing: list[CandidateConstraint],
        operation_id: str,
    ) -> list[str]:
        """Phase 2: Check if constraints are sufficient.

        Args:
            item_props: ItemProperties object
            field_path: Dot-notation field path
            existing: List of existing CandidateConstraint instances
            operation_id: Operation UUID

        Returns:
            List of missing constraint descriptions (empty if sufficient)
        """
        if not self.coverage_checker:
            return []

        try:
            # Convert CandidateConstraint to dict format for coverage checker
            existing_dicts = [
                {
                    "predicate": {
                        "kind": c.predicate_kind,
                        "version": c.predicate_version,
                        "args": c.predicate_args,
                    },
                    "provenance": {
                        "kind": c.evidence[0].source if c.evidence else "unknown",
                        "confidence": c.confidence,
                    },
                }
                for c in existing
            ]

            missing = await self.coverage_checker.check_coverage(
                item_props, field_path, existing_dicts
            )

            logger.debug(
                "Coverage check complete",
                field_path=field_path,
                operation_id=operation_id,
                missing_count=len(missing) if missing else 0,
            )

            return missing or []

        except Exception as e:
            error_msg = f"Coverage check failed: {str(e)}"
            logger.warning(
                error_msg,
                field_path=field_path,
                operation_id=operation_id,
                error_type=type(e).__name__,
            )
            return []

    async def extract_llm(
        self,
        item_props: ItemProperties,
        field_path: str,
        missing: list[str],
        operation_id: str,
        array_paths: list[str] | None = None,
    ) -> list[CandidateConstraint]:
        """Phase 3: LLM extraction for missing constraints.

        Args:
            item_props: ItemProperties object
            field_path: Dot-notation field path
            missing: List of missing constraint descriptions
            operation_id: Operation UUID
            array_paths: List of array paths for JSONPath conversion

        Returns:
            List of CandidateConstraint instances
        """
        if not self.llm_extractor or not missing:
            return []

        try:
            llm_preds = await self.llm_extractor.extract(
                item_props, field_path, missing, operation_id, array_paths
            )

            logger.debug(
                "LLM extraction complete",
                field_path=field_path,
                operation_id=operation_id,
                predicates_count=len(llm_preds) if llm_preds else 0,
            )

            return llm_preds or []

        except Exception as e:
            error_msg = f"LLM extraction failed: {str(e)}"
            logger.warning(
                error_msg,
                field_path=field_path,
                operation_id=operation_id,
                error_type=type(e).__name__,
            )
            return []


__all__ = ["SingleFieldResponseAnalyzer"]
