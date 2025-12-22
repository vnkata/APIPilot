from datetime import time
import itertools
import os
import json
from typing import Iterable, Dict, List, Any, Optional, Tuple, Set
import re
import hashlib


#  HTTP Status Code
def flatten_json_schema(schema, parent_key="", sep=".", ref=""):
    flat_schema = {}
    if schema is None:
        return
    newRef = ref
    if "properties" in schema:
        if "xrefs" in schema:
            ref = schema.get("xrefs", "")
        # root
        for key, value in schema["properties"].items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if value is None:
                continue
            if value.get("type") == "object" and "properties" in value:
                # Recursively flatten nested object
                if "xrefs" in value:
                    newRef = value.get("xrefs", "")
                flat_schema.update(
                    flatten_json_schema(value, new_key, sep=sep, ref=newRef)
                )
            elif value.get("type") == "array":
                items = value.get("items", {})
                array_key = f"{new_key}[]"  # Add [] notation for arrays
                # if "xrefs" in value.get("items",[]):
                #     ref = value.get("xrefs")
                if items.get("type") == "object" and "properties" in items:
                    # Flatten object inside array
                    if "xrefs" in value.get("items", {}):
                        newRef = value.get("items", {}).get("xrefs", "")
                    flat_schema.update(
                        flatten_json_schema(items, array_key, sep=sep, ref=newRef)
                    )
                else:
                    if ref != "":
                        items["xrefs"] = ref
                    # Array of primitives
                    flat_schema[array_key] = items
            else:
                # Primitive field
                if ref != "":
                    value["xrefs"] = ref
                flat_schema[new_key] = value
    elif schema.get("type") == "array":
        # nested array - preserve [] notation if parent_key already has it, otherwise add it
        items = schema.get("items", {})
        newRef = ref
        if "xrefs" in items:
            newRef = items.get("xrefs", "")
        # If parent_key doesn't end with [], add it for array notation
        array_parent_key = (
            parent_key if parent_key.endswith("[]") else f"{parent_key}[]"
        )
        flat_schema.update(
            flatten_json_schema(items, array_parent_key, sep=sep, ref=newRef)
        )
    return flat_schema


def get_combinations(arr, requiredArr) -> List[Tuple]:
    combinations = []
    max_size = 10
    # Empirically determined - 16 is max number before size grows too large, 10 is a good balance for ensuring proper storage (> 21k)
    required_set = set(requiredArr)
    n = len(arr)

    def is_valid(combo):
        return required_set.issubset(combo)

    if n >= max_size:
        window_size = max_size
        for i in range(n - window_size):
            subset = arr[i : i + window_size]
            for j in range(1, window_size + 1):
                for combo in itertools.combinations(subset, j):
                    if is_valid(combo):
                        combinations.append(combo)
        for size in range(window_size + 1, n + 1):
            for i in range(n - size + 1):
                subset = arr[i : i + size]
                combo = tuple(subset)
                if is_valid(combo):
                    combinations.append(combo)
    else:
        for i in range(1, n + 1):
            for combo in itertools.combinations(arr, i):
                if is_valid(combo):
                    combinations.append(combo)

    return combinations


def encode_dict_as_key(dictionary: Dict) -> str:
    json_str = json.dumps(dictionary, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


def handle_word_cases(parameter):
    parameter = re.sub(r"[_|-|\.]", " ", parameter)
    parameter = re.sub(r"(?<!^)([A-Z])", r" \1", parameter)
    parameter = re.sub(r"(\[\])", "", parameter)
    return parameter.lower()


def construct_db_dir(base_title: Optional[str] = None):
    db_path = os.path.join(os.getcwd(), ".cache", base_title)
    if not os.path.exists(db_path):
        print(f"Cache dir not found, I'll create dir {db_path}")
        os.makedirs(db_path)
    return db_path


def to_dict_helper(item):
    """
    Helper method for parsing in to a dictionary. Handles the case where the item is a dictionary, list, or object with
    a to_dict method.
    """
    if hasattr(item, "to_dict"):
        return item.to_dict()
    elif isinstance(item, dict):
        return {k: to_dict_helper(v) for k, v in item.items()}
    elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        return [to_dict_helper(i) for i in item]
    else:
        return item


def remove_think_tags(text: str) -> str:
    """<think>...</think>"""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def is_data_modified(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        # Các key trừ 'description'
        keys_a = set(k for k in a if k not in ("check", "reason", "description"))
        keys_b = set(k for k in b if k not in ("check", "reason", "description"))

        # So sánh keys (phát hiện thêm/xóa field)
        if keys_a != keys_b:
            return True

        # So sánh nội dung từng key
        for key in keys_a:
            if is_data_modified(a[key], b[key]):
                return True

        return False

    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return True
        return any(is_data_modified(x, y) for x, y in zip(a, b))

    else:
        # So sánh giá trị primitive
        return a != b


#### MARKDOWN TABLES PROCESSING ####
