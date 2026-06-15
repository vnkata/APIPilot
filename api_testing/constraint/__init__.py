import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from api_testing.constraint.dynamic_constraint_miner import DynamicConstraintMiner
from api_testing.constraint.evaluation import DSLEngine, DSLEvaluationContext
from api_testing.generators.counter_value_generator import HypothesisProperties
from api_testing.generators.executor import Executor, Strategy
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.constraint_arbitration import ConstraintArbitration
from api_testing.prompts.counterfactual_hypothesis_review import CounterfactualHypothesisReview
from api_testing.utils import flatten_json_schema
from api_testing.utils.http import isSuccessful
from api_testing.utils.log import getLogger

from .static_constraint_miner import (
    StaticConstraintMiner
)

__all__ = [
    "OperationGraph",
    "OperationNode",
    "OperationEdge"
]

class ConstraintMiner:
    MAIN_CACHE = "constraint_miner.json"
    def __init__(
        self,
        spec_parser: Any,
        model: Optional[Any] = None,
        embedding_model: Optional[Any] = None,
        cache_dir: Optional[str] = None,
        requestHeader = None
    ) -> None:
        self.spec_parser = spec_parser
        self.model = model
        self.embedder = embedding_model
        self.project_dir = cache_dir
        self.staic_miner = StaticConstraintMiner(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        self.dynamic_miner = DynamicConstraintMiner(
            spec_parser=self.spec_parser,
            model=self.model,
            cache_dir=self.project_dir
        )
        self.operations = self.spec_parser.operations
        self.logger = getLogger(__name__)
        self.requestHeader = requestHeader

        self.arbitration = ConstraintArbitration(llm=self.model)
        self.counterfactual_reviewer = CounterfactualHypothesisReview(llm=self.model)

    def static_mining(self):
        self.static_constraints = self.staic_miner.mining()

        return self.static_constraints
    
    def dynamic_mining(self):
        self.dynamic_constraints = self.dynamic_miner.mining()
        return self.dynamic_constraints
    
    @staticmethod
    def _load_json_file(filepath: Path) -> Dict[str, Any]:
        """
        Load data from JSON file.
        
        Args:
            filepath: Path to the JSON file
            
        Returns:
            Loaded data dictionary
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise IOError(f"Failed to load JSON from {filepath}: {str(e)}")
        
    def _save_constraints_to_cache(self) -> None:
        """Save all constraints to main cache file."""
        cache_file = Path(self.project_dir) / self.MAIN_CACHE
        self._save_json_file(cache_file, self.constraints)

    @staticmethod
    def _save_json_file(filepath: Path, data: Dict[str, Any]) -> None:
        """
        Save data to JSON file with proper encoding.
        
        Args:
            filepath: Path to save the JSON file
            data: Data to serialize
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise IOError(f"Failed to save JSON to {filepath}: {str(e)}")
    
    def _build_test_case_context(
        self,
        test_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        context = {}
        # input
        input_data = {}
        parameters = test_case.get("parameters") or {}
        if isinstance(parameters, dict):
            input_data.update(parameters)
        request_body = test_case.get("request_body") or {}
        if isinstance(request_body, dict):
            input_data.update(request_body)
        context["input"] = input_data
        # return
        response_body = test_case.get("response_body")
        if isinstance(response_body, str):
            try:
                response_body = json.loads(response_body)
            except Exception:
                pass
        context["return"] = response_body or {}
        return context
    
    def verify_static_constraints(self):
        """
        Validate spec-derived constraints using existing execution evidence.

        Any constraint contradicted by at least one successful execution
        will be removed from self.static_constraints.
        """
        test_case_file = Path(self.project_dir) / "test_cases.json"

        if not test_case_file.exists():
            self.logger.warning(
                f"Test case file not found: {test_case_file}"
            )
            return {}

        if not hasattr(self, "static_constraints"):
            self.static_mining()

        test_cases = self._load_json_file(test_case_file)

        # group by operation
        grouped: Dict[str, list] = {}

        for tc in test_cases:
            operation_id = tc.get("operation_id")
            if not operation_id:
                continue
            grouped.setdefault(
                operation_id,
                []
            ).append(tc)
        engine = DSLEngine()
        removed_constraints: Dict[str, Dict[str, Any]] = {}
        filtered_constraints: Dict[str, Dict[str, str]] = {}
        for endpoint, constraints in self.static_constraints.items():
            filtered_constraints[endpoint] = {}
            endpoint_records = grouped.get(endpoint, [])
            # No evidence -> keep all constraints
            if not endpoint_records:
                filtered_constraints[endpoint] = constraints
                continue
            for prop, rule in constraints.items():
                if not rule:
                    continue
                violated = False
                counterexample = None
                for record in endpoint_records:
                    try:
                        context = self._build_test_case_context(
                            record
                        )
                        passed = engine.evaluate(
                            rule,
                            context
                        )
                    except Exception as e:
                        self.logger.debug(
                            f"Constraint evaluation failed: {rule} - {e}"
                        )
                        passed = False
                    if not passed:
                        violated = True
                        counterexample = {
                            "test_case_id": record.get(
                                "test_case_id"
                            ),
                            "context": self._minimize_context(
                                context,
                                prop
                            )
                        }
                        break
                if violated:
                    removed_constraints \
                        .setdefault(endpoint, {})[prop] = {
                            "rule": rule,
                            "invalid_example": counterexample
                        }

                    self.logger.info(
                        f"Removed static constraint "
                        f"{endpoint}::{prop}"
                    )

                else:
                    filtered_constraints[endpoint][prop] = rule
        self.static_constraints = filtered_constraints
        self.logger.info(
            f"Static verification removed "
            f"{sum(len(v) for v in removed_constraints.values())} "
            f"constraints"
        )
         # save removed constraints
        removed_file = (
            Path(self.project_dir)
            / "removed_static_constraints.json"
        )

        self._save_json_file(
            removed_file,
            removed_constraints
        )
        return removed_constraints

        
    
    def constraint_arbitration(self):
        # cache_file = Path(self.project_dir) / self.MAIN_CACHE
        # if cache_file.exists():
        #     self.logger.debug(f"Loading cached constraints from {cache_file}")
        #     cache = self._load_json_file(cache_file)
        #     self.constraints = cache
        #     return
        self.verify_static_constraints()
        constraints = self.merge_constraints()
        # Implement your arbitration logic here
        for endpoint, props in constraints.items():
            endpoint_constraints = [] # This will hold the final constraints for this endpoint after arbitration
            for prop, details in props.items():
                if details.get("spec") is None or details.get("runtime") is None:
                    continue
                spec_constraint = details.get("spec")
                runtime_constraint = details.get("runtime")
                final_constraint = details.get("final")
                # Example arbitration logic
                if final_constraint is not None:
                    continue
                else:
                    endpoint_constraints.append({
                        "property": prop,
                        "spec": spec_constraint,
                        "runtime": runtime_constraint
                    })
                    print(f"No clear final constraint for {endpoint} - {prop}. Spec: {spec_constraint}, Runtime: {runtime_constraint}")
            if len(endpoint_constraints) == 0:
                continue
            print(f"Arbitrating constraints for endpoint: {endpoint}")
            operation = self.operations.get(endpoint)
            if operation.successful_responses:
                flatten_responses = flatten_json_schema(operation.successful_responses.to_dict())
                data = []
                for idx, constraint in enumerate(endpoint_constraints, start=1):
                    data.append(f"#{idx}. \n Property: {constraint['property']}\n   - Spec Constraint: {constraint['spec']}\n   - Runtime Constraint: {constraint['runtime']}")

                params = {
                    "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}" if operation else endpoint,
                    "summary": operation.summary or operation.description or "",
                    "parameters": "\n".join([
                        f"- {k} : {v.to_human_readable()}"
                        for k, v in operation.parameters.items()
                    ]),
                    "responses": "\n".join([
                        f"- {k.replace("[]", "")} : {ItemProperties.from_dict(v).to_human_readable()}"
                        for k, v in flatten_responses.items()
                    ]),
                    "constraints": "\n".join(data)
                }
                data = self.arbitration.exec(**params)
                for item in data:
                    property = endpoint_constraints[item.id - 1]['property']
                    if item.answer == 1:
                        type = "Equivalent"
                    elif item.answer == 2:
                        type = "Subset"
                    elif item.answer == 3:
                        type = "Intersection"
                    elif item.answer == 4:
                        type = "Disjoint" 
                    self.constraints[endpoint][property]['type'] = type
        for endpoint, props in self.constraints.items():
            for prop, details in props.items():
                if 'type' not in details:
                    self.constraints[endpoint][prop]['type'] = "Unique"
                if details.get('type') == "Equivalent":
                    self.constraints[endpoint][prop]['final'] = details.get('spec') or details.get('runtime')
        self._save_constraints_to_cache()
    
    def _build_history_context(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Build DSLEngine evaluation context from one history record."""
        response_body = record.get("response",{}).get("content",{}).get("text")
        parsed_response = None
        if isinstance(response_body, str):
            try:
                parsed_response = json.loads(response_body)
            except json.JSONDecodeError:
                self.logger.debug("History response_body is not JSON string; using raw value")
                parsed_response = response_body
        else:
            parsed_response = response_body
        context: Dict[str, Any] = {"return": parsed_response if parsed_response is not None else {}}
        input_context: Dict[str, Any] = {}
        parameters = {}
        req = record.get("request", {})
        parameters.update(req.get("path_params", {}))
        for item in req.get("queryString", []):
            parameters[item["name"]] = item["value"]
        
        if isinstance(parameters, dict):
            input_context.update(parameters)

        request_body = req.get("request_body")
        if isinstance(request_body, dict):
            input_context.update(request_body)
        if input_context:
            context["input"] = input_context
        return context
    
    def _minimize_context(
        self,
        context: Dict[str, Any],
        prop: str,
    ) -> Dict[str, Any]:
        mini_context = {}
        if "input" in context:
            mini_context["input"] = context["input"]
        try:
            eval_context = DSLEvaluationContext(context)
            values = {}
            properties = [
                p.strip()
                for p in prop.split(",")
                if p.strip()
            ]
            for p in properties:
                try:
                    values[p] = eval_context.get(p)
                except Exception:
                    values[p] = None
            mini_context["return"] = values
        except Exception as e:
            mini_context["return"] = {
                "error": str(e)
            }

        return mini_context
    
    def verify_constraints(
        self,
        prop: str,
        details: Dict[str, Any],
        records: list[Dict[str, Any]]
    ) -> Dict[str, Any]:
        engine = DSLEngine()
        result = {
            "property": prop,
            "spec": {
                "rule": details.get("spec"),
                "valid": 0,
                "total": 0,
                "invalid_examples": [],
            },
            "runtime": {
                "rule": details.get("runtime"),
                "valid": 0,
                "total": 0,
                "invalid_examples": [],
            },
        }
        for rule_type in ("spec", "runtime"):
            rule = details.get(rule_type)
            if not rule:
                continue
            for idx, record in enumerate(records):
                try:
                    context = self._build_history_context(record)
                    passed = engine.evaluate(
                        rule,
                        context,
                    )
                except Exception as e:
                    print(str(e))
                    passed = False
                result[rule_type]["total"] += 1
                if passed:
                    result[rule_type]["valid"] += 1
                else:
                    result[rule_type]["invalid_examples"].append(
                        {
                            "index": idx,
                            "context":  self._minimize_context(
                                context,
                                prop
                            ),
                        }
                    )
        return result

    def constraint_counterfactual(self, base_url: Optional[str] = None, num_test_cases: int = 20):
        """Generate counterfactual test cases for each endpoint/property hypothesis."""
        if base_url is None and hasattr(self.spec_parser, "get_api_url"):
            base_url = self.spec_parser.get_api_url()

        if base_url is None:
            raise ValueError("base_url is required for counterfactual execution")

        counterfactual_results: Dict[str, Dict[str, Any]] = {}
        for endpoint, props in self.constraints.items():
            operation = self.operations.get(endpoint)
            if operation is None:
                print(f"Skipping counterfactual for unknown operation: {endpoint}")
                continue

            counterfactual_results[endpoint] = {}
            for prop, details in props.items():
                if details.get("type") == "Equivalent" or details.get("type") == "Unique":
                    print(f"Skipping counterfactual for {endpoint} - {prop} due to clear arbitration result.")
                    continue
                try:
                    hypothesis = HypothesisProperties(
                        name=prop,
                        hypothesis_1=details.get("spec"),
                        hypothesis_2=details.get("runtime"),
                        relation=details.get("type")
                    )
                except Exception as e:
                    print(details)
                print(f"Running counterfactual tests for {endpoint} - {prop}")
                executor = Executor(
                    api_url=base_url,
                    requestHeader= self.requestHeader,
                    strategy=Strategy.COUNTER_VALUE,
                    operation=operation,
                    cache_dir=self.project_dir,
                    model=self.model,
                    num_test_cases=num_test_cases,
                    context_pool=None,
                    hypothesis=hypothesis
                )

                entries = executor.exec()
                success_responses = [ 
                    entry
                    for entry in entries if isSuccessful(entry.get("response",{}).get("status",0)) 
                ]
                counterfactual_results[endpoint][prop] = {
                    "type": details.get("type"),
                    "spec": details.get("spec"),
                    "runtime": details.get("runtime"),
                    "results": success_responses,
                }
        self.counterfactual_results = counterfactual_results
        return counterfactual_results

    def constraint_review(
        self,
        base_url: Optional[str] = None,
        num_test_cases: int = 20,
    ):

        if (
            not hasattr(self, "counterfactual_results")
            or not self.counterfactual_results
        ):
            print("constraint_counterfactual")
            self.constraint_counterfactual(
                base_url=base_url,
                num_test_cases=num_test_cases,
            )

        review_results: Dict[str, Dict[str, Any]] = {}

        for endpoint, props in self.constraints.items():
            review_results[endpoint] = {}

            endpoint_info = self.operations.get(endpoint)

            if (
                endpoint_info
                and endpoint_info.successful_responses
            ):
                flatten_responses = flatten_json_schema(
                    endpoint_info.successful_responses.to_dict()
                )
            else:
                flatten_responses = {}

            for prop, details in props.items():

                counterfactual_data = (
                    self.counterfactual_results
                    .get(endpoint, {})
                    .get(prop, {})
                )

                entries = counterfactual_data.get("results", [])

                best_hypothesis = "unknown"

                if details.get("type") == "Equivalent":
                    best_hypothesis = "equal"
                    self.constraints[endpoint][prop]["final"] = (
                        details.get("spec")
                        or details.get("runtime")
                    )
                    continue

                if details.get("type") == "Unique":
                    if (
                        details.get("spec") is not None
                        and details.get("runtime") is None
                    ):
                        self.constraints[endpoint][prop]["final"] = (
                            details.get("spec")
                        )
                        best_hypothesis = "hypothesis_1"

                    elif (
                        details.get("runtime") is not None
                        and details.get("spec") is None
                    ):
                        self.constraints[endpoint][prop]["final"] = (
                            details.get("runtime")
                        )
                        best_hypothesis = "hypothesis_2"

                    continue

                verification_info = self.verify_constraints(
                    prop=prop,
                    details=details,
                    records=entries,
                )
                property_descriptions = []
                for p in [x.strip() for x in prop.split(",")]:
                    property_info = flatten_responses.get(p)
                    if property_info:
                        property_descriptions.append(
                            ItemProperties(
                                **property_info
                            ).to_human_readable()
                        )

                property_description = "\n".join(
                    property_descriptions
                )
                review_data = self.counterfactual_reviewer.exec(
                        endpoint=endpoint,
                        property=prop,
                        property_description=property_description,
                        hypothesis_1=details.get("spec"),
                        hypothesis_2=details.get("runtime"),
                        relation=details.get("type")
                        or "Unknown",
                        verification_info=verification_info,
                    )

                if review_data:
                    best_hypothesis = review_data

                if best_hypothesis == "hypothesis_1":
                    self.constraints[endpoint][prop]["final"] = (
                        details.get("spec")
                    )

                elif best_hypothesis == "hypothesis_2":
                    self.constraints[endpoint][prop]["final"] = (
                        details.get("runtime")
                    )

                elif best_hypothesis == "union":
                    self.constraints[endpoint][prop]["type"] = (
                        "Union"
                    )
                    self.constraints[endpoint][prop]["final"] = (
                        f"and({details.get('spec')}, "
                        f"{details.get('runtime')})"
                    )

                review_results[endpoint][prop] = {
                    "decision": best_hypothesis,
                    "counterfactual_count": len(entries),
                }

        self._save_constraints_to_cache()

        return review_results
    def _summarize_counterfactual_entries(self, entries: list[Dict[str, Any]], max_examples: int = 3) -> str:
        summaries = []
        for idx, entry in enumerate(entries[:max_examples], start=1):
            request = entry.get("request", {})
            response = entry.get("response", {})
            query = {item.get("name"): item.get("value") for item in request.get("queryString", [])}
            body = request.get("postData", {}).get("text", "")
            if len(body) > 400:
                body = body[:400] + "..."
            response_text = response.get("content", {}).get("text", "")
            if len(response_text) > 400:
                response_text = response_text[:400] + "..."
            summaries.append(
                f"{idx}. method={request.get('method')} path={request.get('path_template')} expected={entry.get('expected_code')} actual={response.get('status')}\n"
                f"   query={json.dumps(query, ensure_ascii=False)}\n"
                f"   body={body}\n"
                f"   response_status={response.get('status')} response_body={response_text}"
            )
        if len(entries) > max_examples:
            summaries.append(f"... plus {len(entries) - max_examples} more counterexamples")
        return "\n".join(summaries)

    def _build_counterfactual_description(self, prop: str, details: Dict[str, Any]) -> str:
        parts = [f"Property '{prop}'"]
        if details.get("type"):
            parts.append(f"relationship: {details['type']}")
        if details.get("spec") is not None:
            parts.append(f"spec constraint: {details['spec']}")
        if details.get("runtime") is not None:
            parts.append(f"runtime constraint: {details['runtime']}")
        if details.get("final") is not None:
            parts.append(f"final constraint: {details['final']}")
        return ". ".join(parts)

    def merge_constraints(self):
        merged = {}
        for endpoint in set(self.static_constraints) | set(self.dynamic_constraints):
            d1 = self.static_constraints.get(endpoint, {})
            d2 = self.dynamic_constraints.get(endpoint, {})

            merged[endpoint] = {}

            for prop in set(d1) | set(d2):
                spec = d1.get(prop)
                runtime = d2.get(prop)
                if isinstance(runtime, dict):
                    runtime = runtime.get("dslExpression")
                # Handle composite property: "a,b"
                if "," in prop:
                    parts = [p.strip() for p in prop.split(",")]

                    # Nếu spec có a,b nhưng runtime không có
                    if spec is not None and runtime is None:
                        runtime_parts = [d2.get(p) for p in parts]
                        runtime_parts = [x for x in runtime_parts if x]
                        if runtime_parts:
                            runtime =  f"and({', '.join( [ inv.get("dslExpression") for inv in runtime_parts])})"
                    # Nếu runtime có a,b nhưng spec không có
                    elif runtime is not None and spec is None:
                        spec_parts = [d1.get(p) for p in parts]
                        spec_parts = [x for x in spec_parts if x]
                        if spec_parts:
                            spec = f"and({', '.join(spec_parts)})"
                # Final logic
                if spec is None and runtime is not None:
                    final = runtime
                elif runtime is None and spec is not None:
                    final = spec
                else:
                    final = None

                merged[endpoint][prop] = {
                    "spec": spec,
                    "runtime": runtime,
                    "final": final
                }

        self.constraints = merged
        self._save_constraints_to_cache()

        return merged


