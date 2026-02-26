
from datetime import time
import itertools
import math
import os
import json
import random
from typing import Iterable, Dict, List, Any, Optional, Tuple, Set
import re
import hashlib

#  HTTP Status Code
def flatten_json_schema(schema, parent_key='', sep='.', ref=""):
        flat_schema = {}
        if schema is None:
            return
        newRef = ref
        if 'properties' in schema:
            if "xrefs" in schema:
                ref = schema.get("xrefs", "")    
            # root
            for key, value in schema['properties'].items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                if value is None:
                    continue
                if value.get('type') == 'object' and 'properties' in value:
                    # Recursively flatten nested object
                    if "xrefs" in value:
                        newRef = value.get("xrefs", "")
                    flat_schema.update(
                        flatten_json_schema(value, new_key, sep=sep, ref=newRef))
                elif value.get('type') == 'array':
                    items = value.get('items', {})
                    array_key = f"{new_key}"
                    # if "xrefs" in value.get("items",[]):
                    #     ref = value.get("xrefs")
                    if items.get('type') == 'object' and 'properties' in items:
                        # Flatten object inside array
                        if "xrefs" in value.get("items", {}):
                            newRef = value.get("items", {}).get("xrefs", "")
                        flat_schema.update(flatten_json_schema(
                            items, array_key, sep=sep, ref=newRef))
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
        elif schema.get('type') == 'array':
            # nested
            items = schema.get('items', {})
            newRef = ref
            if "xrefs" in items:
                newRef = items.get("xrefs", "")
            flat_schema.update(
                flatten_json_schema(items, parent_key, sep=sep, ref=newRef))
        return flat_schema


def get_combinations(
    arr: Iterable[Any],
    required: Optional[Set[Any]] = None,
    seed: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    """
    Generate bounded parameter combinations with depth-weighted sampling.

    Uses stratified sampling that prioritizes smaller combinations while ensuring
    required parameters are always included. For large parameter sets, random
    sampling is used with seeded RNG for reproducibility.

    Args:
        arr: All parameters to combine.
        required: Parameters that must appear in every combination.
        seed: Seed string for reproducible randomness (e.g., operation ID).

    Returns:
        List of parameter combination tuples.
    """
    arr = list(arr) if arr is not None else []
    required = required or set()
    optional = [p for p in arr if p not in required]
    required_tuple = tuple(p for p in arr if p in required)  # Preserve order

    max_optional_size = 12
    max_total = 3000
    base_samples = 200
    combination_seed = 42
    # Seeded RNG for reproducibility
    if seed:
        seed_int = int(hashlib.md5(seed.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed_int)
    else:
        rng = random.Random(combination_seed)

    combinations: Set[Tuple[Any, ...]] = set()
    n_optional = len(optional)

    # Always include: required-only and all-params
    combinations.add(required_tuple)
    if optional:
        combinations.add(required_tuple + tuple(optional))

    if n_optional <= max_optional_size:
        # Small enough: exhaustive enumeration of optional params
        for size in range(1, n_optional + 1):
            for combo in itertools.combinations(optional, size):
                combinations.add(required_tuple + combo)
    else:
        # Large: depth-weighted sampling (smaller sizes get more samples)
        for size in range(1, min(max_optional_size, n_optional) + 1):
            # Exponential decay: size=1 gets base_samples, larger sizes get fewer
            samples_for_size = max(10, int(base_samples / (size**0.7)))
            total_possible = math.comb(n_optional, size)

            if total_possible <= samples_for_size:
                # Small enough to enumerate all
                for combo in itertools.combinations(optional, size):
                    combinations.add(required_tuple + combo)
            else:
                # Random sample with seeded RNG
                sampled: Set[Tuple[Any, ...]] = set()
                attempts = 0
                max_attempts = samples_for_size * 20
                while len(sampled) < samples_for_size and attempts < max_attempts:
                    indices = rng.sample(range(n_optional), size)
                    combo = tuple(optional[i] for i in sorted(indices))
                    sampled.add(combo)
                    attempts += 1
                for combo in sampled:
                    combinations.add(required_tuple + combo)

    # Enforce hard cap (deterministic order: sort by size, then content)
    result = sorted(combinations, key=lambda x: (len(x), x))
    if len(result) > max_total:
        # Keep smallest combinations (most valuable for issue isolation)
        result = result[:max_total]

    return result

def get_required_body_params(body: 'ItemProperties', prefix: str = "") -> Optional[set[str]]:
    if not body:
        return None

    req = set()
    if body.type == "object" and body.properties:
        for key, prop in body.properties.items():
            full = f"{prefix}.{key}" if prefix else key
            if key in (body.required or []):
                req.add(full)
            req |= get_required_body_params(prop, full) or set()

    elif body.type == "array" and body.items:
        req |= get_required_body_params(body.items, prefix) or set()

    return req or None


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
