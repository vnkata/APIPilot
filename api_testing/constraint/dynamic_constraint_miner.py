

import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any, Dict, List, Optional

from api_testing.constraint.dynamic_constraints.decls_file import Comparability, DeclsFile
from api_testing.utils.log import getLogger


class DynamicConstraintMiner:
    """Dynamic constraint miner that maps API spec operations to Daikon .decls/.dtrace."""

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

    def extract_decls_classes(self) -> DeclsFile:
        """Parse operations from spec_parser into DeclsFile."""
        self.decls_file = DeclsFile(
            version=1.0,
            comparability=Comparability.IMPLICIT,
            decls_classes=[],
            spec_parser=self.spec_parser,
        )

        # Existing API path conversion logic in DeclsFile
        self.decls_file.parse_operations()

        return self.decls_file

    def save_decls_file(self, output_path: str) -> None:
        """Persist DeclsFile to disk in Daikon .decls format."""
        if not self.decls_file:
            raise RuntimeError("DeclsFile is not generated. Call extract_decls_classes() first.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            # Input header lines for compatibility with Daikon
            f.write("input-language OpenAPI\n")
            f.write("decl-version 2.0\n")
            f.write("var-comparability implicit\n\n")
            f.write(str(self.decls_file))

        self.logger.info(f"Wrote declarations to {output_path}")

    def extract_dtraces_from_har(self, har_path: str, output_path: str) -> None:
        """Read a HAR file and write an approximate Daikon .dtrace file."""
        with open(har_path, "r", encoding="utf-8") as f:
            har_data = json.load(f)

        if "log" not in har_data or "entries" not in har_data["log"]:
            raise ValueError("Invalid HAR data: missing log.entries")

        entries = har_data["log"]["entries"]
        dtrace_path = Path(output_path)
        dtrace_path.parent.mkdir(parents=True, exist_ok=True)

        with dtrace_path.open("w", encoding="utf-8") as fout:
            fout.write("input-language OpenAPI\n")
            fout.write("decl-version 2.0\n")
            fout.write("var-comparability implicit\n\n")

            for i, entry in enumerate(entries, start=1):
                request = entry.get("request", {})
                response = entry.get("response", {})

                method = request.get("method", "UNKNOWN").upper()
                url = request.get("url", "")
                parsed = urlparse(url)
                endpoint_path = parsed.path

                operation_id = self._resolve_operation_id(method, endpoint_path)
                ppt_name = f"{operation_id}:::ENTER"

                # Collate parameters from queryString and postData
                params = self._extract_request_parameters(request)

                fout.write(f"{ppt_name}:::ENTER\n")
                fout.write("this_invocation_nonce\n")
                fout.write(f"{i}\n")

                # Add simple input parameters
                for k, v in params.items():
                    # convert list/values to stable string representation
                    value = ",".join(v) if isinstance(v, list) else str(v)
                    fout.write(f"{k}\n")
                    fout.write(f"{value}\n")

                fout.write("status_code\n")
                fout.write(f"{response.get('status', '')}\n")

                content = response.get("content", {})
                if content:
                    fout.write("response_body\n")
                    body_value = content.get("text", "")
                    if isinstance(body_value, str):
                        body_value = body_value.replace("\n", "\\n")
                    fout.write(f"{body_value}\n")

                fout.write("\n")

        self.logger.info(f"Wrote dtrace file to {dtrace_path}")

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

    def extract_constraints(self):
        """Optional stub for constraint extraction workflow."""
        if not self.decls_file:
            raise RuntimeError("No DeclsFile available. Call extract_decls_classes() first.")

        # Placeholder: actual dynamic constraint logic should be added here.
        return {
            "decls_classes": len(self.decls_file.decls_classes),
            "operations": len(self.operations),
        }
