from __future__ import annotations

from dataclasses import asdict, dataclass
import ast
import json
import re
from typing import Any, Callable, Sequence


_MISSING = object()


@dataclass(frozen=True, slots=True)
class ObservedEvidenceAnalysis:
    """Deterministic consistency check between an invariant and recovered examples."""

    status: str
    kind: str
    support_count: int = 0
    contradiction_count: int = 0
    unevaluated_count: int = 0
    contradiction_examples: tuple[str, ...] = ()
    summary: str = ""

    def to_debug_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SpecEnumAnalysis:
    """Deterministic relationship between a ``one of`` invariant and documented enum."""

    status: str
    invariant_values: tuple[Any, ...] = ()
    spec_values: tuple[Any, ...] = ()
    summary: str = ""

    def to_debug_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _Operand:
    kind: str
    value: Any

    def resolve(self, assignments: dict[str, Any]) -> Any:
        if self.kind == "constant":
            return self.value
        if self.kind == "label":
            return assignments.get(self.value, _MISSING)
        if self.kind == "length":
            value = assignments.get(self.value, _MISSING)
            if value is _MISSING:
                return _MISSING
            if isinstance(value, (str, list, tuple, dict)):
                return len(value)
            return _MISSING
        return _MISSING


@dataclass(frozen=True, slots=True)
class _InvariantExpression:
    kind: str
    evaluate: Callable[[dict[str, Any]], bool | None]


def analyze_observed_examples(
    invariant: str,
    examples: Sequence[str],
) -> ObservedEvidenceAnalysis:
    """Evaluate simple invariant expressions against extracted examples.

    This is intentionally narrow. Unsupported patterns return ``not-evaluated`` so
    the LLM remains responsible for semantic judgment.
    """
    if not examples:
        return ObservedEvidenceAnalysis(
            status="no-examples",
            kind="none",
            summary="Observed evidence check: no concrete examples are available.",
        )

    expression = _parse_invariant_expression(invariant)
    if expression is None:
        return ObservedEvidenceAnalysis(
            status="not-evaluated",
            kind="unsupported",
            unevaluated_count=len(examples),
            summary="Observed evidence check: unsupported invariant pattern.",
        )

    support_count = 0
    contradiction_count = 0
    unevaluated_count = 0
    contradiction_examples: list[str] = []

    for example in examples:
        assignments = _parse_assignments(example)
        outcome = expression.evaluate(assignments)
        if outcome is True:
            support_count += 1
        elif outcome is False:
            contradiction_count += 1
            contradiction_examples.append(example)
        else:
            unevaluated_count += 1

    if support_count == 0 and contradiction_count == 0:
        return ObservedEvidenceAnalysis(
            status="not-evaluated",
            kind=expression.kind,
            unevaluated_count=unevaluated_count,
            summary="Observed evidence check: examples could not be evaluated for this invariant.",
        )

    if contradiction_count:
        first_examples = "; ".join(contradiction_examples[:2])
        summary = (
            "Observed evidence check: "
            f"{contradiction_count} of {support_count + contradiction_count} evaluated "
            f"example(s) contradict the invariant. Example(s): {first_examples}"
        )
    else:
        summary = (
            "Observed evidence check: "
            f"all {support_count} evaluated example(s) satisfy the invariant; "
            "no observed contradiction found."
        )

    return ObservedEvidenceAnalysis(
        status="evaluated",
        kind=expression.kind,
        support_count=support_count,
        contradiction_count=contradiction_count,
        unevaluated_count=unevaluated_count,
        contradiction_examples=tuple(contradiction_examples[:5]),
        summary=summary,
    )


