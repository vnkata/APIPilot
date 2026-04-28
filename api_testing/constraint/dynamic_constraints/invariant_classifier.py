from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
from dataclasses import asdict
from importlib import resources
from pathlib import Path
import time
from typing import Any, Sequence

from api_testing.constraint.dynamic_constraints.classification.context_parser import (
    InvariantContextParser,
)
from api_testing.constraint.dynamic_constraints.classification.example_extractor import (
    ExampleExtractor,
)
from api_testing.constraint.dynamic_constraints.classification.evidence_checker import (
    ObservedEvidenceAnalysis,
    SpecEnumAnalysis,
    analyze_observed_examples,
    analyze_spec_enum_relationship,
)
from api_testing.constraint.dynamic_constraints.classification.models import (
    ExcerptBuildResult,
    NormalizedInvariantContext,
    ParsedProgramPoint,
    VariableReference,
)
from api_testing.constraint.dynamic_constraints.classification.spec_excerpt_builder import (
    SpecExcerptBuilder,
)
from api_testing.constraint.dynamic_constraints.classified_invariant_reader import (
    CLASSIFIED_INVARIANTS_HEADER,
)
from api_testing.constraint.dynamic_constraints.invariant_reader import (
    InvariantReader,
    InvariantRecord,
)
from api_testing.constraint.dynamic_constraints.test_case import TestCase
from api_testing.constraint.dynamic_constraints.utils.test_case_file_manager import (
    TestCaseFileManager,
)
from api_testing.prompts.invariant_classification import InvariantClassificationPrompt
from api_testing.prompts.invariant_classification.schema import (
    InvariantClassificationResult,
    InvariantClassificationVerdict,
)
from api_testing.utils.log import getLogger


CLASSIFIED_INVARIANTS_FILENAME = "classified_invariants.csv"
DEFAULT_PROMPT_VERSION = "main2-python-v1"
DEFAULT_MAX_EXAMPLES = 5


