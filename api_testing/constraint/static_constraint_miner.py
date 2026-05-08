import copy
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from api_testing.constraint.evaluation import DSLEngine
from api_testing.constraint.evaluation.engine.evaluator import DSLTransformer
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.request_response_constraint import RequestResponseConstraint
from api_testing.prompts.response_constraints import ResponseConstraints
from api_testing.utils import flatten_json_schema
from api_testing.utils.graph import is_nested_path_end_with
from api_testing.utils.log import getLogger
from collections import defaultdict

def merge_list_of_dicts(dict_list):
    merged = defaultdict(list)
    
    for d in dict_list:
        for k, v in d.items():
            merged[k].append(v)
    
    return dict(merged)

class StaticConstraintMiner:
    """
    Mines static constraints from API specifications using LLM models.
    
    Extracts both request-response constraints and response property constraints
    from API operations, caching results for performance optimization.
    """
    
    # Cache file names
    MAIN_CACHE = "static_constraint_miner.json"
    REQUEST_RESPONSE_CACHE = "static_constraint_miner_request_response.json"
    RESPONSE_PROPERTIES_CACHE = "static_constraint_miner_response_properties.json"
    
    def __init__(
        self,
        spec_parser: Any,
        model: Optional[Any] = None,
        embedding_model: Optional[Any] = None,
        cache_dir: Optional[str] = None
    ) -> None:
        """
        Initialize the constraint miner.
        
        Args:
            spec_parser: Parser for API specifications containing operations
            model: LLM model for constraint generation
            embedding_model: Optional embedding model (reserved for future use)
            cache_dir: Directory for caching constraint results
            
        Raises:
            ValueError: If required parameters are None
        """
        if spec_parser is None or cache_dir is None:
            raise ValueError("spec_parser and cache_dir are required")
            
        self.spec_parser = spec_parser
        self.model = model
        self.embedding_model = embedding_model
        self.cache_dir = Path(cache_dir)
        self.logger = getLogger()
        self.operations = spec_parser.operations
        self.constraints: Dict[str, Any] = {}
        self.response_constraint = ResponseConstraints(llm=model)
        self.request_response_constraint = RequestResponseConstraint(llm=model)

    def mining(self) -> Dict[str, Dict[str, str]]:
        """
        Mine all constraint types and aggregate results.
        
        Returns:
            ConstraintResult: Aggregated constraints with request-response and response property constraints
            
        Raises:
            Exception: If constraint mining operations fail
        """
        cache_file = self.cache_dir / self.MAIN_CACHE
        
        if cache_file.exists():
            self.logger.debug(f"Loading cached request-response constraints from {cache_file}")
            cache = self._load_json_file(cache_file)
            return cache.get("common", {})
        try:
            self.logger.info("Starting constraint mining process")
            req_res_constraints = self._mine_request_response_constraints()
            res_constraints = self._mine_response_properties_constraints()
            
            common_constraints = self._aggregate_constraints(req_res_constraints, res_constraints)
            
            self.constraints = {
                "request_response": req_res_constraints,
                "response_properties": res_constraints,
                "common": common_constraints
            }
            
            self._save_constraints_to_cache()
            self.logger.info("Constraint mining completed successfully")
            
            return common_constraints
        except Exception as e:
            self.logger.error(f"Error during constraint mining: {str(e)}")
            raise
    
    def verify_constraints(self, history) -> bool:
        """
        Verify the validity of mined constraints against historical data.

        Args:
            history: Historical verification data. This may be a list of history
                records, a dictionary with records, or a file path to a JSON file.

        Returns:
            bool: True if all applicable constraints pass on the history data,
                False if any constraint fails.
        """
        if not self.constraints:
            cache_file = self.cache_dir / self.MAIN_CACHE
            if cache_file.exists():
                self.constraints = self._load_json_file(cache_file)
            else:
                self.logger.warning("No cached constraints found, mining constraints before verification")
                self.mining()

        history_records = self._normalize_history(history)
        if history_records is None:
            self.logger.error("History input could not be parsed for verification")
            return False

        engine = DSLEngine()
        all_constraints = self.constraints.get("common", {})
        if not all_constraints:
            self.logger.warning("No common constraints available for verification")
            return False

        final_results = dict(defaultdict(list))
        for record in history_records:
            operation_id = record.get("operation_id") or record.get("operationId")
            if not operation_id:
                self.logger.debug("Skipping history record without operation_id")
                continue

            rules = all_constraints.get(operation_id)
            if not rules:
                self.logger.debug(f"No constraints found for operation_id={operation_id}")
                continue

            context = self._build_history_context(record)
            results = engine.validate(rules, context)
            final_results.setdefault(operation_id, []).append(results)
            for rule_path, passed in results.items():
                if not passed and rule_path == "return.holiday.id":
                    self.logger.warning(
                            f"Constraint verification failed for operation_id={operation_id}, "
                            f"path={rule_path}, rules={rules.get(rule_path)}, history_record={record.get('test_case_id', 'unknown')}"
                        )
        def filter_always_true(merged_dict):
            return {
                k: v
                for k, v in merged_dict.items()
                if all(v)
            }
        for op_id, results in final_results.items():
            merged_results = merge_list_of_dicts(results)
            truekeys = list(filter_always_true(merged_results).keys())
            all_constraints_passed = { k: v for k, v in all_constraints.get(op_id, {}).items() if k in truekeys }
            self.constraints["final_verification"] = self.constraints.get("final_verification", {})
            self.constraints["final_verification"][op_id] = all_constraints_passed
        
        self._save_constraints_to_cache()
        return False

    def _normalize_history(self, history):
        """Normalize history input into a list of records."""
        if isinstance(history, (str, Path)):
            try:
                with open(Path(history), "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load history file {history}: {e}")
                return None
        else:
            data = history

        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            return data

        self.logger.error("Unsupported history data format; expected list or dict")
        return None

    def _build_history_context(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Build DSLEngine evaluation context from one history record."""
        response_body = record.get("response_body")
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

        parameters = record.get("parameters")
        if isinstance(parameters, dict):
            input_context.update(parameters)

        request_body = record.get("request_body")
        if isinstance(request_body, dict):
            input_context.update(request_body)

        if input_context:
            context["input"] = input_context

        return context
    
    def _aggregate_constraints(
        self,
        req_res_constraints: Dict[str, List[Dict[str, Any]]],
        res_constraints: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, str]]:
        """
        Aggregate request-response and response property constraints.
        
        Args:
            req_res_constraints: Request-response constraints by operation UUID
            res_constraints: Response property constraints by operation UUID
            
        Returns:
            Dictionary of aggregated constraints by operation UUID
        """
        aggregated = {}
        
        for uuid in self.operations.keys():
            aggregated[uuid] = dict(res_constraints.get(uuid, {}))
            
            for req_res in req_res_constraints.get(uuid, []):
                self._merge_constraint(aggregated[uuid], req_res)
        
        return aggregated

    @staticmethod
    def _merge_constraint(
        target: Dict[str, str],
        constraint: Dict[str, Any]
    ) -> None:
        """
        Merge a constraint into the target dictionary.
        
        Args:
            target: Target constraint dictionary to merge into
            constraint: Constraint to merge
        """
        property_name = constraint.get("property", "")
        predicate = constraint.get("predicate", "")
        
        for prop in map(str.strip, property_name.split(",")):
            if not prop:
                continue
                
            prop = prop if "return" in prop else f"return.{prop}"
            
            if prop in target:
                target[prop] = f"and({target[prop]},{predicate})"
            else:
                target[prop] = predicate

    def request_response_constraints(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Public method for backward compatibility.
        
        Returns:
            Request-response constraints
        """
        return self._mine_request_response_constraints()

    def _mine_request_response_constraints(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Mine constraints between request parameters and response properties.
        
        Uses cache if available to improve performance.
        
        Returns:
            Dictionary mapping operation UUIDs to list of request-response constraints
        """
        cache_file = self.cache_dir / self.REQUEST_RESPONSE_CACHE
        
        if cache_file.exists():
            self.logger.debug(f"Loading cached request-response constraints from {cache_file}")
            return self._load_json_file(cache_file)
        
        self.logger.info("Mining request-response constraints")
        req_res_constraints: Dict[str, List[Dict[str, Any]]] = {}
        
        for opt in self.operations.values():
            if not opt.successful_responses:
                continue
            
            try:
                constraints = self._extract_request_response_constraints(opt)
                if constraints:
                    req_res_constraints[opt.uuid] = constraints
            except Exception as e:
                self.logger.warning(f"Failed to mine constraints for {opt.uuid}: {str(e)}")
        
        self._save_json_file(cache_file, req_res_constraints)
        return req_res_constraints

    def _extract_request_response_constraints(self, operation: Any) -> List[Dict[str, Any]]:
        """
        Extract request-response constraints for a single operation.
        
        Args:
            operation: API operation to process
            
        Returns:
            List of constraints extracted for the operation
        """
        main_response = self._get_main_response_text(operation)
        other_responses = self._get_other_responses_text(operation)
        params_text = self._format_parameters_text(operation)
        
        llm_args = {
            "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
            "summary": operation.summary or operation.description or "",
            "params": params_text,
            "main_response": main_response,
            "other_responses": other_responses
        }
        
        response = self.request_response_constraint.exec(**llm_args)
        constraints = response.get("constraints", [])
        
        return self._map_constraints_to_response_paths(
            operation,
            constraints
        )

    def _get_main_response_text(self, operation: Any) -> str:
        """Extract and clean main response schema text."""
        successful_responses = operation.successful_responses
        main_xrefs = successful_responses.xrefs
        
        if main_xrefs is None:
            main_xrefs = "Response"  # fallback name if xrefs is missing
            # return ""
        
        schema_copy = copy.deepcopy(successful_responses)
        schema_copy.xrefs = None
        cleaned_text = self._normalize_schema_text(schema_copy.to_human_readable())
        
        return f"{main_xrefs}: {cleaned_text}"

    def _get_other_responses_text(self, operation: Any) -> str:
        """Extract and clean other response schemas."""
        main_xrefs = operation.successful_responses.xrefs
        other_responses = {
            k: v for k, v in operation.schemas.items() 
            if k != main_xrefs
        }
        
        result_items = []
        for schema_name, schema in other_responses.items():
            schema_copy = copy.deepcopy(schema)
            schema_copy.xrefs = None
            cleaned_text = self._normalize_schema_text(schema_copy.to_human_readable())
            result_items.append(f"- {schema_name}: {cleaned_text}")
        
        return "\n".join(result_items)

    @staticmethod
    def _normalize_schema_text(text: str) -> str:
        """Normalize schema text by removing extra whitespace and escape sequences."""
        text = text.replace('\\n', '').replace('\n', '')
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'\\+', '', text)
        return text

    @staticmethod
    def _format_parameters_text(operation: Any) -> str:
        """Format operation parameters as readable text."""
        param_lines = [
            f"- {k}::parameter : {v.to_human_readable()}"
            for k, v in operation.parameters.items()
        ]
        
        request_body_lines = [
            f"- {k}::requestBody : {ItemProperties.from_dict(v).to_human_readable()}"
            for k, v in operation.get_request_body().items()
        ]
        
        return "\n".join(param_lines + request_body_lines)

    def _map_constraints_to_response_paths(
        self,
        operation: Any,
        constraints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map constraints to actual response property paths.
        
        Args:
            operation: API operation
            constraints: Constraints from LLM
            
        Returns:
            List of constraints with mapped response paths
        """
        result = []
        flatten_responses = flatten_json_schema(operation.successful_responses.to_dict())
        
        for constraint in constraints:
            property_name = constraint.get("property", "")
            if not property_name:
                continue
            
            for response_path, props in flatten_responses.items():
                for property_part in map(str.strip, property_name.split(",")):
                    property_part = property_part.replace("return.", "").strip()
                    if is_nested_path_end_with(response_path, property_part):
                        predicate = constraint.get("predicate", "").replace(property_part, f"{response_path}")
                        # print(f"Mapping constraint property '{property_part}' to response path '{response_path}' with predicate '{predicate}'")
                        result.append({
                            "property": f"return.{response_path}",
                            "predicate": predicate,
                            "parameter": constraint.get("parameter"),
                        })
                        break
        
        return result
 
    def response_properties_constraints(self) -> Dict[str, Dict[str, Any]]:
        """
        Public method for backward compatibility.
        
        Returns:
            Response property constraints
        """
        return self._mine_response_properties_constraints()

    def _mine_response_properties_constraints(self) -> Dict[str, Dict[str, Any]]:
        """
        Mine constraints within response properties of each schema.
        
        Uses cache if available to improve performance.
        
        Returns:
            Dictionary mapping operation UUIDs to response property constraints
        """
        cache_file = self.cache_dir / self.RESPONSE_PROPERTIES_CACHE
        
        if cache_file.exists():
            self.logger.debug(f"Loading cached response property constraints from {cache_file}")
            return self._load_json_file(cache_file)
        
        self.logger.info("Mining response property constraints")
        
        # Extract all unique schemas
        schemas = {
            k: v for opt in self.operations.values()
            for k, v in opt.schemas.items()
        }
        
        self.logger.debug(f"Processing {len(schemas)} unique schemas")
        schema_constraints = self._extract_schema_constraints(schemas)
        
        # Map schema constraints to operation constraints
        final_constraints = self._map_schema_to_operation_constraints(schema_constraints)
        
        self._save_json_file(cache_file, final_constraints)
        return final_constraints

    def _extract_schema_constraints(
        self,
        schemas: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extract constraints for each schema.
        
        Args:
            schemas: Dictionary of schemas to process
            
        Returns:
            Dictionary mapping schema names to their constraints
        """
        schema_constraints = {}
        
        for schema_name, schema in schemas.items():
            try:
                flattened_schema = flatten_json_schema(schema.to_dict())
                
                if not flattened_schema:
                    continue
                
                # Format schema properties for LLM
                flatten_texts = [
                    f"- {k}: {ItemProperties.from_dict(v).to_human_readable()}"
                    for k, v in flattened_schema.items()
                    if v is not None
                ]
                
                if not flatten_texts:
                    continue
                
                llm_args = {
                    "schema": schema_name,
                    "properties": "\n".join(flatten_texts)
                }
                
                response = self.response_constraint.exec(**llm_args)
                schema_constraints[schema_name] = response
                
            except Exception as e:
                self.logger.warning(f"Failed to extract constraints for schema {schema_name}: {str(e)}")
        
        return schema_constraints

    def _map_schema_to_operation_constraints(
        self,
        schema_constraints: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Map schema-level constraints to operation-level constraints.
        
        Args:
            schema_constraints: Constraints extracted at schema level
            
        Returns:
            Dictionary mapping operation UUIDs to their constraints
        """
        final_constraints: Dict[str, Dict[str, Any]] = {}
        
        for opt in self.operations.values():
            final_constraints[opt.uuid] = {}
            
            if not opt.successful_responses:
                continue
            
            flatten_responses = flatten_json_schema(opt.successful_responses.to_dict())
            
            for response_path, response_props in flatten_responses.items():
                response_schema = response_props.get("xrefs")
                
                if response_schema not in schema_constraints:
                    continue
                
                schema_rules = schema_constraints[response_schema]
                
                for attribute_name, attribute_rules in schema_rules.items():
                    if is_nested_path_end_with(response_path, attribute_name):
                        attribute_rules = attribute_rules.replace(attribute_name, f"return.{response_path}")
                        final_constraints[opt.uuid][f"return.{response_path}"] = attribute_rules
        
        return final_constraints

    def _save_constraints_to_cache(self) -> None:
        """Save all constraints to main cache file."""
        cache_file = self.cache_dir / self.MAIN_CACHE
        self._save_json_file(cache_file, self.constraints)
        self.logger.debug(f"Constraints saved to {cache_file}")

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