def analyze_spec_enum_relationship(invariant: str, spec_excerpt: str) -> SpecEnumAnalysis:
    parsed_one_of = _parse_one_of_invariant(invariant)
    if parsed_one_of is None:
        return SpecEnumAnalysis(
            status="not-applicable",
            summary="Spec enum check: invariant is not a one-of expression.",
        )

    label, invariant_values = parsed_one_of
    spec_values = _find_spec_enum_values(label, spec_excerpt)
    if spec_values is None:
        return SpecEnumAnalysis(
            status="no-enum",
            invariant_values=tuple(invariant_values),
            summary="Spec enum check: no matching documented enum found in the excerpt.",
        )

    invariant_keys = {_value_key(value) for value in invariant_values}
    spec_keys = {_value_key(value) for value in spec_values}

    if invariant_keys == spec_keys:
        return SpecEnumAnalysis(
            status="exact",
            invariant_values=tuple(invariant_values),
            spec_values=tuple(spec_values),
            summary="Spec enum check: invariant values exactly match the documented enum.",
        )
    if invariant_keys.issubset(spec_keys):
        additional = sorted(spec_keys - invariant_keys)
        return SpecEnumAnalysis(
            status="subset",
            invariant_values=tuple(invariant_values),
            spec_values=tuple(spec_values),
            summary=(
                "Spec enum check: invariant is a strict subset of the documented enum; "
                f"spec enum allows additional value(s): {', '.join(additional)}."
            ),
        )

    missing = sorted(invariant_keys - spec_keys)
    return SpecEnumAnalysis(
        status="conflict",
        invariant_values=tuple(invariant_values),
        spec_values=tuple(spec_values),
        summary=(
            "Spec enum check: invariant includes value(s) not documented in the enum: "
            f"{', '.join(missing)}."
        ),
    )


def _parse_invariant_expression(invariant: str) -> _InvariantExpression | None:
    cleaned = invariant.strip()

    one_of = _parse_one_of_invariant(cleaned)
    if one_of is not None:
        label, values = one_of
        value_keys = {_value_key(value) for value in values}

        def evaluate_one_of(assignments: dict[str, Any]) -> bool | None:
            actual = assignments.get(label, _MISSING)
            if actual is _MISSING or isinstance(actual, (list, dict)):
                return None
            return _value_key(actual) in value_keys

        return _InvariantExpression(kind="one_of", evaluate=evaluate_one_of)

    substring_match = re.fullmatch(
        r"(?P<left>.+?)\s+is a substring of\s+(?P<right>.+)",
        cleaned,
    )
    if substring_match:
        left = _parse_operand(substring_match.group("left"))
        right = _parse_operand(substring_match.group("right"))

        def evaluate_substring(assignments: dict[str, Any]) -> bool | None:
            left_value = left.resolve(assignments)
            right_value = right.resolve(assignments)
            if left_value is _MISSING or right_value is _MISSING:
                return None
            if not isinstance(left_value, str) or not isinstance(right_value, str):
                return None
            return left_value in right_value

        return _InvariantExpression(kind="substring", evaluate=evaluate_substring)

    comparison_match = re.fullmatch(
        r"(?P<left>.+?)\s*(?P<operator>>=|<=|==|>|<)\s*(?P<right>.+)",
        cleaned,
    )
    if not comparison_match:
        return None

    left = _parse_operand(comparison_match.group("left"))
    right = _parse_operand(comparison_match.group("right"))
    operator = comparison_match.group("operator")

    def evaluate_comparison(assignments: dict[str, Any]) -> bool | None:
        left_value = left.resolve(assignments)
        right_value = right.resolve(assignments)
        if left_value is _MISSING or right_value is _MISSING:
            return None
        return _compare_values(left_value, right_value, operator)

    return _InvariantExpression(kind=f"comparison:{operator}", evaluate=evaluate_comparison)


def _parse_one_of_invariant(invariant: str) -> tuple[str, list[Any]] | None:
    match = re.fullmatch(r"(?P<label>.+?)\s+one of\s+\{(?P<values>.*)\}", invariant.strip())
    if not match:
        return None

    values = _parse_value_list(match.group("values"))
    if not values:
        return None
    return match.group("label").strip(), values


