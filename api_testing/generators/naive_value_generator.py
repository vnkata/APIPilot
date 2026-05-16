import asyncio
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

def has_file_deep(data):
    if isinstance(data, dict):
        return any(has_file_deep(v) for v in data.values())
    if isinstance(data, list):
        return any(has_file_deep(v) for v in data)
    if isinstance(data, tuple) and len(data) == 3:
        filename, content, content_type = data
        return True
    return isinstance(data, (bytes, bytearray))

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

def to_placeholder(obj):
    if isinstance(obj, tuple) and len(obj) == 3:
        filename, content, content_type = obj
        return {
            "filename": filename,
            "content": "<BINARY>",
            "content_type": content_type
        }
    # bytes
    if isinstance(obj, (bytes, bytearray)):
        return "<BINARY>"

    # custom object (BytesValue)
    if obj.__class__.__name__ == "BytesValue":
        return "<BINARY>"

    # fallback
    return str(obj)

def deduplicate_items(items):
    """
    Deduplicate a list of items (dict) using stable hashing.
    Handles binary data via to_placeholder.
    """
    seen = set()
    result = []

    for item in items:
        try:
            key = json.dumps(
                item,
                sort_keys=True,
                default=to_placeholder,
                separators=(",", ":")
            )
        except Exception:
            key = str(item)

        h = hashlib.md5(key.encode("utf-8")).hexdigest()

        if h not in seen:
            seen.add(h)
            result.append(item)

    return result


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
        if not request_body:
            return [[]]

        # 🔥 NEW STRUCTURE: có __type__
        if isinstance(request_body, dict) and "__type__" in request_body:
            body_type = request_body.get("__type__")

            # -------------------------
            # ARRAY / PRIMITIVE → only 1 way
            # -------------------------
            if body_type in ("array", "primitive"):
                return [["__body__"]]

            # -------------------------
            # OBJECT → combinations of fields
            # -------------------------
            if body_type == "object":
                props = request_body.get("properties", {})
                if not isinstance(props, dict):
                    return [[]]

                request_body_label = list(props.keys())

                # required fields
                request_body_required_label = {
                    k
                    for k, v in props.items()
                    if getattr(v, "nullable", None) is False
                }

                return get_combinations(
                    request_body_label,
                    request_body_required_label
                )

        # -------------------------
        # FALLBACK (old format)
        # -------------------------
        if isinstance(request_body, dict):
            request_body_label = list(request_body.keys())

            request_body_required_label = {
                k
                for k, v in request_body.items()
                if getattr(v, "required", False)
                or (getattr(v, "nullable", None) is False)
            }

            return get_combinations(
                request_body_label,
                request_body_required_label
            )

        return [[]]

    
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
            field_map: Dict[str, Any],
            selected_fields: List[str],
            should_mutate: bool = False
        ) -> Tuple[Dict[str, Any], bool]:
            """Generate values for selected fields. Ensure required fields are never null."""
            
            generated: Dict[str, Any] = {}
            mutated = False

            for name in selected_fields:
                if name is None:
                    continue

                field = field_map.get(name)
                if not field:
                    generated[name] = None
                    continue

                val = None

                try:
                    strategy_type = getattr(getattr(field, "strategy", None), "type", None)

                    # -------------------------
                    # 1️⃣ Generate normal value
                    # -------------------------
                    if not strategy_type or strategy_type == "LLMGenerator":
                        val = "**LLMGenerator**"
                    else:
                        if callable(getattr(field.generator, "next_value_as_string", None)):
                            val = field.generator.next_value_as_string()
                        else:
                            val = field.generator.next_value(context_pool=self.context_pool)

                    # -------------------------
                    # 2️⃣ Mutation
                    # -------------------------
                    if should_mutate and random.random() < 0.5:
                        strategy = random.choice(list(FuzzStrategy)).value

                        if strategy_type == "LLMGenerator":
                            val = "**LLMGenerator**"
                        else:
                            val = field.generator.next_fuzz_value(
                                strategy=strategy,
                                context_pool=self.context_pool
                            )
                        mutated = True

                except Exception:
                    val = None

                # -------------------------
                # 3️⃣ Normalize array
                # -------------------------
                if getattr(field, "type", None) == "array" and val is not None:
                    if not isinstance(val, list):
                        val = [val]

                # -------------------------
                # 4️⃣ Enforce required / non-nullable
                # -------------------------
                is_required = getattr(field, "required", False)
                is_non_nullable = getattr(field, "nullable", None) is False

                if (is_required or is_non_nullable) and val is None:
                    val = "**LLMGenerator**"

                generated[name] = val

            return generated, mutated

        
        is_array_body = (
            isinstance(self.request_body, dict)
            and self.request_body.get("__type__") == "array"
        )

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
            body_mutated = False
            body = []

            if is_array_body:
                # 🔥 ALWAYS use LLM placeholder for array
                items_schema = self.request_body.get("items", {})
                if items_schema.get("__type__") == "object":
                    props = items_schema.get("properties", {})
                    min_items = items_schema.get("minItems", 1)
                    max_items = items_schema.get("maxItems", 5)

                    if should_mutate:
                        num_items = random.choice([
                            0,                # empty array
                            1,
                            random.randint(2, 5),
                            10               # large payload
                        ])
                    else:
                        num_items = random.randint(min_items, max_items)

                    for _ in range(num_items):
                        item, mutated = generate_fields(
                            props,
                            list(props.keys()),
                            should_mutate
                        )
                        body.append(item)
                        body_mutated = body_mutated or mutated
                    body = {
                        "__body__": body
                    }
                else:
                    body = {
                        "__body__": "**LLMGenerator**" # for array with LLM gen
                    }

            else:
                props_mapping = self.request_body.get("properties", {})
                body, body_mutated = generate_fields(
                    props_mapping,
                    body_selected,
                    should_mutate
                )

            if not should_mutate:    
                for _ in range(10):
                    path_param_values = {k: v for k, v in params.items() if k in path_params}

                    # 1️⃣ blacklist check FIRST
                    if self.context_pool.is_blacklisted(path_param_values):
                        params, params_mutated = generate_fields(self.parameters, params_selected)
                        # body, body_mutated = generate_fields(self.request_body, body_selected)
                        continue
                    # 2️⃣ whitelist priority (70%)
                    if random.random() < 0.7:
                        if self.context_pool.in_whitelist(path_param_values):
                            break
                    else:
                        # 3️⃣ exploration 30%
                        break
                    params, params_mutated = generate_fields(self.parameters, params_selected)
                    # body, body_mutated = generate_fields(self.request_body, body_selected)
                    # 
            # --- Rebuild body & finalize ---
            data.append(
                {   
                    "idx": (i+1),
                    "parameters": remove_nulls(params),
                    "requestBody": body,
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
            return (item.get("expected_code") == "2xx" or contains_llm_generator(item)) and  has_file_deep(item.get("requestBody")) == False

        judge_datas = [item for item in test_datas if _need_judge(item)]
        normal_datas = [item for item in test_datas if not _need_judge(item)]
        # -----------------------------
        # 2️⃣ Execute judge
        # -----------------------------
        judge_results = []

        if judge_datas:
            rb_desc = ""

            if isinstance(self.request_body, dict) and "__type__" in self.request_body:
                body_type = self.request_body.get("__type__")

                # 🔥 ARRAY
                if body_type == "array":
                    rb_desc = self.request_body.get("description") or "Array request body"

                # 🔥 OBJECT
                elif body_type == "object":
                    props = self.request_body.get("properties", {})
                    rb_desc = "\n".join(
                        f"- {k} : {v.to_human_readable()}"
                        for k, v in props.items()
                    )

                # 🔥 PRIMITIVE
                elif body_type == "primitive":
                    gen = self.request_body.get("__generator__")
                    rb_desc = gen.to_human_readable() if gen else "Primitive request body"

            else:
                # fallback (old format)
                rb_desc = "\n".join(
                    f"- {k} : {v.to_human_readable()}"
                    for k, v in (self.request_body or {}).items()
                )
            # judge_datas = deduplicate_items(judge_datas)
            base_params = {
                "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
                "summary": " ".join(filter(None, [self.operation.summary, self.operation.description])),
                "parameters": "\n".join(
                    f"- {k} : {v.to_human_readable()}"
                    for k, v in self.parameters.items()
                ),
                "requestBody": rb_desc,
            }

            JUDGE_BATCH_SIZE = 5
            all_judge_results = []
            chunks = [judge_datas[i:i+JUDGE_BATCH_SIZE] for i in range(0, len(judge_datas), JUDGE_BATCH_SIZE)]

            for chunk in chunks:
                params = {**base_params, "test_datas": json.dumps(chunk, separators=(",", ":"), ensure_ascii=False, default=to_placeholder)}
                chunk_results = self.semantic_oracle_judge.exec(**params)
                all_judge_results.extend(chunk_results.dict().get("datas"))
            judge_results = all_judge_results
            original_map = {
                int(item.get("idx")): item
                for item in judge_datas
                if item.get("idx") is not None
            }
            merged_judge_results = []
            for item in judge_results:
                idx = item.get("idx")
                if idx is not None and int(idx) in original_map:
                    original = original_map[int(idx)]

                    merged = {
                        **original,
                        **item,
                        "parameters": {
                            **original.get("parameters", {}),
                            **item.get("parameters", {})
                        },
                        "requestBody": (
                            original.get("requestBody")
                            if has_file_deep(original.get("requestBody"))
                            else item.get("requestBody")
                        )
                    }
                    merged_judge_results.append(merged)
                else:
                    # fallback nếu không có idx
                    merged_judge_results.append(item)

            judge_results = merged_judge_results
        # -----------------------------
        # 3️⃣ Merge (không cần thứ tự)
        # -----------------------------
        merged_results = normal_datas + judge_results
        return merged_results

    async def exec_async(self):
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
            field_map: Dict[str, Any],
            selected_fields: List[str],
            should_mutate: bool = False
        ) -> Tuple[Dict[str, Any], bool]:
            """Generate values for selected fields. Ensure required fields are never null."""

            generated: Dict[str, Any] = {}
            mutated = False

            for name in selected_fields:
                if name is None:
                    continue

                field = field_map.get(name)
                if not field:
                    generated[name] = None
                    continue

                val = None

                try:
                    strategy_type = getattr(getattr(field, "strategy", None), "type", None)

                    if not strategy_type or strategy_type == "LLMGenerator":
                        val = "**LLMGenerator**"
                    else:
                        if callable(getattr(field.generator, "next_value_as_string", None)):
                            val = field.generator.next_value_as_string()
                        else:
                            val = field.generator.next_value(context_pool=self.context_pool)

                    if should_mutate and random.random() < 0.5:
                        strategy = random.choice(list(FuzzStrategy)).value

                        if strategy_type == "LLMGenerator":
                            val = "**LLMGenerator**"
                        else:
                            val = field.generator.next_fuzz_value(
                                strategy=strategy,
                                context_pool=self.context_pool
                            )
                        mutated = True

                except Exception:
                    val = None

                if getattr(field, "type", None) == "array" and val is not None:
                    if not isinstance(val, list):
                        val = [val]

                is_required = getattr(field, "required", False)
                is_non_nullable = getattr(field, "nullable", None) is False

                if (is_required or is_non_nullable) and val is None:
                    val = "**LLMGenerator**"

                generated[name] = val

            return generated, mutated

        is_array_body = (
            isinstance(self.request_body, dict)
            and self.request_body.get("__type__") == "array"
        )

        for i in range(self.num_test_cases):
            params_selected = (
                required_params
                if (i == 0 and required_params)
                else random.choice(param_combos)
            )
            body_selected = random.choice(body_combos)
            should_mutate = random.random() < self.mutation_ratio
            params, params_mutated = generate_fields(self.parameters, params_selected, should_mutate)
            body_mutated = False
            body = []

            if is_array_body:
                items_schema = self.request_body.get("items", {})
                if items_schema.get("__type__") == "object":
                    props = items_schema.get("properties", {})
                    min_items = items_schema.get("minItems", 1)
                    max_items = items_schema.get("maxItems", 5)

                    if should_mutate:
                        num_items = random.choice([
                            0,
                            1,
                            random.randint(2, 5),
                            10
                        ])
                    else:
                        num_items = random.randint(min_items, max_items)

                    for _ in range(num_items):
                        item, mutated = generate_fields(
                            props,
                            list(props.keys()),
                            should_mutate
                        )
                        body.append(item)
                        body_mutated = body_mutated or mutated
                    body = {
                        "__body__": body
                    }
                else:
                    body = {
                        "__body__": "**LLMGenerator**"
                    }

            else:
                props_mapping = self.request_body.get("properties", {})
                body, body_mutated = generate_fields(
                    props_mapping,
                    body_selected,
                    should_mutate
                )

            if not should_mutate:
                for _ in range(10):
                    path_param_values = {k: v for k, v in params.items() if k in path_params}

                    if self.context_pool.is_blacklisted(path_param_values):
                        params, params_mutated = generate_fields(self.parameters, params_selected)
                        continue
                    if random.random() < 0.7:
                        if self.context_pool.in_whitelist(path_param_values):
                            break
                    else:
                        break
                    params, params_mutated = generate_fields(self.parameters, params_selected)

            data.append(
                {
                    "idx": (i+1),
                    "parameters": remove_nulls(params),
                    "requestBody": body,
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

        def _need_judge(item):
            return (item.get("expected_code") == "2xx" or contains_llm_generator(item)) and  has_file_deep(item.get("requestBody")) == False

        judge_datas = [item for item in test_datas if _need_judge(item)]
        normal_datas = [item for item in test_datas if not _need_judge(item)]
        judge_results = []

        if judge_datas:
            rb_desc = ""

            if isinstance(self.request_body, dict) and "__type__" in self.request_body:
                body_type = self.request_body.get("__type__")

                if body_type == "array":
                    rb_desc = self.request_body.get("description") or "Array request body"

                elif body_type == "object":
                    props = self.request_body.get("properties", {})
                    def to_hr(v):
                        return v.to_human_readable() if isinstance(v, ItemProperties) else ItemProperties.from_dict(v).to_human_readable() if isinstance(v, dict) else str(v)
                    rb_desc = "\n".join(
                        f"- {k} : {to_hr(v)}"
                        for k, v in props.items()
                    )

                elif body_type == "primitive":
                    gen = self.request_body.get("__generator__")
                    rb_desc = gen.to_human_readable() if gen else "Primitive request body"

            else:
                def to_hr(v):
                    return v.to_human_readable() if isinstance(v, ItemProperties) else ItemProperties.from_dict(v).to_human_readable() if isinstance(v, dict) else str(v)
                rb_desc = "\n".join(
                    f"- {k} : {to_hr(v)}"
                    for k, v in (self.request_body or {}).items()
                )

            base_params = {
                "endpoint": f"{self.operation.http_method.upper()} {self.operation.endpoint_path}",
                "summary": " ".join(filter(None, [self.operation.summary, self.operation.description])),
                "parameters": "\n".join(
                    f"- {k} : {v.to_human_readable()}"
                    for k, v in self.parameters.items()
                ),
                "requestBody": rb_desc,
            }

            JUDGE_BATCH_SIZE = 5
            chunks = [judge_datas[i:i+JUDGE_BATCH_SIZE] for i in range(0, len(judge_datas), JUDGE_BATCH_SIZE)]

            async def call_judge(chunk):
                params = {**base_params, "test_datas": json.dumps(chunk, separators=(",", ":"), ensure_ascii=False, default=to_placeholder)}
                return await self.semantic_oracle_judge.a_exec(**params)

            tasks = [call_judge(chunk) for chunk in chunks]
            chunk_results_list = await asyncio.gather(*tasks)

            all_judge_results = []
            for chunk_results in chunk_results_list:
                all_judge_results.extend(chunk_results.dict().get("datas"))

            judge_results = all_judge_results
            original_map = {
                int(item.get("idx")): item
                for item in judge_datas
                if item.get("idx") is not None
            }
            merged_judge_results = []
            for item in judge_results:
                idx = item.get("idx")
                if idx is not None and int(idx) in original_map:
                    original = original_map[int(idx)]

                    merged = {
                        **original,
                        **item,
                        "parameters": {
                            **original.get("parameters", {}),
                            **item.get("parameters", {})
                        },
                        "requestBody": (
                            original.get("requestBody")
                            if has_file_deep(original.get("requestBody"))
                            else item.get("requestBody")
                        )
                    }
                    merged_judge_results.append(merged)
                else:
                    merged_judge_results.append(item)

            judge_results = merged_judge_results

        merged_results = normal_datas + judge_results
        return merged_results
