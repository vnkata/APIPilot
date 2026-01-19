
from datetime import time
import itertools
import os
import json
from typing import Iterable, Dict, List, Any, Optional, Tuple, Set
import re
import hashlib

#  HTTP Status Code
def flatten_json_schema(schema, parent_key='', sep='.', ref=""):
    """
    Recursively flattens a JSON schema.
    Preserves array-level metadata (description and type) for arrays of primitives
    to ensure the downstream parser can correctly identify list-based fields.
    """
    flat_schema = {}
    if schema is None:
        return flat_schema

    # Inherit or update the external reference (xrefs)
    current_ref = schema.get("xrefs", ref)

    # 1. Process objects with defined properties
    if 'properties' in schema:
        for key, value in schema['properties'].items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if value is None:
                continue

            p_type = value.get('type')

            if p_type == 'object' and 'properties' in value:
                # Recursively flatten nested objects
                flat_schema.update(flatten_json_schema(value, new_key, sep=sep, ref=current_ref))

            elif p_type == 'array':
                items = value.get('items', {})
                # Only recurse if the array contains an object with its own properties
                if items.get('type') == 'object' and 'properties' in items:
                    flat_schema.update(flatten_json_schema(items, new_key, sep=sep, ref=current_ref))
                else:
                    # Array of primitives (e.g., transcriptIds): 
                    # Store the array definition itself to preserve 'description' and 'type: array'
                    flat_copy = value.copy()
                    if current_ref:
                        flat_copy["xrefs"] = current_ref
                    flat_schema[new_key] = flat_copy

            else:
                # Standard primitive field (string, integer, etc.)
                flat_copy = value.copy()
                if current_ref:
                    flat_copy["xrefs"] = current_ref
                flat_schema[new_key] = flat_copy

    # 2. Handle cases where the top-level schema is an array definition
    elif schema.get('type') == 'array':
        items = schema.get('items', {})
        if items.get('type') == 'object' and 'properties' in items:
            return flatten_json_schema(items, parent_key, sep=sep, ref=current_ref)
        else:
            # Preserve metadata for root or nested level primitive arrays
            flat_copy = schema.copy()
            if current_ref:
                flat_copy["xrefs"] = current_ref
            flat_schema[parent_key] = flat_copy

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
            subset = arr[i:i + window_size]
            for j in range(1, window_size + 1):
                for combo in itertools.combinations(subset, j):
                    if is_valid(combo):
                        combinations.append(combo)
        for size in range(window_size + 1, n + 1):
            for i in range(n - size + 1):
                subset = arr[i:i + size]
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
    parameter = re.sub(r'[_|-|\.]', ' ', parameter)
    parameter = re.sub(r'(?<!^)([A-Z])', r' \1', parameter)
    parameter = re.sub(r'(\[\])', '', parameter)
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
    if hasattr(item, 'to_dict'):
        return item.to_dict()
    elif isinstance(item, dict):
        return {k: to_dict_helper(v) for k, v in item.items()}
    elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        return [to_dict_helper(i) for i in item]
    else:
        return item


def remove_think_tags(text: str) -> str:
    """ <think>...</think>"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


def is_data_modified(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        # Các key trừ 'description'
        keys_a = set(k for k in a if k not in (
            "check", "reason", "description"))
        keys_b = set(k for k in b if k not in (
            "check", "reason", "description"))

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
