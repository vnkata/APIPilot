import hashlib
import json
import os
import random
from typing import Dict, List, Optional, Set, Tuple

from api_testing.inputs.fuzz_strategy import FuzzStrategy
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.semantic_oracle_judge import SemanticOracleJudge
from api_testing.utils import get_body_combinations, get_combinations
from api_testing.utils.common import remove_nulls
from typing import Any, Dict


def unflatten_dict(flat_dict: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
    """
    Convert a flattened dictionary with dot-separated keys back into a nested dictionary.

    Example:
        {"a.b.c": 1, "a.b.d": 2}
        → {"a": {"b": {"c": 1, "d": 2}}}
    """
    nested: Dict[str, Any] = {}

    for path, value in flat_dict.items():
        parts = path.split(sep)
        current = nested

        # Traverse or create nested structure
        for key in parts[:-1]:
            current = current.setdefault(key, {})

        # Assign the leaf value
        current[parts[-1]] = value

    return nested

def has_llm_placeholder(obj):

    if isinstance(obj, dict):
        for v in obj.values():
            if has_llm_placeholder(v):
                return True

    elif isinstance(obj, list):
        for v in obj:
            if has_llm_placeholder(v):
                return True

    elif isinstance(obj, str):
        if v := obj:
            return v == "**LLMGenerator**" or v == "**LLMGenerator**::invalid"

    return False

class NaiveValueGenerator:
    def __init__(
        self,
        operation: "OperationProperties",
        parameters: Dict[str, "ParameterProperties"],
        request_body: Dict[str, "ItemProperties"],
        model=None,
        num_test_cases=1,
        cache_dir: str = ".",
        context_pool=None,
        mutation_ratio=0.0,
    ):
        self.operation = operation
        self.parameters = parameters
        self.request_body = request_body
        self.model = model
        self.num_test_cases = num_test_cases
        self.cache_dir = cache_dir
        self.context_pool = context_pool
        self.mutation_ratio = mutation_ratio
        self.combination_cache = None
        self.semantic_oracle_judge = SemanticOracleJudge(llm=model)

    def load_cache(self):
        if self.combination_cache is not None:
            return self.combination_cache
        CACHE_FILE = os.path.join(self.cache_dir, "combination.json")
        cache = {}
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}
        return cache

    def __get_combination_parameters(self, parameters):
        parameter_label = parameters.keys()
        parameter_required_label = {k for k, v in parameters.items() if v.required}
        params_combinations = get_combinations(
            parameter_label, parameter_required_label
        )
        return params_combinations

    def __get_combination_request_body__(self, request_body):
        request_body_label = request_body.keys()
        request_body_required_label = {
            k
            for k, v in request_body.items()
            if v.nullable is not None and v.nullable == False
        }
        request_body_combinations = get_combinations(
            request_body_label, request_body_required_label
        )
        return request_body_combinations
    
    def exec(self):
        # process parameters
        cache = self.load_cache()
        if self.operation.uuid in cache:
            param_combos = cache.get(self.operation.uuid, {}).get("parameters", [])
            body_combos = cache.get(self.operation.uuid, {}).get("requestBody", [])
        else:
            param_combos = self.__get_combination_parameters(self.parameters)
            body_combos = self.__get_combination_request_body__(self.request_body)
            cache[self.operation.uuid] = {
                "parameters": param_combos,
                "requestBody": body_combos,
            }
            # save cache
            CACHE_FILE = os.path.join(self.cache_dir, "combination.json")
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        
        required_params = [
            n for n, p in self.parameters.items() if getattr(p, "required", False)
        ]
        path_params = [
            name for name, p in self.parameters.items()
            if getattr(p, "in_value", None) == "path"
        ]
        data = []
        path_field_resources = {
            field: [ r.get("resource") for r in  self.parameters.get(field).strategy.genParameters.get("pool",[])]
            for field in path_params
        }
        self.context_pool.set_priority_resources(path_field_resources.values())

        def generate_fields(
            field_map: Dict[str, Any], selected_fields: List[str], should_mutate=False
        ) -> Tuple[Dict[str, Any], bool]:
            """Generate a dict of values for selected fields. Return (generated_data, is_mutated)."""
            generated, mutated = {}, False
            # path_params
            
            for name in selected_fields:
                if name is None:
                    continue
                field = field_map.get(name)
                if not field or not field.strategy.type:
                    continue
                val = None
                try:
                    if field.strategy.type == "LLMGenerator":
                        val = "**LLMGenerator**"
                    else:
                        val = (
                            field.generator.next_value_as_string()
                            if callable(getattr(field.generator, "next_value_as_string", None))
                            else field.generator.next_value(context_pool=self.context_pool)
                        )

                    if should_mutate and random.random() < self.mutation_ratio:
                        strategy = random.choice(list(FuzzStrategy)).value
                        if field.strategy.type == "LLMGenerator":
                            val = "**LLMGenerator**"
                        else: 
                            val = field.generator.next_fuzz_value(
                                strategy=strategy, context_pool=self.context_pool
                            )
                        mutated = True
                except:
                    val = None
                generated[name] = val

            return generated, mutated

        for i in range(self.num_test_cases):
        
        
            # --- Select parameters ---
            params_selected = (
                required_params
                if (i == 0 and required_params)
                else random.choice(param_combos)
            )
            body_selected = random.choice(body_combos)
            should_mutate = random.random() < self.mutation_ratio
            # --- Generate parameter values ---
            params, params_mutated = generate_fields(self.parameters, params_selected, should_mutate)
            body, body_mutated = generate_fields(self.request_body, body_selected, should_mutate)
            if not should_mutate:    
                for i in range(10):
                    path_param_values = {k: v for k, v in params.items() if k in path_params}

                    # 1️⃣ blacklist check FIRST
                    if self.context_pool.is_blacklisted(path_param_values):
                        params, params_mutated = generate_fields(self.parameters, params_selected)
                        body, body_mutated = generate_fields(self.request_body, body_selected)
                        continue
                    # 2️⃣ whitelist priority (70%)
                    if random.random() < 0.7:
                        if self.context_pool.in_whitelist(path_param_values):
                            break
                    else:
                        # 3️⃣ exploration 30%
                        break
                    params, params_mutated = generate_fields(self.parameters, params_selected)
                    body, body_mutated = generate_fields(self.request_body, body_selected)
                    # 
            # --- Rebuild body & finalize ---
            data.append(
                {
                    "parameters": remove_nulls(params),
                    "requestBody": remove_nulls(body),
                    "expected_code": "4xx"
                    if (params_mutated or body_mutated)
                    else "2xx",
                }
            )

            self.context_pool.clear_cache()


        self.context_pool.clear_priority_resources()
        test_datas = [
            item
            for item in data
            if (
                item["expected_code"] != "2xx"
                or all(
                    item.get("parameters", {}).get(param) is not None
                    for param in required_params
                )
            )
        ]
        def contains_llm_generator(obj):
            if isinstance(obj, dict):
                return any(contains_llm_generator(v) for v in obj.values())
            if isinstance(obj, list):
                return any(contains_llm_generator(v) for v in obj)
            return obj == "**LLMGenerator**"


        # -----------------------------
        # 1️⃣ Split
        # -----------------------------
        def _need_judge(item):
            return item.get("expected_code") == "2xx" or contains_llm_generator(item)

        judge_datas = [item for item in test_datas if _need_judge(item)]
        normal_datas = [item for item in test_datas if not _need_judge(item)]

        # -----------------------------
        # 2️⃣ Execute judge
        # -----------------------------
        judge_results = []

        if judge_datas:
            params = {
                "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
                "summary": " ".join(filter(None, [self.operation.summary, self.operation.description])),
                "parameters": "\n".join(
                    f"- {k} : {v.to_human_readable()}"
                    for k, v in self.parameters.items()
                ),
                "requestBody": "\n".join(
                    f"- {k} : {v.to_human_readable()}"
                    for k, v in self.request_body.items()
                ),
                "test_datas": json.dumps(judge_datas,separators=(",", ":"), ensure_ascii=False)
            }

            judge_results = self.semantic_oracle_judge.exec(**params)
            judge_results = judge_results.dict().get("datas")
        # -----------------------------
        # 3️⃣ Merge (không cần thứ tự)
        # -----------------------------
        merged_results = normal_datas + judge_results

        return merged_results

        
        # params = {
        #     "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
        #     "summary": ((self.operation.summary or "") + " " + (self.operation.description or "")).strip(),
        #     "parameters": "\n".join([
        #         f"- {k} : {v.to_human_readable()}"   
        #         for k, v in self.parameters.items() 
        #     ]),
        #     "requestBody": "\n".join([
        #         f"- {k} : {v.to_human_readable()}"   
        #         for k, v in self.request_body.items() 
        #     ]),
        #     "test_datas": json.dumps(filtered_data, indent=4)
        # }
        # ## semantic oracle judge
        # results = self.semantic_oracle_judge.exec(**params)
        # results = [ item for item in results.dict().get("datas") if item.get("satisfies", False)]
        # return results
    
    # def exec(self):
    #     # process parameters
    #     cache = self.load_cache()
    #     if self.operation.uuid in cache:
    #         param_combos = cache.get(self.operation.uuid, {}).get("parameters", [])
    #         body_combos = cache.get(self.operation.uuid, {}).get("requestBody", [])
    #     else:
    #         param_combos = self.__get_combination_parameters(self.parameters)
    #         body_combos = self.__get_combination_request_body__(self.request_body)
    #         cache[self.operation.uuid] = {
    #             "parameters": param_combos,
    #             "requestBody": body_combos,
    #         }
    #         # save cache
    #         CACHE_FILE = os.path.join(self.cache_dir, "combination.json")
    #         with open(CACHE_FILE, "w", encoding="utf-8") as f:
    #             json.dump(cache, f, indent=2, ensure_ascii=False)
    #     # if self.operation.uuid == :
    #     #     print(body_combos)  
    #     required_params = [
    #         n for n, p in self.parameters.items() if getattr(p, "required", False)
    #     ]
    #     data = []
    #     self.context_pool.set_current(self.operation.uuid)

    #     def generate_fields(
    #         field_map: Dict[str, Any], selected_fields: List[str]
    #     ) -> Tuple[Dict[str, Any], bool]:
    #         """Generate a dict of values for selected fields. Return (generated_data, is_mutated)."""
    #         generated, mutated = {}, False
    #         for name in selected_fields:
    #             if name is None:
    #                 continue
    #             field = field_map.get(name)
    #             if not field:
    #                 continue
    #             val = None
    #             try:
    #                 val = field.generator.next_value(context_pool=self.context_pool)
    #             except:
    #                 pass        
    #             if random.random() < self.mutation_ratio:
    #                 strategy = random.choice(list(FuzzStrategy)).value
    #                 val = field.generator.next_fuzz_value(
    #                     strategy=strategy, context_pool=self.context_pool
    #                 )
    #                 mutated = True
    #             generated[name] = val

    #         return generated, mutated

    #     for i in range(self.num_test_cases):
        
        
    #         # --- Select parameters ---
    #         params_selected = (
    #             required_params
    #             if (i == 0 and required_params)
    #             else random.choice(param_combos)
    #         )
    #         body_selected = random.choice(body_combos)
            
    #         # --- Generate parameter values ---
    #         params, params_mutated = generate_fields(self.parameters, params_selected)
    #         body, body_mutated = generate_fields(self.request_body, body_selected)

    #         # --- Rebuild body & finalize ---
    #         data.append(
    #             {
    #                 "parameters": remove_nulls(params),
    #                 "requestBody": unflatten_dict(body),
    #                 "expected_code": "4xx"
    #                 if (params_mutated or body_mutated)
    #                 else "2xx",
    #             }
    #         )

    #         self.context_pool.clear_cache()
    #         self.context_pool.clear_current()
    #     filtered_data = [
    #         item
    #         for item in data
    #         if all(
    #             item.get("parameters", {}).get(param) is not None
    #             for param in required_params
    #         )
    #     ]
    #     return filtered_data