def _parse_assignments(example: str) -> dict[str, Any]:
    assignments: dict[str, Any] = {}
    for chunk in _split_example_assignments(example):
        label, separator, value_text = chunk.partition("=")
        if not separator:
            continue
        assignments[label.strip()] = _parse_value(value_text.strip())
    return assignments


def _split_example_assignments(example: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_string = False
    escape = False

    for char in example:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\" and in_string:
            current.append(char)
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            current.append(char)
            continue
        if char == ";" and not in_string:
            chunks.append("".join(current).strip())
            current = []
            continue
        current.append(char)

    if current:
        chunks.append("".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def _parse_operand(raw_operand: str) -> _Operand:
    text = raw_operand.strip()
    length_match = re.fullmatch(r"LENGTH\((?P<label>.+)\)", text)
    if length_match:
        return _Operand(kind="length", value=length_match.group("label").strip())

    constant = _try_parse_constant(text)
    if constant is not _MISSING:
        return _Operand(kind="constant", value=constant)
    return _Operand(kind="label", value=text)


def _try_parse_constant(text: str) -> Any:
    if not text:
        return _MISSING
    if text[0] == '"' and text[-1:] == '"':
        return _parse_value(text)
    if text in {"[]", "{}", "true", "false", "null"}:
        return _parse_value(text)
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return _MISSING


def _parse_value_list(value_list_text: str) -> list[Any]:
    wrapped = f"[{value_list_text}]"
    try:
        value = json.loads(wrapped)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        values = []
        for raw_value in _split_comma_values(value_list_text):
            parsed = _parse_value(raw_value.strip())
            values.append(parsed)
        return values


def _split_comma_values(value: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    in_string = False
    escape = False

    for char in value:
        if escape:
            current.append(char)
            escape = False
            continue
        if char == "\\" and in_string:
            current.append(char)
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            current.append(char)
            continue
        if char == "," and not in_string:
            chunks.append("".join(current))
            current = []
            continue
        current.append(char)

    if current:
        chunks.append("".join(current))
    return chunks


def _parse_value(value_text: str) -> Any:
    try:
        return json.loads(value_text)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(value_text)
    except (SyntaxError, ValueError):
        return value_text


def _compare_values(left: Any, right: Any, operator: str) -> bool | None:
    if operator == "==":
        return left == right

    if not _is_orderable(left) or not _is_orderable(right):
        return None

    if operator == "<=":
        return left <= right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == ">":
        return left > right
    return None


def _is_orderable(value: Any) -> bool:
    return isinstance(value, (int, float, str)) and not isinstance(value, bool)


def _find_spec_enum_values(label: str, spec_excerpt: str) -> list[Any] | None:
    label_leaf = _leaf_name(label)
    if not label_leaf:
        return None

    for line in spec_excerpt.splitlines():
        if "enum=" not in line:
            continue
        if not _line_matches_label(line, label_leaf):
            continue
        enum_match = re.search(r"enum=(?P<enum>\[[^\]]*\])", line)
        if not enum_match:
            continue
        try:
            enum_values = ast.literal_eval(enum_match.group("enum"))
        except (SyntaxError, ValueError):
            continue
        if isinstance(enum_values, list):
            return enum_values
    return None


def _leaf_name(label: str) -> str:
    cleaned = label.strip()
    size_match = re.fullmatch(r"size\((?P<label>.+)\)", cleaned)
    if size_match:
        cleaned = size_match.group("label")
    cleaned = cleaned.replace("[]", "")
    if "." not in cleaned:
        return cleaned
    return cleaned.rsplit(".", 1)[-1]


def _line_matches_label(line: str, leaf_name: str) -> bool:
    lowered_line = line.lower()
    lowered_leaf = leaf_name.lower()
    return (
        f"`{lowered_leaf}`" in lowered_line
        or f".{lowered_leaf}`" in lowered_line
        or f"[].{lowered_leaf}`" in lowered_line
    )


def _value_key(value: Any) -> str:
    if isinstance(value, bool):
        return json.dumps(int(value), ensure_ascii=False, sort_keys=True)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)
