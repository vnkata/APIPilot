from __future__ import annotations

from dataclasses import asdict
import json
import re

from api_testing.constraint.dynamic_constraints.classification.models import (
    NormalizedInvariantContext,
    ParsedProgramPoint,
    PathSegment,
    VariableReference,
)
from api_testing.constraint.dynamic_constraints.invariant_reader import InvariantRecord
from api_testing.models.specification_model import OperationProperties


HTTP_METHOD_PREFIXES = ("get", "post", "put", "patch", "delete", "head", "options")


class InvariantContextParser:
    """Parse Daikon program points and variable references into classifier context.

    The parser converts raw Daikon strings such as
    ``get-/widgets&get-/widgets&200&items():::EXIT`` and
    ``(input.category, return.items[..])`` into typed objects consumed by the
    classifier, excerpt builder, and example extractor.
    """

    def __init__(
        self,
        operations: dict[str, OperationProperties],
        invariant_kinds: dict[str, str],
    ) -> None:
        self.operations = operations
        self.invariant_kinds = invariant_kinds

    def normalize_record(self, record: InvariantRecord) -> NormalizedInvariantContext:
        """Resolve one raw invariant row into operation, program point, and variables."""
        parsed_program_point = self.parse_program_point(record.pptname)
        operation = self.resolve_operation(parsed_program_point.operation_key)
        if operation is None:
            raise RuntimeError(
                f"Unable to resolve operation '{parsed_program_point.operation_key}' from pptname '{record.pptname}'."
            )

        variables = self.parse_variables(record.variables)
        input_variables = tuple(variable for variable in variables if variable.role == "input")
        output_variables = tuple(variable for variable in variables if variable.role == "return")

        return NormalizedInvariantContext(
            record=record,
            parsed_program_point=parsed_program_point,
            operation=operation,
            invariant_description=self.invariant_kinds.get(
                record.invariant_type,
                "No invariant description available.",
            ),
            input_variables=input_variables,
            output_variables=output_variables,
        )

    def parse_program_point(self, pptname: str) -> ParsedProgramPoint:
        """Parse the operation key, status code, Daikon point, and response container path."""
        if ":::" not in pptname:
            raise ValueError(f"Invalid pptname format: {pptname}")

        prefix, program_point = pptname.split(":::", 1)
        segments = [segment for segment in prefix.split("&") if segment]

        operation_key = None
        status_code = ""
        containers: list[PathSegment] = []

        for segment in segments:
            lower_segment = segment.lower()
            if operation_key is None and any(
                lower_segment.startswith(f"{method}-") for method in HTTP_METHOD_PREFIXES
            ):
                method_name, endpoint_path = segment.split("-", 1)
                operation_key = f"{method_name.lower()}-{endpoint_path}"
                continue
            if operation_key is not None and lower_segment == operation_key.lower():
                continue

            status_match = re.match(r"^(?P<status>\d+)(?P<suffix>.*)$", segment)
            if status_code == "" and status_match:
                status_code = status_match.group("status")
                suffix = status_match.group("suffix")
                if suffix:
                    containers.extend(self._parse_container_segment(suffix))
                continue

            containers.extend(self._parse_container_segment(segment))

        if operation_key is None or "-" not in operation_key:
            raise ValueError(f"Could not parse operation key from pptname: {pptname}")

        http_method, endpoint_path = operation_key.split("-", 1)
        return ParsedProgramPoint(
            raw=pptname,
            operation_key=operation_key,
            http_method=http_method.lower(),
            endpoint_path=endpoint_path,
            status_code=status_code,
            program_point=program_point,
            container_segments=tuple(containers),
        )

    def parse_variables(self, raw_variables: str) -> tuple[VariableReference, ...]:
        """Parse Daikon variable references into request/response path references."""
        cleaned = raw_variables.strip()
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = cleaned[1:-1]

        values = []
        for raw_token in self._split_top_level(cleaned):
            token = raw_token.strip()
            if not token:
                continue

            is_size = token.startswith("size(") and token.endswith(")")
            variable_token = token[5:-1] if is_size else token

            role = "unknown"
            path_text = variable_token
            input_suffix = self._extract_role_suffix(variable_token, "input")
            return_suffix = self._extract_role_suffix(variable_token, "return")
            if input_suffix is not None:
                role = "input"
                path_text = input_suffix
            elif return_suffix is not None:
                role = "return"
                path_text = return_suffix

            path_segments = self._parse_path_segments(path_text)
            values.append(
                VariableReference(
                    raw=token,
                    role=role,
                    is_size=is_size,
                    path_segments=tuple(path_segments),
                    display_path=".".join(
                        segment.display() for segment in path_segments if segment.display()
                    ),
                )
            )

        return tuple(values)

    def resolve_operation(self, operation_key: str) -> OperationProperties | None:
        """Resolve an operation key from the exact key or method/path fallback."""
        operation = self.operations.get(operation_key)
        if operation is not None:
            return operation

        lowered_key = operation_key.lower()
        for key, candidate in self.operations.items():
            if key.lower() == lowered_key:
                return candidate

        method, path = operation_key.split("-", 1)
        normalized_method = method.lower()
        normalized_path = path.rstrip("/").lower()
        for candidate in self.operations.values():
            candidate_method = (candidate.http_method or "").lower()
            candidate_path = (candidate.endpoint_path or "").rstrip("/").lower()
            if candidate_method == normalized_method and candidate_path == normalized_path:
                return candidate
        return None

    def _parse_container_segment(self, segment: str) -> list[PathSegment]:
        cleaned = segment.strip()
        if not cleaned or cleaned == "()":
            return []

        if cleaned.startswith("%array"):
            return [PathSegment(name=None, is_array=True)]

        if cleaned.endswith("()"):
            name = cleaned[:-2]
            if name == "%array":
                return [PathSegment(name=None, is_array=True)]
            if not name:
                return []
            return [PathSegment(name=name, is_array=True)]

        return [PathSegment(name=cleaned, is_array=False)]

    @staticmethod
    def _extract_role_suffix(variable_token: str, role_prefix: str) -> str | None:
        if not variable_token.startswith(role_prefix):
            return None

        suffix = variable_token[len(role_prefix):]
        if not suffix:
            return ""
        if suffix.startswith("."):
            return suffix[1:]
        if suffix.startswith("["):
            return suffix
        return None

    @staticmethod
    def _split_top_level(value: str) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        depth = 0

        for char in value:
            if char == "," and depth == 0:
                chunks.append("".join(current))
                current = []
                continue

            if char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)

            current.append(char)

        if current:
            chunks.append("".join(current))
        return chunks

    def _parse_path_segments(self, path_text: str) -> list[PathSegment]:
        segments: list[PathSegment] = []
        normalized_path = path_text.replace("[..]", "[]")
        for raw_segment in filter(None, normalized_path.split(".")):
            normalized = raw_segment.strip()
            if not normalized:
                continue
            if normalized == "[]":
                segments.append(PathSegment(name=None, is_array=True))
            elif normalized.endswith("[]"):
                segments.append(PathSegment(name=normalized[:-2], is_array=True))
            else:
                segments.append(PathSegment(name=normalized, is_array=False))
        return segments


def main() -> None:
    """Print a parser demo without requiring a parsed OpenAPI spec."""
    parser = InvariantContextParser(operations={}, invariant_kinds={})
    program_point = parser.parse_program_point(
        "get-/widgets&get-/widgets&200&items():::EXIT"
    )
    variables = parser.parse_variables("(input.category, size(return.tags[..]))")
    print(
        json.dumps(
            {
                "program_point": asdict(program_point),
                "variables": [asdict(variable) for variable in variables],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
