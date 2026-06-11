
from collections import defaultdict
from importlib import resources
import json
import os
from pathlib import Path
import random
import re
from typing import Any, Dict, List, Optional
import copy
from api_testing.constraint.dynamic_constraints.decls_file import Comparability, DeclsFile
from api_testing.constraint.dynamic_constraints.invariant_extractor import InvariantExtractor
from api_testing.constraint.dynamic_constraints.test_case import TestCase
from api_testing.constraint.dynamic_constraints.utils.csv_manager import read_csv
from api_testing.constraint.dynamic_constraints.utils.test_case_file_manager import TestCaseFileManager
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.invariant_classification import InvariantClassification
from api_testing.utils import flatten_json_schema
from api_testing.utils.graph import is_nested_path_end_with
from api_testing.utils.log import getLogger
from itertools import groupby

def remove_outer_parens(s: str):
    s = s.strip()
    if s.startswith("(") and s.endswith(")"):
        return s[1:-1]   # chỉ cắt 1 ký tự mỗi bên
    return s

def normalize_variable_name(var: str) -> str:
    var = var.strip()
    # size(x) -> x
    var = re.sub(r"size\((.*?)\)", r"\1", var)
    # remove array notation
    var = var.replace("[..]", "")
    var = re.sub(r"\[\d+\]", "", var)
    # remove arithmetic suffix/prefix
    var = re.sub(r"\s*[-+*/]\s*\d+(\.\d+)?$", "", var)
    return var.strip()

def group_by_endpoint(final_invariants):
    grouped = defaultdict(list)
    
    for item in final_invariants:
        endpoint = item.get("endpoint", "")
        grouped[endpoint].append(item)

    return dict(grouped)

def group_invariants_by_variable(
    data: Dict[str, List[Dict]]
) -> Dict[str, Dict[str, List[Dict]]]:
    """
    Group invariants theo:
    endpoint -> variable -> list[invariants]
    """
    result = {}

    for endpoint, invariants in data.items():
        var_group = defaultdict(list) 

        for inv in invariants:
            variable = ",".join(inv.get("variable"))
            var_group[variable].append(inv)

        result[endpoint] = dict(var_group)

    return result

