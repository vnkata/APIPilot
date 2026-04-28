
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from api_testing.constraint.dynamic_constraints.decls_file import Comparability, DeclsFile
from api_testing.constraint.dynamic_constraints.invariant_classifier import (
    CLASSIFIED_INVARIANTS_FILENAME as DEFAULT_CLASSIFIED_INVARIANTS_FILENAME,
    InvariantClassifier,
)
from api_testing.constraint.dynamic_constraints.invariant_extractor import InvariantExtractor
from api_testing.constraint.dynamic_constraints.test_case import TestCase
from api_testing.constraint.dynamic_constraints.utils.test_case_file_manager import TestCaseFileManager
from api_testing.utils.log import getLogger


class DynamicConstraintMiner:
    """Dynamic constraint miner that maps API spec operations to Daikon .decls/.dtrace."""

    DECLS_FILENAME = "test_cases.decls"
    DTRACE_FILENAME = "test_cases.dtrace"
    INVARIANTS_FILENAME = "invariants.csv"
    CLASSIFIED_INVARIANTS_FILENAME = DEFAULT_CLASSIFIED_INVARIANTS_FILENAME

    def __init__(self, spec_parser=None, model=None, cache_dir=None):
        self.spec_parser = spec_parser
        self.model = model
        self.cache_dir = Path(cache_dir or '.')
        self.cache_file = self.cache_dir / "dynamic_constraint_miner.json"
        self.logger = getLogger(__name__)

        if not self.spec_parser or not hasattr(self.spec_parser, "operations"):
            raise ValueError("spec_parser with operations is required")

        self.operations = self.spec_parser.operations
        self.decls_file: Optional[DeclsFile] = None

    def _cache_path(self, filename: str) -> Path:
        """Return an artifact path inside the miner cache directory."""
        return self.cache_dir / filename

    def extract_decls_classes(self) -> DeclsFile:
        """Parse operations from spec_parser into DeclsFile."""
        self.decls_file = DeclsFile(
            version=2.0,
            comparability=Comparability.IMPLICIT,
            spec_parser=self.spec_parser,
            cache_dir=self.cache_dir
        )

        # Existing API path conversion logic in DeclsFile
        self.decls_file.parse_operations()
        self.save_decls_file(self._cache_path(self.DECLS_FILENAME))
        return self.decls_file

    def save_decls_file(self, output_path: str | Path) -> None:
        """Persist DeclsFile to disk in Daikon .decls format."""
        if not self.decls_file:
            raise RuntimeError("DeclsFile is not generated. Call extract_decls_classes() first.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            # Input header lines for compatibility with Daikon
            f.write(str(self.decls_file))

        self.logger.info(f"Wrote declarations to {output_path}")

    def extract_dtraces(self):
        testcase = TestCaseFileManager(cache_dir=self.cache_dir)
        test_cases = testcase.parse_test_cases_from_history()
        testcase.save_test_cases()
        self.generate_dtrace_file(test_cases, self._cache_path(self.DTRACE_FILENAME))

    def extract_invariants(self, output_path: str | Path | None = None) -> Path:
        """Run Daikon to extract invariants from generated decls and dtrace files."""
        decls_path = self._cache_path(self.DECLS_FILENAME)
        dtrace_path = self._cache_path(self.DTRACE_FILENAME)

        missing_files = [path for path in (decls_path, dtrace_path) if not path.exists()]
        if missing_files:
            missing_paths = ", ".join(str(path) for path in missing_files)
            raise FileNotFoundError(
                "Missing required instrumentation files: "
                f"{missing_paths}. Call extract_decls_classes() and extract_dtraces() first."
            )

        extractor = InvariantExtractor(cache_dir=self.cache_dir)
        return extractor.extract_invariants(
            decls_path=decls_path,
            dtrace_path=dtrace_path,
            output_path=output_path,
        )

    def mine_dynamic_constraints(self) -> Dict[str, Path]:
        """Run the full dynamic mining workflow and return generated artifact paths."""
        self.extract_decls_classes()
        self.extract_dtraces()
        invariants_path = self.extract_invariants()

        return {
            "decls_path": self._cache_path(self.DECLS_FILENAME),
            "dtrace_path": self._cache_path(self.DTRACE_FILENAME),
            "invariants_path": invariants_path,
        }

    def classify_invariants(
        self,
        output_path: str | Path | None = None,
        *,
        persist_debug_artifacts: bool = False,
    ) -> Path:
        """Classify an existing ``invariants.csv`` artifact.

        Preconditions:
        - ``extract_invariants()`` has already produced ``cache_dir/invariants.csv``.
        - ``self.model`` implements the LLM interface expected by
          ``InvariantClassifier``.

        Returns the path to ``classified_invariants.csv``. Per-row classifier
        failures are handled by the classifier as ``inconclusive`` rows.
        """
        invariants_path = self._cache_path(self.INVARIANTS_FILENAME)
        if not invariants_path.exists():
            raise FileNotFoundError(
                f"Missing invariants file: {invariants_path}. Call extract_invariants() first."
            )
        if self.model is None:
            raise RuntimeError("DynamicConstraintMiner.model is required to classify invariants.")

        classifier = InvariantClassifier(
            spec_parser=self.spec_parser,
            model=self.model,
            cache_dir=self.cache_dir,
        )
        return classifier.classify_invariants(
            input_path=invariants_path,
            output_path=output_path,
            persist_debug_artifacts=persist_debug_artifacts,
        )

    def mine_and_classify_dynamic_constraints(
        self,
        *,
        persist_debug_artifacts: bool = False,
    ) -> Dict[str, Path]:
        """Run mining and then classify the mined invariants.

        The legacy ``mine_dynamic_constraints()`` behavior is unchanged; this
        method is the explicit end-to-end path for callers that want both raw
        and classified invariant artifacts.
        """
        artifacts = self.mine_dynamic_constraints()
        classified_invariants_path = self.classify_invariants(
            persist_debug_artifacts=persist_debug_artifacts,
        )
        return {
            **artifacts,
            "classified_invariants_path": classified_invariants_path,
        }



    def _resolve_operation_id(self, method: str, path: str) -> str:
        """Map request method+path to known operation name if possible."""
        # Find best match by path ending
        for op_name, operation in (self.operations or {}).items():
            candidate_path = getattr(operation, "endpoint_path", None) or getattr(operation, "path", None)
            candidate_method = getattr(operation, "http_method", None)

            if candidate_path and candidate_method and candidate_method.upper() == method:
                if path.rstrip("/") == candidate_path.rstrip("/"):
                    return op_name

        # fallback naming
        cleaned_path = path.strip("/").replace("/", "_") or "root"
        return f"{method}_{cleaned_path}"

    def _extract_request_parameters(self, request: Dict[str, Any]) -> Dict[str, List[str]]:
        """Extract query string and body form data from HAR request."""
        parameters: Dict[str, List[str]] = {}

        for q in request.get("queryString", []):
            key = q.get("name")
            value = q.get("value")
            if key:
                parameters.setdefault(key, []).append(value)

        # path_params field may be present in our HAR format
        for k, v in (request.get("path_params", {}) or {}).items():
            if k:
                parameters.setdefault(k, []).append(str(v))

        post_data = request.get("postData", {})
        text = post_data.get("text")

        if text:
            try:
                parsed_body = json.loads(text)
                if isinstance(parsed_body, dict):
                    for k, v in parsed_body.items():
                        parameters.setdefault(k, []).append(str(v))
                else:
                    parameters.setdefault("body", []).append(str(parsed_body))
            except json.JSONDecodeError:
                parameters.setdefault("body", []).append(str(text))

        return parameters

    def generate_dtrace_file(self, test_cases: List[TestCase], output_path: str | Path) -> None:
        """Generate dtrace file from test cases array.
        
        Args:
            test_cases: List of TestCase objects
            output_path: Path to output .dtrace file
        """
        if not self.decls_file:
            raise RuntimeError("DeclsFile is not generated. Call extract_decls_classes() first.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        test_case_count = 0

        with output_path.open('w', encoding='utf-8') as dtrace_out:
            dtrace_out.write("decl-version 2.0\n")
            dtrace_out.write("var-comparability implicit\n\n")

            for test_case in test_cases:
                if test_case_count % 50 == 0:
                    self.logger.info(f"Generated dtrace for {test_case_count} test cases")

                test_case_count += 1
                # test_case.path = test_case.path.replace(self.decls_file.common_path, "") # only get relative path

                for decls_class in self.decls_file.decls_classes:
                    test_case_path = f"{test_case.http_method.lower()}-{test_case.path}"
                    if self._path_matches_endpoint(decls_class.class_name, test_case_path):
                        exits_for_status = [
                            e for e in decls_class.decls_exits
                            if int(e.status_code) == int(test_case.status_code or 0)
                        ]

                        for decls_exit in exits_for_status:
                            enters_for_exit = [
                                e for e in decls_class.decls_enters
                                if (int(e.status_code) == int(decls_exit.status_code) and
                                    e.name_suffix == decls_exit.name_suffix)
                            ]

                            if enters_for_exit:
                                decls_enter = enters_for_exit[0]
                                dtrace_content = decls_exit.generate_dtrace(test_case, decls_enter)
                                dtrace_out.write(dtrace_content)

        self.logger.info(f"Generated dtrace file: {output_path}")

    def _path_matches_endpoint(self, endpoint: str, path: str) -> bool:
        """Check if test case path matches the decls class endpoint.
        
        Args:
            endpoint: Decls class endpoint (e.g., "GET-/api/users")
            path: Test case path (e.g., "/api/users")
            
        Returns:
            True if they match
        """
        # Extract path part from endpoint (after the method)
        # if '-' in endpoint:
        #     endpoint_path = endpoint.split('-', 1)[1]
        # else:
        #     endpoint_path = endpoint
        # Simple match: check if path contains endpoint_path or vice versa
        return endpoint.lower() == path.lower()

    def extract_constraints(self):
        """Optional stub for constraint extraction workflow."""
        if not self.decls_file:
            raise RuntimeError("No DeclsFile available. Call extract_decls_classes() first.")

        # Placeholder: actual dynamic constraint logic should be added here.
        return {
            "decls_classes": len(self.decls_file.decls_classes),
            "operations": len(self.operations),
        }