class InvariantClassifier:
    """Classify Daikon invariants with LLM-backed API contract context.

    Inputs are the parsed OpenAPI operations, an LLM model exposing
    ``generate(...)`` and ``get_model_name()``, and a cache directory containing
    ``invariants.csv`` plus optional ``test_cases.json``. The main output is
    ``classified_invariants.csv``; optional debug JSON files include prompt
    context, selected schema paths, examples, and model results.
    """

    def __init__(
        self,
        *,
        spec_parser,
        model,
        cache_dir: str | Path | None = None,
        prompt_version: str = DEFAULT_PROMPT_VERSION,
        max_examples: int = DEFAULT_MAX_EXAMPLES,
    ) -> None:
        if not spec_parser or not hasattr(spec_parser, "operations"):
            raise ValueError("spec_parser with operations is required")

        self.spec_parser = spec_parser
        self.operations = spec_parser.operations or {}
        self.model = model
        self.cache_dir = Path(cache_dir or ".")
        self.prompt_version = prompt_version
        self.max_examples = max_examples
        self.logger = getLogger(__name__)
        self.prompt = InvariantClassificationPrompt(model) if model is not None else None
        self._test_case_cache: list[TestCase] | None = None
        self._invariant_kinds = self._load_invariant_kinds()

        self.context_parser = InvariantContextParser(self.operations, self._invariant_kinds)
        self.spec_excerpt_builder = SpecExcerptBuilder()
        self.example_extractor = ExampleExtractor(max_examples=max_examples)

    def classify_invariants(
        self,
        input_path: str | Path | None = None,
        output_path: str | Path | None = None,
        *,
        persist_debug_artifacts: bool = False,
        resume: bool = False,
        max_workers: int = 1,
        max_rows: int | None = None,
        summary_json_path: str | Path | None = None,
        summary_csv_path: str | Path | None = None,
    ) -> Path:
        """Classify invariants and write ``classified_invariants.csv``.

        Raises a clear runtime error when the configured model does not expose
        the required LLM methods. Per-invariant failures are written as
        ``inconclusive`` rows so one bad invariant does not stop the batch.
        """
        self._validate_model()

        reader = InvariantReader(cache_dir=self.cache_dir)
        input_file = Path(input_path) if input_path is not None else self.cache_dir / "invariants.csv"
        output_file = (
            Path(output_path)
            if output_path is not None
            else self.cache_dir / CLASSIFIED_INVARIANTS_FILENAME
        )
        output_file.parent.mkdir(parents=True, exist_ok=True)

        records = reader.read_invariants(input_file)
        if max_rows is not None:
            if max_rows < 1:
                raise ValueError("max_rows must be >= 1 when provided.")
            records = records[:max_rows]

        test_cases = self._load_test_cases()
        approx_number_of_operations = len(test_cases)
        model_name = self.model.get_model_name()
        debug_dir = self.cache_dir / "classification_debug" if persist_debug_artifacts else None
        if debug_dir is not None:
            debug_dir.mkdir(parents=True, exist_ok=True)

        completed_rows = (
            self._read_completed_rows(output_file)
            if resume and output_file.exists()
            else {}
        )
        result_rows_by_index: dict[int, list[str]] = {}
        summary_entries_by_index: dict[int, dict[str, Any]] = {}
        records_to_process: list[tuple[int, InvariantRecord]] = []

        for index, record in enumerate(records, start=1):
            row_key = self._row_key_from_record(record)
            completed_row = completed_rows.get(row_key)
            if completed_row is not None:
                result_rows_by_index[index] = completed_row
                summary_entries_by_index[index] = self._summary_entry_from_row(
                    index=index,
                    row_key=row_key,
                    row=completed_row,
                    status="skipped",
                    duration_seconds=0.0,
                )
                continue
            records_to_process.append((index, record))

        started_at = datetime.now(timezone.utc)
        interrupted = False
        worker_count = max(1, int(max_workers or 1))

        try:
            if worker_count == 1:
                for index, record in records_to_process:
                    row_index, row, summary_entry = self._classify_record(
                        index=index,
                        record=record,
                        test_cases=test_cases,
                        approx_number_of_operations=approx_number_of_operations,
                        model_name=model_name,
                        debug_dir=debug_dir,
                        log_debug=persist_debug_artifacts,
                    )
                    result_rows_by_index[row_index] = row
                    summary_entries_by_index[row_index] = summary_entry
            else:
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    futures = [
                        executor.submit(
                            self._classify_record,
                            index=index,
                            record=record,
                            test_cases=test_cases,
                            approx_number_of_operations=approx_number_of_operations,
                            model_name=model_name,
                            debug_dir=debug_dir,
                            log_debug=persist_debug_artifacts,
                        )
                        for index, record in records_to_process
                    ]
                    for future in as_completed(futures):
                        row_index, row, summary_entry = future.result()
                        result_rows_by_index[row_index] = row
                        summary_entries_by_index[row_index] = summary_entry
        except KeyboardInterrupt:
            interrupted = True
            self.logger.warning(
                "Invariant classification interrupted. Persisting %d completed row(s).",
                len(result_rows_by_index),
            )
            raise
        finally:
            ordered_indexes = sorted(result_rows_by_index)
            rows = [result_rows_by_index[index] for index in ordered_indexes]
            summary_entries = [
                summary_entries_by_index[index]
                for index in sorted(summary_entries_by_index)
            ]
            self._write_rows(output_file, rows)
            self._write_summary_artifacts(
                summary_json_path=Path(summary_json_path) if summary_json_path else None,
                summary_csv_path=Path(summary_csv_path) if summary_csv_path else None,
                entries=summary_entries,
                total_records=len(records),
                skipped_records=sum(1 for entry in summary_entries if entry["status"] == "skipped"),
                processed_records=sum(1 for entry in summary_entries if entry["status"] != "skipped"),
                model_name=model_name,
                prompt_version=self.prompt_version,
                max_workers=worker_count,
                input_path=input_file,
                output_path=output_file,
                debug_dir=debug_dir,
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                interrupted=interrupted,
            )

        counts = Counter(row[5] for row in result_rows_by_index.values())

        self.logger.info(
            (
                "Classified %d invariant(s) into %s "
                "(true-positive=%d, false-positive=%d, inconclusive=%d)"
            ),
            len(result_rows_by_index),
            output_file,
            counts.get(InvariantClassificationVerdict.TRUE_POSITIVE.value, 0),
            counts.get(InvariantClassificationVerdict.FALSE_POSITIVE.value, 0),
            counts.get(InvariantClassificationVerdict.INCONCLUSIVE.value, 0),
        )
        return output_file

    def _classify_record(
        self,
        *,
        index: int,
        record: InvariantRecord,
        test_cases: Sequence[TestCase],
        approx_number_of_operations: int,
        model_name: str,
        debug_dir: Path | None,
        log_debug: bool,
    ) -> tuple[int, list[str], dict[str, Any]]:
        started = time.perf_counter()
        row_key = self._row_key_from_record(record)
        status = "success"
        examples_count = 0
        debug_payload: dict[str, Any] = {
            "row_index": index,
            "row_key": row_key,
            "status": status,
            "record": {
                "pptname": record.pptname,
                "invariant": record.invariant,
                "invariant_type": record.invariant_type,
                "variables": record.variables,
                "postman_assertion": record.postman_assertion,
            },
        }

        try:
            context = self._normalize_invariant(record)
            debug_payload["normalized_context"] = self._context_to_debug_dict(context)

            excerpt_result = self._build_spec_excerpt_result(context)
            spec_excerpt = excerpt_result.excerpt
            debug_payload["spec_excerpt"] = spec_excerpt
            debug_payload["spec_excerpt_debug"] = self._excerpt_debug_to_dict(excerpt_result)

            examples = self._extract_examples(context, test_cases)
            examples_count = len(examples)
            debug_payload["examples"] = list(examples)
            observed_evidence = analyze_observed_examples(record.invariant, examples)
            spec_enum_evidence = analyze_spec_enum_relationship(record.invariant, spec_excerpt)
            debug_payload["observed_evidence"] = observed_evidence.to_debug_dict()
            debug_payload["spec_enum_evidence"] = spec_enum_evidence.to_debug_dict()
            result = self.prompt.exec(
                invariant=record.invariant,
                invariant_type=record.invariant_type,
                invariant_description=context.invariant_description,
                program_point=context.parsed_program_point.program_point,
                response_container_path=context.parsed_program_point.response_container_path,
                spec_excerpt=spec_excerpt,
                examples=examples,
                approx_number_of_operations=approx_number_of_operations,
                evidence_checks=[
                    observed_evidence.summary,
                    spec_enum_evidence.summary,
                ],
                log_debug=log_debug,
            )
            result, correction = self._apply_deterministic_corrections(
                result=result,
                context=context,
                observed_evidence=observed_evidence,
                spec_enum_evidence=spec_enum_evidence,
            )
            if correction is not None:
                debug_payload["deterministic_correction"] = correction
            verdict = result.verdict.value
            confidence = float(result.confidence)
            reason = result.reason
            debug_payload["result"] = result.model_dump()
        except Exception as exc:
            self.logger.warning(
                "Invariant classification fell back to inconclusive for %s: %s",
                record.pptname,
                exc,
            )
            status = "error"
            verdict = InvariantClassificationVerdict.INCONCLUSIVE.value
            confidence = 0.0
            reason = f"{type(exc).__name__}: {exc}"
            debug_payload["error"] = reason

        duration_seconds = time.perf_counter() - started
        debug_payload["status"] = status
        debug_payload["duration_seconds"] = round(duration_seconds, 6)

        row = [
            record.pptname,
            record.invariant,
            record.invariant_type,
            record.variables,
            record.postman_assertion,
            verdict,
            f"{confidence:.4f}",
            reason,
            model_name,
            self.prompt_version,
            str(examples_count),
            str(approx_number_of_operations),
        ]

        if debug_dir is not None:
            debug_path = debug_dir / f"{index:04d}.json"
            debug_path.write_text(
                json.dumps(debug_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        summary_entry = self._summary_entry_from_row(
            index=index,
            row_key=row_key,
            row=row,
            status=status,
            duration_seconds=duration_seconds,
        )
        return index, row, summary_entry

    def _normalize_invariant(self, record: InvariantRecord) -> NormalizedInvariantContext:
        return self.context_parser.normalize_record(record)

    def _parse_pptname(self, pptname: str) -> ParsedProgramPoint:
        return self.context_parser.parse_program_point(pptname)

    def _parse_variables(self, raw_variables: str) -> tuple[VariableReference, ...]:
        return self.context_parser.parse_variables(raw_variables)

    def _build_spec_excerpt(self, context: NormalizedInvariantContext) -> str:
        return self._build_spec_excerpt_result(context).excerpt

    def _build_spec_excerpt_result(self, context: NormalizedInvariantContext) -> ExcerptBuildResult:
        return self.spec_excerpt_builder.build_with_debug(context)

    def _extract_examples(
        self,
        context: NormalizedInvariantContext,
        test_cases: Sequence[TestCase],
    ) -> list[str]:
        return self.example_extractor.extract_examples(context, test_cases)

    @staticmethod
    def _apply_deterministic_corrections(
        *,
        result: InvariantClassificationResult,
        context: NormalizedInvariantContext,
        observed_evidence: ObservedEvidenceAnalysis,
        spec_enum_evidence: SpecEnumAnalysis,
    ) -> tuple[InvariantClassificationResult, dict[str, Any] | None]:
        """Correct narrow cases where deterministic evidence contradicts LLM output."""
        if spec_enum_evidence.status == "exact":
            corrected = InvariantClassificationResult(
                verdict=InvariantClassificationVerdict.TRUE_POSITIVE,
                confidence=max(float(result.confidence), 0.9),
                reason=(
                    "Deterministic spec check: the invariant values match the "
                    "documented enum, and observed examples do not contradict it."
                ),
            )
            return corrected, {
                "type": "spec_enum_exact_match",
                "previous_result": result.model_dump(),
            }

        if spec_enum_evidence.status == "subset":
            corrected = InvariantClassificationResult(
                verdict=InvariantClassificationVerdict.FALSE_POSITIVE,
                confidence=max(float(result.confidence), 0.8),
                reason=(
                    "Deterministic spec check: the invariant is narrower than the "
                    f"documented enum. {spec_enum_evidence.summary}"
                ),
            )
            return corrected, {
                "type": "spec_enum_subset",
                "previous_result": result.model_dump(),
            }

        if spec_enum_evidence.status == "conflict":
            corrected = InvariantClassificationResult(
                verdict=InvariantClassificationVerdict.FALSE_POSITIVE,
                confidence=max(float(result.confidence), 0.85),
                reason=(
                    "Deterministic spec check: the invariant contains value(s) outside "
                    f"the documented enum. {spec_enum_evidence.summary}"
                ),
            )
            return corrected, {
                "type": "spec_enum_conflict",
                "previous_result": result.model_dump(),
            }

        if observed_evidence.status != "evaluated":
            return result, None

        if observed_evidence.contradiction_count > 0:
            corrected = InvariantClassificationResult(
                verdict=InvariantClassificationVerdict.FALSE_POSITIVE,
                confidence=max(float(result.confidence), 0.85),
                reason=(
                    "Deterministic observed-evidence check: "
                    f"{observed_evidence.contradiction_count} observed example(s) "
                    "contradict the invariant. "
                    f"Example: {observed_evidence.contradiction_examples[0]}"
                ),
            )
            return corrected, {
                "type": "observed_example_contradiction",
                "previous_result": result.model_dump(),
            }

        if (
            result.verdict == InvariantClassificationVerdict.FALSE_POSITIVE
            and observed_evidence.support_count > 0
            and observed_evidence.contradiction_count == 0
            and InvariantClassifier._reason_claims_observed_contradiction(result.reason)
        ):
            if context.input_variables and not context.output_variables:
                corrected = InvariantClassificationResult(
                    verdict=InvariantClassificationVerdict.FALSE_POSITIVE,
                    confidence=min(max(float(result.confidence), 0.7), 0.85),
                    reason=(
                        "Deterministic observed-evidence check: the recovered examples "
                        "satisfy this request-only invariant, but the API contract does "
                        "not document this relationship, so it is likely an overfit input "
                        "correlation."
                    ),
                )
            else:
                corrected = InvariantClassificationResult(
                    verdict=InvariantClassificationVerdict.TRUE_POSITIVE,
                    confidence=max(float(result.confidence), 0.85),
                    reason=(
                        "Deterministic observed-evidence check: all evaluated examples "
                        "satisfy the invariant and no observed contradiction was found."
                    ),
                )
            return corrected, {
                "type": "removed_impossible_observed_contradiction",
                "previous_result": result.model_dump(),
            }

        return result, None

    @staticmethod
    def _reason_claims_observed_contradiction(reason: str) -> bool:
        normalized = reason.lower()
        has_observed_reference = (
            "observed" in normalized
            or "example" in normalized
            or "examples" in normalized
            or "presence of" in normalized
        )
        has_contradiction_language = (
            "contradict" in normalized
            or "not support" in normalized
            or "unsupported by" in normalized
            or "less than" in normalized
            or "greater than" in normalized
            or "larger" in normalized
            or "negative" in normalized
            or "positive" in normalized
            or "equal" in normalized
            or "substring" in normalized
        )
        return has_observed_reference and has_contradiction_language

    def _load_test_cases(self) -> list[TestCase]:
        if self._test_case_cache is not None:
            return self._test_case_cache

        file_manager = TestCaseFileManager(cache_dir=str(self.cache_dir))
        test_cases_path = self.cache_dir / "test_cases.json"
        if test_cases_path.exists():
            self._test_case_cache = file_manager.load_test_cases(test_cases_path)
            return self._test_case_cache

        history_dir = self.cache_dir / "history"
        if history_dir.exists():
            self._test_case_cache = file_manager.parse_test_cases_from_history()
            return self._test_case_cache

        self._test_case_cache = []
        return self._test_case_cache

    def _validate_model(self) -> None:
        if self.model is None:
            raise RuntimeError("DynamicConstraintMiner.model is required to classify invariants.")
        if not hasattr(self.model, "generate"):
            raise RuntimeError("The configured model must expose a generate(...) method.")
        if not hasattr(self.model, "get_model_name"):
            raise RuntimeError("The configured model must expose a get_model_name() method.")
        if self.prompt is None:
            self.prompt = InvariantClassificationPrompt(self.model)

    @staticmethod
    def _context_to_debug_dict(context: NormalizedInvariantContext) -> dict[str, Any]:
        return {
            "parsed_program_point": {
                "operation_key": context.parsed_program_point.operation_key,
                "http_method": context.parsed_program_point.http_method,
                "endpoint_path": context.parsed_program_point.endpoint_path,
                "status_code": context.parsed_program_point.status_code,
                "program_point": context.parsed_program_point.program_point,
                "response_container_path": context.parsed_program_point.response_container_path,
            },
            "input_variables": [InvariantClassifier._variable_to_debug_dict(var) for var in context.input_variables],
            "output_variables": [InvariantClassifier._variable_to_debug_dict(var) for var in context.output_variables],
            "invariant_description": context.invariant_description,
        }

    @staticmethod
    def _variable_to_debug_dict(variable: VariableReference) -> dict[str, Any]:
        return {
            "raw": variable.raw,
            "role": variable.role,
            "is_size": variable.is_size,
            "display_path": variable.display_path,
            "path_segments": [asdict(segment) for segment in variable.path_segments],
        }

    @staticmethod
    def _excerpt_debug_to_dict(excerpt_result: ExcerptBuildResult) -> dict[str, Any]:
        return {
            "shape": excerpt_result.shape,
            "budget_profile": asdict(excerpt_result.budget_profile),
            "matched_schema_paths": [
                asdict(matched_path)
                for matched_path in excerpt_result.matched_schema_paths
            ],
        }

    @classmethod
    def _read_completed_rows(cls, output_file: Path) -> dict[str, list[str]]:
        completed: dict[str, list[str]] = {}
        try:
            with output_file.open("r", encoding="utf-8", newline="") as classified_file:
                header_line = classified_file.readline().rstrip("\r\n")
                if header_line != CLASSIFIED_INVARIANTS_HEADER:
                    return completed

                reader = csv.reader(classified_file, delimiter=";")
                for row in reader:
                    if len(row) < 12:
                        continue
                    row_key = cls._row_key_from_values(row[:5])
                    completed[row_key] = row[:12]
        except OSError:
            return completed
        return completed

    @classmethod
    def _row_key_from_record(cls, record: InvariantRecord) -> str:
        return cls._row_key_from_values(
            [
                record.pptname,
                record.invariant,
                record.invariant_type,
                record.variables,
                record.postman_assertion,
            ]
        )

    @staticmethod
    def _row_key_from_values(values: Sequence[str]) -> str:
        payload = "\x1f".join(values[:5])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _summary_entry_from_row(
        *,
        index: int,
        row_key: str,
        row: Sequence[str],
        status: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        normalized_row = list(row) + [""] * max(0, 12 - len(row))
        confidence_text = normalized_row[6] or "0.0"
        try:
            confidence = float(confidence_text)
        except ValueError:
            confidence = 0.0
        return {
            "row_index": index,
            "row_key": row_key,
            "status": status,
            "pptname": normalized_row[0],
            "invariant": normalized_row[1],
            "invariant_type": normalized_row[2],
            "verdict": normalized_row[5],
            "confidence": confidence,
            "reason": normalized_row[7],
            "model": normalized_row[8],
            "prompt_version": normalized_row[9],
            "examples_count": int(normalized_row[10] or 0),
            "approx_number_of_operations": int(normalized_row[11] or 0),
            "duration_seconds": round(duration_seconds, 6),
        }

    @staticmethod
    def _write_summary_artifacts(
        *,
        summary_json_path: Path | None,
        summary_csv_path: Path | None,
        entries: Sequence[dict[str, Any]],
        total_records: int,
        skipped_records: int,
        processed_records: int,
        model_name: str,
        prompt_version: str,
        max_workers: int,
        input_path: Path,
        output_path: Path,
        debug_dir: Path | None,
        started_at: datetime,
        finished_at: datetime,
        interrupted: bool,
    ) -> None:
        if summary_json_path is None and summary_csv_path is None:
            return

        verdict_counts = Counter(str(entry.get("verdict", "")) for entry in entries)
        status_counts = Counter(str(entry.get("status", "")) for entry in entries)
        technical_failures = [
            entry
            for entry in entries
            if entry.get("status") == "error"
        ]
        low_confidence = [
            entry
            for entry in entries
            if float(entry.get("confidence", 0.0)) <= 0.5
        ]

        if summary_json_path is not None:
            summary_json_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "total_records": total_records,
                "completed_records": len(entries),
                "skipped_records": skipped_records,
                "processed_records": processed_records,
                "interrupted": interrupted,
                "verdict_counts": dict(verdict_counts),
                "status_counts": dict(status_counts),
                "technical_failure_count": len(technical_failures),
                "low_confidence_count": len(low_confidence),
                "technical_failures": technical_failures,
                "low_confidence_rows": low_confidence,
                "model": model_name,
                "prompt_version": prompt_version,
                "max_workers": max_workers,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "debug_dir": str(debug_dir) if debug_dir is not None else None,
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_seconds": round((finished_at - started_at).total_seconds(), 6),
            }
            summary_json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if summary_csv_path is not None:
            summary_csv_path.parent.mkdir(parents=True, exist_ok=True)
            fieldnames = [
                "row_index",
                "row_key",
                "status",
                "pptname",
                "invariant",
                "invariant_type",
                "verdict",
                "confidence",
                "reason",
                "model",
                "prompt_version",
                "examples_count",
                "approx_number_of_operations",
                "duration_seconds",
            ]
            with summary_csv_path.open("w", encoding="utf-8", newline="") as summary_file:
                writer = csv.DictWriter(summary_file, fieldnames=fieldnames)
                writer.writeheader()
                for entry in entries:
                    writer.writerow({field: entry.get(field, "") for field in fieldnames})

    @staticmethod
    def _write_rows(output_file: Path, rows: Sequence[Sequence[str]]) -> None:
        with output_file.open("w", encoding="utf-8", newline="") as classified_file:
            writer = csv.writer(classified_file, delimiter=";")
            classified_file.write(CLASSIFIED_INVARIANTS_HEADER + "\n")
            writer.writerows(rows)

    @staticmethod
    def _load_invariant_kinds() -> dict[str, str]:
        resource_text = resources.files(
            "api_testing.constraint.dynamic_constraints.resources"
        ).joinpath("invariant_kinds.txt").read_text(encoding="utf-8")

        invariant_kinds: dict[str, str] = {}
        for raw_line in resource_text.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            invariant_type, _, description = line.partition(":")
            invariant_kinds[invariant_type.strip()] = description.strip()
        return invariant_kinds


def main() -> None:
    """Print practical usage snippets without loading secrets or calling an LLM."""
    usage = {
        "purpose": "Classify Daikon invariants from an existing cache_dir/invariants.csv.",
        "safe_default": "This demo only prints usage. It does not instantiate OpenAIModel or call an LLM.",
        "minimal_flow": [
            "spec = SpecificationParser(spec_path='datasets/Bills-api.json')",
            "spec.parse_specification()",
            "model = OpenAIModel(model='gpt-4.1-mini')",
            "classifier = InvariantClassifier(spec_parser=spec, model=model, cache_dir='.cache/Bills API_3')",
            "classifier.classify_invariants(persist_debug_artifacts=True)",
        ],
        "artifact": str(Path("cache_dir") / CLASSIFIED_INVARIANTS_FILENAME),
        "debug_artifacts": str(Path("cache_dir") / "classification_debug" / "0001.json"),
    }
    print(json.dumps(usage, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