class DynamicConstraintMiner:
    """Dynamic constraint miner that maps API spec operations to Daikon .decls/.dtrace."""
    DECLS_FILENAME = "test_cases.decls"
    DTRACE_FILENAME = "test_cases.dtrace"
    INVARIANTS_FILENAME = "invariants.csv"
    MAIN_CACHE = "dynamic_constraint_miner.json"

    def __init__(self, spec_parser=None, model=None, cache_dir=None):
        self.spec_parser = spec_parser
        self.model = model
        self.cache_dir = Path(cache_dir or '.')
        self.cache_file = self.cache_dir / self.MAIN_CACHE
        self.logger = getLogger(__name__)

        if not self.spec_parser or not hasattr(self.spec_parser, "operations"):
            raise ValueError("spec_parser with operations is required")

        self.operations = self.spec_parser.operations
        self.decls_file: Optional[DeclsFile] = None
        self.extractor = InvariantExtractor(cache_dir=self.cache_dir)
        self._invariant_kinds = self._load_invariant_kinds()

        self.classifier = InvariantClassification(llm=self.model)
        
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
        # test_cases = random.sample(test_cases, 50)
        self.generate_dtrace_file(test_cases, self._cache_path(self.DTRACE_FILENAME))

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
        
    def extract_invariants(self) -> Path:
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
        invariant_file  = os.path.join(self.cache_dir, self.INVARIANTS_FILENAME)
        # if not os.path.exists(invariant_file):
        #     self.logger.info(f"Reusing existing invariants file: {invariant_file}")
            # return Path(invariant_file)
        self.extractor.extract_invariants(
            decls_path=decls_path,
            dtrace_path=dtrace_path,
        )
        invariants = read_csv(invariant_file, delimiter=";")
        headers = invariants[0] if invariants else []
        final_invariants = []
        for i, row in enumerate(invariants[1:], start=1):
            invariant_dict = dict(zip(headers, row))
            if ":::ENTER" in invariant_dict.get("pptname"):
                continue
            pptname = invariant_dict.get("pptname", "")
            variables = invariant_dict.get("variables", "")
            variables = remove_outer_parens(variables).split(",") if variables else []
            invariant_dict["dslExpression"] = invariant_dict["dslExpression"].replace(
                "[..]",
                "[]"
            )
            for item in map(str.strip, variables):
                if "return" not in item:
                    continue
                variable = normalize_variable_name(item)
                match_id = re.search(r"&(\d{3})&", pptname)
                output_container_path = None
                if match_id:
                    match_args = re.search(r"\(([^()]*)\)", pptname)
                    index_end = match_args.start() if match_args else len(pptname)
                    output_container_path = (
                        pptname[match_id.start() + 5:index_end]
                        .replace("&", ".")
                    )
                    original_variable = variable
                    variable = variable.replace(
                        "return",
                        f"return.{output_container_path}"
                    )
                    invariant_dict["invariant"] = invariant_dict["invariant"].replace(
                        original_variable,
                        variable
                    )
                    invariant_dict["dslExpression"] = invariant_dict["dslExpression"].replace(
                        original_variable,
                        variable
                    )
                    invariant_dict["variables"] = invariant_dict["variables"].replace(
                        original_variable,
                        variable
                    )
                
                if  "return.array" in variable:
                    variable = variable.replace("return.array", "return")
                    invariant_dict["invariant"] = invariant_dict["invariant"].replace(
                        "return.array",
                        variable
                    )
                    invariant_dict["dslExpression"] = invariant_dict["dslExpression"].replace(
                        "return.array",
                        variable
                    )


                invariant_dict.setdefault("variable", []).append(variable)
                invariant_dict.setdefault(
                    "response_container_path",
                    output_container_path
                )
            endpoint = invariant_dict.get("pptname", "").split("&")[0]
            invariant_dict["endpoint"] = endpoint
            final_invariants.append(invariant_dict)

        return group_by_endpoint(final_invariants)

    def mining(self) -> Dict[str, Path]:
        """Run the full dynamic mining workflow and return generated artifact paths."""
        cache_file = self.cache_dir / self.MAIN_CACHE
        if cache_file.exists():
            self.logger.debug(f"Loading cached request-response constraints from {cache_file}")
            cache = self._load_json_file(cache_file)
            return cache.get("constraints", {})
        
        self.extract_decls_classes()
        self.extract_dtraces()
        raw_invariants = self.extract_invariants()
        invariants = self._map_invariant_to_response_paths(raw_invariants) 
        invariants = self.classify_invariants(invariants)

        group_invariants = group_invariants_by_variable(invariants)
        final_invariants = {}
        for endpoint, invariants in group_invariants.items():
            final_invariants[endpoint] = {}

            for property, invariant_list in invariants.items():
                if not invariant_list:
                    final_invariants[endpoint][property] = None
                    continue

                if len(invariant_list) == 1:
                    final_invariants[endpoint][property] = {
                        "invariant": invariant_list[0].get("invariant"),
                        "dslExpression": invariant_list[0].get("dslExpression"),
                    }
                else:
                    final_invariants[endpoint][property] = {
                        "invariant": "and(" + ",".join(
                            item.get("invariant", "") for item in invariant_list
                        ) + ")",
                        "dslExpression": "and(" + ",".join(
                            item.get("dslExpression", "") for item in invariant_list
                        ) + ")",
                    }

        self.constraints = {
            "raw": raw_invariants,
            "group_invariants": group_invariants,
            "constraints": final_invariants
        }
        self._save_constraints_to_cache()
        return final_invariants
    
    def _map_invariant_to_response_paths(self, invariants):
        final_invariants = {}

        for opt in self.operations.values():
            if not opt.successful_responses:
                continue
            invariants_for_opt = invariants.get(opt.uuid, [])
            final_invariants[opt.uuid] = []

            flatten_responses = flatten_json_schema(
                opt.successful_responses.to_dict()
            )
            for invariant in invariants_for_opt:
                new_invariant = copy.deepcopy(invariant)
                mapped_variables = []
                for variable in invariant.get("variable", []):
                    mapped_variable = variable

                    for response_path in flatten_responses.keys():
                        if variable == "return":
                            mapped_variable = f"return{response_path}" if response_path.startswith("[]") else f"return.{response_path}"
                            new_invariant["invariant"] = (
                                new_invariant["invariant"]
                                .replace(variable, mapped_variable)
                            )
                            new_invariant["dslExpression"]=(
                                new_invariant["dslExpression"]
                                .replace(variable, mapped_variable)
                            )

                        elif is_nested_path_end_with(
                            response_path,
                            variable.replace("return.","").replace("return", ""),
                            equal=True
                        ) :
                            mapped_variable = f"return{response_path}" if response_path.startswith("[]") else f"return.{response_path}"
                            new_invariant["invariant"] = (
                                new_invariant["invariant"]
                                .replace(variable, mapped_variable)
                            )
                            new_invariant["dslExpression"]=(
                                new_invariant["dslExpression"]
                                .replace(variable, mapped_variable)
                            )
                            break

                    mapped_variables.append(mapped_variable)

                new_invariant["variable"] = mapped_variables
                final_invariants[opt.uuid].append(new_invariant)

        return final_invariants

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
    


    def classify_invariants(
        self, invariants: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Classify invariants using the InvariantClassifier."""
        classified_invariants = {}
        for endpoint, inv_list in invariants.items():
            classified_invariants[endpoint] = []
            self.logger.info(f"Classifying invariants for endpoint: {endpoint} with {len(inv_list)} invariants")
            data = []
            if len(inv_list) == 0: 
                continue
            for i, inv in enumerate(inv_list): 
                self.logger.debug(f"Classifying invariant: {inv}")
                params = {
                    "invariant": inv.get("invariant"),
                    "invariant_type": inv.get("invariantType"),  
                    "invariant_description": self._invariant_kinds.get(inv.get("invariantType", ""), "No description available."),
                    "variables": inv.get("variables", ""),
                    "endpoint": inv.get("endpoint", ""),
                    "response_container_path": inv.get("response_container_path", ""),
                    "spec_excerpt": "",  # You can enhance this by providing relevant spec excerpts
                    "examples_block": [],  # Optionally provide examples for the classifi er   
                    "evidence_checks_block": [],  # Optionally provide evidence checks for the classifier
                }
                str = f"""#{i+1}: Invariant: {params['invariant']}
Invariant Type: {params['invariant_type']} 
Invariant description: {params['invariant_description']}
The return fields refer to the path {params['response_container_path'] or "__ROOT__"} in the response body ."""
                data.append(str)
                # Here you would call self.classifier.exec() with the appropriate parameters
            operation = self.operations.get(endpoint)
            flatten_responses = flatten_json_schema(operation.successful_responses.to_dict())

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
                "invariants": "\n".join(data)
            }
            classified = self.classifier.exec(**params)
            for item in classified:
                invariant = inv_list[item.id-1]
                if item.classification == "true-positive":
                    classified_invariants[endpoint].append(invariant)
        return classified_invariants
    
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
    
    def _path_matches_endpoint(self, endpoint_pattern: str, request_path: str) -> bool:
        return endpoint_pattern.rstrip("/").lower() == request_path.rstrip("/").lower()
    
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
            print(len(test_cases))
            for test_case in test_cases:
                if test_case_count % 50 == 0:
                    self.logger.info(f"Generated dtrace for {test_case_count} test cases")

                test_case_count += 1
                # test_case.path = test_case.path.replace(self.decls_file.common_path, "") # only get relative path

                for decls_class in self.decls_file.decls_classes:
                    test_case_path = f"{test_case.http_method.lower()}-{test_case.path}"
                    if test_case_path == "post-/projects":
                        print(test_case_path,decls_class.class_name)
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
   
    def mapping_invariant_to_dsl(self, invariant: str) -> str:
        if not invariant or not isinstance(invariant, str):
            return invariant

        s = invariant.strip()

        # -----------------------------------------
        # equality
        # X == Y
        # -----------------------------------------
        m = re.match(r"^(.+?)\s*==\s*(.+?)$", s)
        if m:
            return f"eq({m.group(1).strip()},{m.group(2).strip()})"

        # -----------------------------------------
        # >=
        # -----------------------------------------
        m = re.match(r"^(.+?)\s*>=\s*(.+?)$", s)
        if m:
            return f"gte({m.group(1).strip()},{m.group(2).strip()})"

        # -----------------------------------------
        # >
        # -----------------------------------------
        m = re.match(r"^(.+?)\s*>\s*(.+?)$", s)
        if m:
            return f"gt({m.group(1).strip()},{m.group(2).strip()})"


        # -----------------------------------------
        # <=
        # -----------------------------------------
        m = re.match(r"^(.+?)\s*<=\s*(.+?)$", s)
        if m:
            return f"lte({m.group(1).strip()},{m.group(2).strip()})"
        
        # -----------------------------------------
        # <
        # -----------------------------------------
        m = re.match(r"^(.+?)\s*<\s*(.+?)$", s)
        if m:
            return f"lt({m.group(1).strip()},{m.group(2).strip()})"

        # -----------------------------------------
        # substring relation
        # A is a substring of B
        # -----------------------------------------
        m = re.match(
            r"^(.+?)\s+is a substring of\s+(.+?)$",
            s,
            re.IGNORECASE,
        )
        if m:
            return f"substring({m.group(1).strip()},{m.group(2).strip()})"

        # -----------------------------------------
        # Timestamp
        # -----------------------------------------
        m = re.match(
            r"^(.+?)\s+is\s+Timestamp(?:\.\s*Format:.*)?$",
            s,
            re.IGNORECASE,
        )
        if m:
            return f"isTimestamp({m.group(1).strip()})"

        # -----------------------------------------
        # Date
        # -----------------------------------------
        m = re.match(
            r"^(.+?)\s+is\s+a?\s*Date(?:\.\s*Format:.*)?$",
            s,
            re.IGNORECASE,
        )
        if m:
            return f"isDate({m.group(1).strip()})"

        # -----------------------------------------
        # Email
        # -----------------------------------------
        m = re.match(r"^(.+?)\s+is\s+Email$", s, re.IGNORECASE)
        if m:
            return f"isEmail({m.group(1).strip()})"

        # -----------------------------------------
        # URL
        # -----------------------------------------
        m = re.match(r"^(.+?)\s+is\s+Url$", s, re.IGNORECASE)
        if m:
            return f"isURL({m.group(1).strip()})"

        # -----------------------------------------
        # LENGTH(x)==N
        # -----------------------------------------
        m = re.match(
            r"^(?:LENGTH|length)\((.+?)\)\s*==\s*(\d+)$",
            s,
            re.IGNORECASE,
        )
        if m:
            return f"eq(sizeOf({m.group(1).strip()}),{m.group(2)})"

        # -----------------------------------------
        # All elements have LENGTH=N
        # -----------------------------------------
        m = re.match(
            r"^All the elements of\s+(.+?)\s+have LENGTH\s*=\s*(\d+)$",
            s,
            re.IGNORECASE,
        )
        if m:
            return f"eq(sizeOf(element),{m.group(2)})"

        # -----------------------------------------
        # one of {a,b,c}
        # -----------------------------------------
        m = re.match(
            r"^(.+?)\s+one of\s*\{(.+?)\}$",
            s,
            re.IGNORECASE,
        )
        if m:
            path = m.group(1).strip()
            values = [v.strip() for v in re.split(r",|;", m.group(2))]
            values = [
                v if re.match(r"^-?\d+$", v) else f'"{v}"'
                for v in values
            ]
            return f"contains([{', '.join(values)}], {path})"

        # -----------------------------------------
        # keep existing contains(...)
        # -----------------------------------------
        if s.startswith("contains("):
            return s

        # -----------------------------------------
        # keep existing logical expressions
        # and(...)
        # or(...)
        # not(...)
        # -----------------------------------------
        if re.match(r"^(and|or|not)\s*\(", s):
            return s

        return s