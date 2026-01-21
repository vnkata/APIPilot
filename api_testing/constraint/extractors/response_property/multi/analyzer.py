"""
Cross-field response analyzer for detecting relationships between response fields.

Implements 3-step pipeline:
1. Heuristic extraction (deterministic patterns)
2. Coverage check (LLM validates completeness)
3. LLM extraction (for missing relationships)
"""

import json
from typing import List, Optional
from pathlib import Path
from datetime import datetime

from api_testing.models.specification_model import OperationProperties, ItemProperties
from api_testing.constraint.config.settings import CrossFieldAnalyzerSettings
from api_testing.constraint.extractors.common import CandidateConstraint
from api_testing.constraint.extractors.response_property.multi.heuristic_crossfield import (
    ResPropHeuristicCrossFieldExtractor,
)
from api_testing.constraint.extractors.response_property.multi.coverage_checker import (
    ResPropCrossFieldCoverageChecker,
)
from api_testing.constraint.extractors.response_property.multi.llm_extractor import (
    ResPropCrossFieldLLMExtractor,
)
from common.logger import get_logger

logger = get_logger(__name__)


class CrossFieldResponseAnalyzer:
    """Analyzes response schema to detect cross-field constraints.

    Implements 3-step pipeline:
    1. Heuristic extraction - deterministic pattern matching
    2. Coverage check - LLM validates if heuristics are sufficient
    3. LLM extraction - extracts missing relationships with predicate mapping/suggestion
    """

    def __init__(
        self,
        settings: CrossFieldAnalyzerSettings,
        intermediate_dir: Optional[Path] = None,
    ):
        """Initialize analyzer.

        Args:
            settings: CrossFieldAnalyzerSettings instance
            intermediate_dir: Directory for intermediate outputs
        """
        self.logger = logger
        self.settings = settings
        self.intermediate_dir = intermediate_dir

        # Base output dir (operation subfolders created dynamically)
        self.base_output_dir = None
        if self.intermediate_dir:
            self.base_output_dir = self.intermediate_dir / "2_crossfieldresponse"
            self.base_output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize extractors based on settings
        self.heuristic_extractor = (
            ResPropHeuristicCrossFieldExtractor() if self.settings.heuristic else None
        )

        self.coverage_checker = (
            ResPropCrossFieldCoverageChecker() if self.settings.coverage_check else None
        )

        self.llm_extractor = (
            ResPropCrossFieldLLMExtractor() if self.settings.llm_extraction else None
        )

        logger.debug(
            "Initialized CrossFieldResponseAnalyzer",
            settings_enabled=self.settings.enabled,
            heuristic_enabled=self.settings.heuristic,
            coverage_enabled=self.settings.coverage_check,
            llm_enabled=self.settings.llm_extraction,
            has_intermediate_dir=intermediate_dir is not None,
        )

    def _get_operation_output_dir(self, operation_id: str) -> Optional[Path]:
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

    def _save_intermediate(self, operation_id: str, phase_name: str, data, stats: dict):
        """Save intermediate output with metadata wrapper.

        Args:
            operation_id: Operation UUID
            phase_name: Name of the phase (e.g., 'heuristic', 'coverage', 'llm', 'final')
            data: Data to save (auto-serializes Pydantic models)
            stats: Statistics dictionary
        """
        output_dir = self._get_operation_output_dir(operation_id)
        if not output_dir:
            return

        # Serialize Pydantic models to dicts for JSON compatibility (recursive)
        def serialize_value(value):
            """Recursively serialize Pydantic models to dicts."""
            if hasattr(value, "model_dump"):
                return value.model_dump()
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            else:
                return value

        serialized_data = serialize_value(data)

        output = {
            "phase": f"2_{phase_name}",
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

    async def analyze(
        self,
        operation: OperationProperties,
        response_schema: ItemProperties,
    ) -> List[CandidateConstraint]:
        """Analyze response schema for cross-field relationships with intermediate saving.

        Args:
            operation: Operation properties
            response_schema: Full response schema

        Returns:
            List of candidate constraints
        """
        candidates = []

        if not response_schema or not response_schema.properties:
            return candidates

        try:
            # Step 1: Heuristic extraction (if enabled)
            heuristic_candidates = []
            if self.settings.heuristic and self.heuristic_extractor:
                self.logger.debug(
                    "Step 1: Running heuristic cross-field extraction",
                    operation=operation.uuid,
                )

                heuristic_candidates = self.heuristic_extractor.extract(
                    response_schema=response_schema,
                    operation_id=operation.uuid,
                )

                candidates.extend(heuristic_candidates)

                # Save heuristic results
                self._save_intermediate(
                    operation.uuid,
                    "heuristic",
                    [
                        c.model_dump() if hasattr(c, "model_dump") else c.__dict__
                        for c in heuristic_candidates
                    ],
                    {
                        "heuristic_count": len(heuristic_candidates),
                    },
                )

                self.logger.info(
                    f"Heuristic extraction found {len(heuristic_candidates)} cross-field constraints",
                    operation=operation.uuid,
                )
            else:
                self.logger.debug(
                    "Heuristic extraction disabled, skipping",
                    operation=operation.uuid,
                )

            # Step 2: Coverage check (if enabled)
            if self.settings.coverage_check and self.coverage_checker:
                self.logger.debug(
                    "Step 2: Checking coverage with LLM",
                    operation=operation.uuid,
                )

                missing_relationships = await self.coverage_checker.check(
                    response_schema=response_schema,
                    heuristic_results=heuristic_candidates,
                )

                # Save coverage results
                self._save_intermediate(
                    operation.uuid,
                    "coverage",
                    {
                        "missing_relationships": missing_relationships,
                    },
                    {
                        "is_sufficient": (
                            len(missing_relationships) == 0
                            if missing_relationships
                            else True
                        ),
                        "missing_count": (
                            len(missing_relationships) if missing_relationships else 0
                        ),
                    },
                )

                if missing_relationships:
                    self.logger.info(
                        f"Coverage check found {len(missing_relationships)} missing relationships",
                        operation=operation.uuid,
                    )

                    # Step 3: LLM extraction for missing relationships (if enabled)
                    if self.settings.llm_extraction and self.llm_extractor:
                        self.logger.debug(
                            "Step 3: Extracting missing relationships with LLM",
                            operation=operation.uuid,
                        )

                        llm_candidates = await self.llm_extractor.extract(
                            response_schema=response_schema,
                            missing_relationships=missing_relationships,
                            operation_id=operation.uuid,
                        )

                        candidates.extend(llm_candidates)

                        # Save LLM results
                        self._save_intermediate(
                            operation.uuid,
                            "llm",
                            [
                                (
                                    c.model_dump()
                                    if hasattr(c, "model_dump")
                                    else c.__dict__
                                )
                                for c in llm_candidates
                            ],
                            {
                                "llm_count": len(llm_candidates),
                            },
                        )

                        self.logger.info(
                            f"LLM extraction added {len(llm_candidates)} constraints",
                            operation=operation.uuid,
                        )
                else:
                    self.logger.info(
                        "Coverage check: heuristic extraction is complete",
                        operation=operation.uuid,
                    )

            # Save final results
            self._save_intermediate(
                operation.uuid,
                "final",
                [
                    c.model_dump() if hasattr(c, "model_dump") else c.__dict__
                    for c in candidates
                ],
                {
                    "total_constraints": len(candidates),
                    "heuristic_count": len(heuristic_candidates),
                    "llm_count": len(candidates) - len(heuristic_candidates),
                },
            )

            self.logger.info(
                f"Cross-field analysis complete: {len(candidates)} total constraints",
                operation=operation.uuid,
                heuristic=len(heuristic_candidates),
                llm=len(candidates) - len(heuristic_candidates),
            )

            return candidates

        except Exception as e:
            # Save error output
            output_dir = self._get_operation_output_dir(operation.uuid)
            if output_dir:
                error_output = {
                    "phase": "2_error",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "operation_id": operation.uuid,
                    "data": [],
                    "stats": {},
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                error_filepath = output_dir / "error.json"
                try:
                    with open(error_filepath, "w", encoding="utf-8") as f:
                        json.dump(error_output, f, indent=2, ensure_ascii=False)
                except Exception as save_error:
                    logger.error(f"Failed to save error output", error=str(save_error))

            logger.error(
                "Cross-field analysis failed",
                operation=operation.uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


__all__ = ["CrossFieldResponseAnalyzer"]
