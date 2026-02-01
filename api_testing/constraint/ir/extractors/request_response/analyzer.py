"""
Request-Response Analyzer orchestrating heuristic extractors and LLM fallback.

Implements 3-step pipeline:
1. Heuristic extraction (deterministic patterns)
2. Coverage check (identify unmatched parameters)
3. LLM extraction (for unmatched parameters)
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from api_testing.constraint.ir.config.settings import RequestResponseAnalyzerSettings
from api_testing.constraint.ir.extractors.common import CandidateConstraint
from api_testing.constraint.ir.extractors.request_response.coverage_checker import (
    RequestResponseCoverageChecker,
)
from api_testing.constraint.ir.extractors.request_response.heuristics import (
    EchoIdentityExtractor,
    FilterExtractor,
    PaginationExtractor,
    ProjectionExpandExtractor,
    RangeExtractor,
    SearchExtractor,
    SortExtractor,
)
from api_testing.constraint.ir.extractors.request_response.llm import (
    RequestResponseLLMExtractor,
)
from api_testing.models.specification_model import OperationProperties
from common.logger import get_logger

logger = get_logger(__name__)


class RequestResponseAnalyzer:
    """Orchestrates request-response constraint extraction.

    Implements 3-step pipeline:
    1. Heuristic extraction - deterministic pattern matching
    2. Coverage check - identify unmatched parameters
    3. LLM extraction - extract constraints for unmatched parameters
    """

    def __init__(
        self,
        settings: RequestResponseAnalyzerSettings,
        intermediate_dir: Path | None = None,
    ):
        """Initialize analyzer.

        Args:
            settings: RequestResponseAnalyzerSettings instance
            intermediate_dir: Directory for intermediate outputs
        """
        self.settings = settings
        self.intermediate_dir = intermediate_dir

        # Base output dir (operation subfolders created dynamically)
        self.base_output_dir = None
        if self.intermediate_dir:
            self.base_output_dir = self.intermediate_dir / "3_requestresponse"
            self.base_output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize heuristic extractors in priority order (if heuristic enabled)
        if self.settings.heuristic:
            self.extractors = [
                EchoIdentityExtractor(),  # Highest confidence - exact matching
                FilterExtractor(),  # High confidence - array filtering
                PaginationExtractor(),  # High confidence - well-defined patterns
                RangeExtractor(),  # High confidence - paired parameters
                SortExtractor(),  # Medium confidence - requires parsing
                ProjectionExpandExtractor(),  # Medium confidence - conditional
                SearchExtractor(),  # Lowest confidence - fuzzy semantics
            ]
        else:
            self.extractors = []

        # Initialize coverage checker and LLM extractor based on settings
        self.coverage_checker = (
            RequestResponseCoverageChecker() if self.settings.coverage_check else None
        )

        self.llm_extractor = (
            RequestResponseLLMExtractor() if self.settings.llm_extraction else None
        )

        self.logger = logger

        logger.debug(
            "Initialized RequestResponseAnalyzer",
            settings_enabled=self.settings.enabled,
            heuristic_enabled=self.settings.heuristic,
            coverage_enabled=self.settings.coverage_check,
            llm_enabled=self.settings.llm_extraction,
            has_intermediate_dir=intermediate_dir is not None,
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
            "phase": f"3_{phase_name}",
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
    ) -> list[CandidateConstraint]:
        """Analyze operation for request-response constraints with intermediate saving.

        Args:
            operation: Operation to analyze

        Returns:
            List of candidate constraints
        """
        all_candidates = []

        # Get response schema once
        response_schema = operation.get_success_response_schema()

        if not response_schema:
            self.logger.debug(
                f"No success response schema for operation {operation.operation_id if hasattr(operation, 'operation_id') else 'unknown'}"
            )
            return []

        try:
            # Step 1: Heuristic extraction (if enabled)
            heuristic_candidates = []
            if self.settings.heuristic and self.extractors:
                self.logger.debug(
                    "Step 1: Running heuristic request-response extraction",
                    operation=operation.uuid,
                )

                extractor_results = {}
                for extractor in self.extractors:
                    try:
                        candidates = extractor.extract(operation, response_schema)

                        if candidates:
                            self.logger.debug(
                                f"{extractor.name} found {len(candidates)} candidates",
                                operation=(
                                    operation.operation_id
                                    if hasattr(operation, "operation_id")
                                    else "unknown"
                                ),
                            )
                            all_candidates.extend(candidates)
                            extractor_results[extractor.name] = len(candidates)

                    except Exception as e:
                        self.logger.error(
                            f"Error in {extractor.name}: {e}",
                            exc_info=True,
                            operation=(
                                operation.operation_id
                                if hasattr(operation, "operation_id")
                                else "unknown"
                            ),
                        )
                        continue

                # Deduplicate and merge candidates
                heuristic_candidates = self._deduplicate_candidates(all_candidates)

                # Save heuristic results
                self._save_intermediate(
                    operation.uuid,
                    "heuristic",
                    [
                        c.model_dump() if hasattr(c, "model_dump") else c.__dict__
                        for c in heuristic_candidates
                    ],
                    {
                        "total_raw_candidates": len(all_candidates),
                        "deduplicated_candidates": len(heuristic_candidates),
                        "extractor_results": extractor_results,
                    },
                )

                self.logger.info(
                    f"Heuristic extraction: {len(all_candidates)} candidates → {len(heuristic_candidates)} after deduplication",
                    operation=(
                        operation.operation_id
                        if hasattr(operation, "operation_id")
                        else "unknown"
                    ),
                )
            else:
                self.logger.debug(
                    "Heuristic extraction disabled, skipping",
                    operation=operation.uuid,
                )

            # Step 2: Coverage check - find unmatched parameters (if enabled)
            if self.settings.coverage_check and self.coverage_checker:
                self.logger.debug(
                    "Step 2: Checking for unmatched parameters",
                    operation=operation.uuid,
                )

                unmatched_params = self.coverage_checker.find_unmatched_parameters(
                    operation, heuristic_candidates
                )

                # Save coverage results
                self._save_intermediate(
                    operation.uuid,
                    "coverage",
                    {
                        "unmatched_params": unmatched_params,
                    },
                    {
                        "unmatched_count": (
                            len(unmatched_params) if unmatched_params else 0
                        ),
                        "is_complete": (
                            len(unmatched_params) == 0 if unmatched_params else True
                        ),
                    },
                )

                # Step 3: LLM extraction for unmatched parameters (if enabled)
                if (
                    self.settings.llm_extraction
                    and unmatched_params
                    and self.llm_extractor
                ):
                    self.logger.debug(
                        f"Step 3: Extracting constraints for {len(unmatched_params)} unmatched parameters with LLM",
                        operation=operation.uuid,
                    )

                    llm_candidates = await self.llm_extractor.extract(
                        operation, unmatched_params
                    )

                    if llm_candidates:
                        self.logger.info(
                            f"LLM extraction added {len(llm_candidates)} constraints",
                            operation=operation.uuid,
                        )
                        all_candidates.extend(llm_candidates)

                        # Re-deduplicate with LLM candidates
                        heuristic_candidates = self._deduplicate_candidates(
                            all_candidates
                        )

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

            # Save final results
            self._save_intermediate(
                operation.uuid,
                "final",
                [
                    c.model_dump() if hasattr(c, "model_dump") else c.__dict__
                    for c in heuristic_candidates
                ],
                {
                    "total_constraints": len(heuristic_candidates),
                    "heuristic_count": len(
                        [
                            c
                            for c in heuristic_candidates
                            if not hasattr(c, "source") or c.source != "llm"
                        ]
                    ),
                    "llm_count": len(
                        [
                            c
                            for c in heuristic_candidates
                            if hasattr(c, "source") and c.source == "llm"
                        ]
                    ),
                },
            )

            self.logger.info(
                f"Request-response analysis complete: {len(heuristic_candidates)} total constraints",
                operation=operation.uuid,
            )

            return heuristic_candidates

        except Exception as e:
            # Save error output
            output_dir = self._get_operation_output_dir(operation.uuid)
            if output_dir:
                error_output = {
                    "phase": "3_error",
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
                    logger.error("Failed to save error output", error=str(save_error))

            logger.error(
                "Request-response analysis failed",
                operation=operation.uuid,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def _deduplicate_candidates(
        self,
        candidates: list[CandidateConstraint],
    ) -> list[CandidateConstraint]:
        """Deduplicate and merge candidate constraints.

        Args:
            candidates: List of candidate constraints

        Returns:
            Deduplicated list
        """
        if not candidates:
            return []

        # Group by canonical key
        groups: dict[str, list[CandidateConstraint]] = defaultdict(list)

        for candidate in candidates:
            key = candidate.canonical_key()
            groups[key].append(candidate)

        # Merge candidates in each group
        merged = []

        for key, group in groups.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Merge all candidates in group
                base = group[0]
                for other in group[1:]:
                    base.merge_with(other)
                merged.append(base)

        # Sort by confidence (highest first)
        merged.sort(key=lambda c: c.confidence, reverse=True)

        return merged


__all__ = ["RequestResponseAnalyzer"]
