import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from api_testing.constraint.counter_examples.reducer import reduce_runtime_evidence
from api_testing.constraint.evaluation import DSLEngine
from api_testing.memory.contextual_memory import ContextualMemory
from api_testing.models.http_data import RequestData, ResponseData
from api_testing.utils.log import getLogger


class ConstraintRuleEvaluator:
    """Evaluate static DSL and common dynamic invariant forms on one response."""

    def __init__(self) -> None:
        self.engine = DSLEngine()

    @staticmethod
    def _canonical_path(value: str) -> str:
        return value.replace("[]", "")

    def _align_property(self, expression: str, property_name: str) -> str:
        def replace_path(match: re.Match) -> str:
            value = match.group(0)
            if self._canonical_path(value) == self._canonical_path(property_name):
                return property_name
            return value

        return re.sub(r"return(?:\.[A-Za-z_][A-Za-z0-9_]*(?:\[\])?)+", replace_path, expression)

    @staticmethod
    def _split_arguments(expression: str) -> list[str]:
        arguments: list[str] = []
        start = 0
        depth = 0
        quoted = False
        quote = ""
        for index, char in enumerate(expression):
            if quoted:
                if char == quote:
                    quoted = False
                continue
            if char in ("'", '"'):
                quoted = True
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0:
                arguments.append(expression[start:index].strip())
                start = index + 1
        arguments.append(expression[start:].strip())
        return arguments

    def _dynamic_to_dsl(self, expression: str, property_name: str) -> Optional[str]:
        value = self._align_property(expression.strip(), property_name)
        if value.startswith("and(") and value.endswith(")"):
            parts = self._split_arguments(value[4:-1])
            translated = [self._dynamic_to_dsl(part, property_name) for part in parts]
            if all(translated):
                return "and(" + ",".join(translated) + ")"
            return None

        one_of = re.fullmatch(r"(.+?)\s+one of\s+\{\s*(.+?)\s*\}", value)
        if one_of:
            return f"in({one_of.group(1).strip()},[{one_of.group(2)}])"

        length = re.fullmatch(r"LENGTH\((.+)\)\s*==\s*(-?\d+)", value, flags=re.IGNORECASE)
        if length:
            return f"eq(size_of({length.group(1).strip()}),{length.group(2)})"

        is_url = re.fullmatch(r"(.+?)\s+is\s+Url", value, flags=re.IGNORECASE)
        if is_url:
            return f"isURL({is_url.group(1).strip()})"

        elements_equal = re.fullmatch(r"(.+\[\])\s+elements\s+==\s+(.+)", value)
        if elements_equal:
            return f"allEq({elements_equal.group(1).strip()},{elements_equal.group(2).strip()})"

        is_member = re.fullmatch(r"(.+?)\s+in\s+(.+\[\])", value)
        if is_member:
            return f"contains({is_member.group(2).strip()},{is_member.group(1).strip()})"

        comparison = re.fullmatch(r"(.+?)\s*(>=|<=|==|>|<)\s*(.+)", value)
        if comparison:
            left, operator, right = comparison.groups()
            operations = {">=": "gte", "<=": "lte", "==": "eq", ">": "gt", "<": "lt"}
            right = right.replace("size(", "size_of(")
            return f"{operations[operator]}({left.strip()},{right.strip()})"

        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(", value):
            return value
        return None

    def executable_rule(
        self,
        expression: str,
        property_name: str,
        dynamic: bool = False,
    ) -> Optional[str]:
        return self._dynamic_to_dsl(expression, property_name) if dynamic else expression

    def evaluate(
        self,
        expression: str,
        property_name: str,
        response_payload: Any,
        request_parameters: Dict[str, Any],
        dynamic: bool = False,
    ) -> Optional[bool]:
        rule = self.executable_rule(expression, property_name, dynamic=dynamic)
        if rule is None:
            return None
        context = {"return": response_payload or {}, "input": request_parameters or {}}
        if not self.engine._collect_targets(property_name, context):
            return None
        try:
            return self.engine.validate({property_name: rule}, context)[property_name]
        except Exception:
            return None

    def has_target(self, property_name: str, response_payload: Any) -> bool:
        context = {"return": response_payload or {}, "input": {}}
        return bool(self.engine._collect_targets(property_name, context))


class ConstraintConflictResolver:
    """Execute staged requests and attach runtime support to relation records."""

    MAIN_CACHE = "combine_constraint_miners.json"

    def __init__(
        self,
        cache_dir: str | Path,
        base_url: Optional[str] = None,
        requestor: Optional[Any] = None,
        evaluator: Optional[ConstraintRuleEvaluator] = None,
        memory: Optional[Any] = None,
        request_timeout: tuple[float, float] = (5.0, 30.0),
        max_test_cases: int = 5,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.base_url = base_url
        self.requestor = requestor
        self.evaluator = evaluator or ConstraintRuleEvaluator()
        self.request_timeout = request_timeout
        self.max_test_cases = max(1, max_test_cases)
        self.logger = getLogger(__name__)
        self._owns_memory = False
        self.memory = memory
        memory_path = self.cache_dir / "contextual_memory.db"
        if self.memory is None and memory_path.exists():
            self.memory = ContextualMemory(cache_dir=str(self.cache_dir))
            self._owns_memory = True

    def _memory_path_parameter_candidates(
        self, endpoint: str, required_parameters: list[str]
    ) -> list[Dict[str, Any]]:
        if self.memory is None or not required_parameters:
            return []
        endpoint_context = self.memory.contexts.get(endpoint, {})
        if not isinstance(endpoint_context, dict):
            return []
        candidates: list[Dict[str, Any]] = []
        for item in endpoint_context.get("whitelist", []):
            if isinstance(item, dict) and all(key in item for key in required_parameters):
                candidates.append({key: item[key] for key in required_parameters})
        # Generated histories may store both integer IDs and their URL string forms.
        # Prefer typed values so response equality checks follow the API schema type.
        candidates.sort(
            key=lambda candidate: sum(
                isinstance(value, str) for value in candidate.values()
            )
        )
        return candidates

    def _request_from_record(self, record: Dict[str, Any]) -> Optional[RequestData]:
        counter_example = record.get("counter_example") or {}
        payload = counter_example.get("staged_payload") or {}
        endpoint = record["endpoint"]
        default_method, _, default_path = endpoint.partition("-")
        path_parameters = re.findall(r"{([^}]+)}", default_path)
        parameters = dict(payload.get("parameters") or {})
        candidates = self._memory_path_parameter_candidates(endpoint, path_parameters)
        memory_parameters = candidates[0] if candidates else {}
        for key, value in memory_parameters.items():
            parameters[key] = value
        if path_parameters and not all(key in parameters for key in path_parameters):
            record["verification_error"] = (
                "No whitelisted contextual-memory values are available for required path "
                f"parameters: {', '.join(path_parameters)}."
            )
            return None
        if memory_parameters:
            counter_example["path_parameter_source"] = "contextual_memory.db whitelist"
        if not payload:
            counter_example["request_source"] = "default endpoint probe; no LLM payload was staged"
        record["counter_example"] = counter_example
        return RequestData(
            # Resolve parameterized endpoints from the canonical endpoint instead of
            # accepting an unverified literal identifier guessed by the LLM.
            endpoint_path=default_path if path_parameters else payload.get("endpoint_path") or default_path,
            http_method=payload.get("http_method") or default_method,
            parameters=parameters,
            headers=payload.get("headers") or {},
            body=payload.get("body"),
            mime_type=payload.get("mime_type") or "application/json",
            expected_code="2xx",
        )

    def _request_variants(self, record: Dict[str, Any], request: RequestData) -> list[RequestData]:
        variants: list[RequestData] = []
        signatures: set[str] = set()

        def add(candidate: RequestData) -> None:
            signature = json.dumps(candidate.to_dict(), sort_keys=True, default=str)
            if signature not in signatures and len(variants) < self.max_test_cases:
                signatures.add(signature)
                variants.append(candidate)

        add(request)
        counter_example = record.get("counter_example") or {}
        default_method, _, default_path = record["endpoint"].partition("-")
        required_parameters = re.findall(r"{([^}]+)}", default_path)
        memory_candidates = self._memory_path_parameter_candidates(
            record["endpoint"], required_parameters
        )
        preferred_memory = memory_candidates[0] if memory_candidates else {}
        for payload in counter_example.get("staged_payloads") or []:
            parameters = dict(payload.get("parameters") or {})
            parameters.update(preferred_memory)
            add(
                RequestData(
                    endpoint_path=(
                        default_path
                        if required_parameters
                        else payload.get("endpoint_path") or default_path
                    ),
                    http_method=payload.get("http_method") or default_method,
                    parameters=parameters,
                    headers=payload.get("headers") or {},
                    body=payload.get("body"),
                    mime_type=payload.get("mime_type") or "application/json",
                    expected_code="2xx",
                )
            )
        for candidate in self._memory_path_parameter_candidates(
            record["endpoint"], required_parameters
        ):
            alternate = copy.deepcopy(request)
            alternate.parameters.update(candidate)
            add(alternate)

        query_parameters = {
            key: value
            for key, value in request.parameters.items()
            if key not in required_parameters
        }
        if query_parameters:
            default_probe = copy.deepcopy(request)
            default_probe.parameters = {
                key: value
                for key, value in default_probe.parameters.items()
                if key in required_parameters
            }
            add(default_probe)
        return variants

    def _execute(self, request: RequestData) -> ResponseData:
        if self.requestor is not None:
            if hasattr(self.requestor, "exec"):
                return self.requestor.exec(request)
            return self.requestor(request)
        if not self.base_url:
            raise ValueError("base_url is required when no requestor is supplied")

        parameters = dict(request.parameters or {})
        endpoint_path = request.endpoint_path
        for key in re.findall(r"{([^}]+)}", endpoint_path):
            if key in parameters:
                endpoint_path = endpoint_path.replace(f"{{{key}}}", str(parameters.pop(key)))

        url = f"{self.base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
        kwargs: Dict[str, Any] = {
            "headers": request.resolve_headers(),
            "cookies": request.resolve_cookies(),
            "params": parameters,
            "timeout": self.request_timeout,
        }
        if request.body is not None:
            if "application/json" in request.mime_type:
                kwargs["json"] = request.body
            else:
                kwargs["data"] = request.body
        try:
            response = requests.request(request.http_method, url, **kwargs)
            return ResponseData.from_requests(response)
        except requests.exceptions.RequestException as exc:
            self.logger.warning("Counter-example request failed for %s: %s", url, exc)
            return ResponseData.from_requests(None)

    @staticmethod
    def _response_summary(response: ResponseData) -> Dict[str, Any]:
        summary: Dict[str, Any] = {
            "status_code": response.status_code,
            "mime_type": response.mime_type,
        }
        payload = response.parsed
        if isinstance(payload, dict):
            summary["response_properties"] = sorted(payload.keys())
        elif isinstance(payload, list):
            summary["response_items"] = len(payload)
        elif payload is not None:
            summary["response_type"] = type(payload).__name__
        return summary

    def _evaluate_case(
        self, record: Dict[str, Any], request: RequestData, response: ResponseData, index: int
    ) -> Dict[str, Any]:
        case: Dict[str, Any] = {
            "case_number": index,
            "request": request.to_dict(),
            "response_summary": self._response_summary(response),
            "response_payload": response.parsed,
            "static_evaluation": {
                "source_expression": record["static_constraint"],
                "executed_expression": self.evaluator.executable_rule(
                    record["static_constraint"], record["property"]
                ),
                "result": None,
            },
            "dynamic_evaluation": {
                "source_expression": record["dynamic_constraint"],
                "executed_expression": self.evaluator.executable_rule(
                    record["dynamic_constraint"], record["property"], dynamic=True
                ),
                "result": None,
            },
        }
        if response.status_code >= 500:
            case["runtime_verdict"] = "CONFLICT_BOTH_FALSE"
            return case
        if not response.ok:
            case["runtime_verdict"] = "INCONCLUSIVE_HTTP_STATUS"
            return case
        if not self.evaluator.has_target(record["property"], response.parsed):
            case["runtime_verdict"] = "PROPERTY_NOT_PRESENT"
            return case

        parameters = request.parameters or {}
        if isinstance(request.body, dict):
            parameters = {**parameters, **request.body}
        static_true = self.evaluator.evaluate(
            record["static_constraint"], record["property"], response.parsed, parameters
        )
        dynamic_true = self.evaluator.evaluate(
            record["dynamic_constraint"],
            record["property"],
            response.parsed,
            parameters,
            dynamic=True,
        )
        case["static_evaluation"]["result"] = static_true
        case["dynamic_evaluation"]["result"] = dynamic_true
        if static_true is None or dynamic_true is None:
            case["runtime_verdict"] = "INCONCLUSIVE_EVALUATION"
        elif static_true and not dynamic_true:
            case["runtime_verdict"] = "STATIC_WIN"
        elif dynamic_true and not static_true:
            case["runtime_verdict"] = "DYNAMIC_WIN"
        elif static_true and dynamic_true:
            case["runtime_verdict"] = "BOTH_TRUE"
        else:
            case["runtime_verdict"] = "CONFLICT_BOTH_FALSE"
        return case

    def evaluate_case(
        self, record: Dict[str, Any], request: RequestData, response: ResponseData, index: int
    ) -> Dict[str, Any]:
        """Evaluate one approved counter-example request/response pair.

        This public wrapper keeps backend HITL review code off private resolver
        methods while preserving the existing conflict-resolution semantics.
        """
        return self._evaluate_case(record, request, response, index)

    def _apply_aggregate_verdict(self, record: Dict[str, Any], cases: list[Dict[str, Any]]) -> None:
        evaluated_cases = [
            case for case in cases if case["runtime_verdict"] != "PROPERTY_NOT_PRESENT"
        ]
        verdicts = {case["runtime_verdict"] for case in evaluated_cases}
        record["runtime_evaluation"] = {
            "cases_executed": len(cases),
            "cases_evaluated": len(evaluated_cases),
            "static_expression": self.evaluator.executable_rule(
                record["static_constraint"], record["property"]
            ),
            "dynamic_expression": self.evaluator.executable_rule(
                record["dynamic_constraint"], record["property"], dynamic=True
            ),
            "case_runtime_verdicts": [case["runtime_verdict"] for case in cases],
        }
        reduction = reduce_runtime_evidence(
            relation=record.get("relation"),
            cases=cases,
        )
        record["runtime_verdict"] = reduction.runtime_verdict
        record["runtime_recommendation"] = reduction.runtime_recommendation
        record["reason"] = reduction.reason

    def _resolve_record(
        self, record: Dict[str, Any], progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        if record.get("status") not in {"UNRESOLVED", "CONFLICT"}:
            return record
        if not record.get("static_constraint") or not record.get("dynamic_constraint"):
            return record
        request = self._request_from_record(record)
        if request is None:
            record["runtime_verdict"] = "PENDING_PATH_PARAMETERS"
            record["reason"] = (
                f"{record['reason']} {record.get('verification_error', 'No executable request is available.')}"
            )
            return record

        counter_example = record.setdefault("counter_example", {})
        cases = []
        for index, variant in enumerate(self._request_variants(record, request), start=1):
            response = self._execute(variant)
            cases.append(self._evaluate_case(record, variant, response, index))
            record["validation_cases"] = cases
            if cases:
                counter_example["staged_payload"] = cases[0]["request"]
                counter_example["server_actual_response"] = cases[0]["response_summary"]
            if progress_callback is not None:
                progress_callback()
        record["validation_cases"] = cases
        first_case = cases[0]
        counter_example["staged_payload"] = first_case["request"]
        counter_example["server_actual_response"] = first_case["response_summary"]
        self._apply_aggregate_verdict(record, cases)
        return record

    def resolve(self, combined_constraints: Dict[str, Any]) -> Dict[str, Any]:
        output = copy.deepcopy(combined_constraints)
        for properties in output.values():
            for property_name, record in properties.items():
                if record.get("status") in {"UNRESOLVED", "CONFLICT"}:
                    properties[property_name] = self._resolve_record(
                        record, progress_callback=lambda: self._save(output)
                    )
                    # Persist progress after each runtime check. A cancelled network or
                    # LLM run must not discard evidence from completed requests.
                    self._save(output)
        self._save(output)
        if self._owns_memory:
            self.memory.close()
            self._owns_memory = False
        return output

    def _save(self, result: Dict[str, Any]) -> None:
        output_path = self.cache_dir / self.MAIN_CACHE
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, indent=4, default=str)
