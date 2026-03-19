
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

def flatten_item_properties(
    item: 'ItemProperties',
    prefix: str = "",
    include_containers: bool = False
) -> Dict[str, 'ItemProperties']:
    """
    Flatten nested ItemProperties objects into a flat dict with dot-separated keys.

    Args:
        item: The ItemProperties schema to flatten.
        prefix: Internal recursion prefix (path of parent keys).
        include_containers: If True, include container objects (like 'user' or 'user.address')
                            even if they are not leaf fields.

    Returns:
        Dict[str, ItemProperties]: Mapping from full dotted key to the corresponding ItemProperties node.
    """
    if item is None:
        return {}

    flat = {}

    # Nếu đây là object
    if item.properties:
        # Optionally include this container object itself
        if include_containers and prefix:
            flat[prefix] = item
        
        for key, value in item.properties.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if key in item.required:
                value.nullable = False
            flat.update(flatten_item_properties(value, prefix=full_key, include_containers=include_containers))

    # Nếu đây là array
    elif item.items and item.type == "array":
        # Flatten phần tử trong array (ví dụ user[].name → user.name)
        flat.update(flatten_item_properties(item.items, prefix=prefix, include_containers=include_containers))

    # Nếu là leaf node
    else:
        flat[prefix] = item

    return flat

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

# body
def get_required_body_params(operation_body: 'ItemProperties', prefix: str = "") -> Optional[Set[str]]:
    if operation_body is None:
        return None

    required_body = set()

    if operation_body.properties and operation_body.type == "object":
        for key, value in operation_body.properties.items():
            full_key = f"{prefix}.{key}" if prefix else key

            # Nếu field này nằm trong danh sách required
            if operation_body.required and key in operation_body.required:
                # Nếu field required là object → chỉ lấy các child params (bỏ key cha)
                if value.type == "object":
                    required_body |= set(get_body_params(value, prefix=full_key))
                # Nếu là array → lấy required từ items
                elif value.type == "array" and value.items:
                    child_required = get_required_body_params(value.items, prefix=full_key)
                    if child_required:
                        required_body |= child_required
                else:
                    # Field thường (string, number, v.v.) → thêm trực tiếp
                    required_body.add(full_key)

            # Dù required hay không, vẫn đệ quy để đi sâu vào nested object
            if value.type in ("object", "array"):
                child_required = get_required_body_params(value, prefix=full_key)
                if child_required:
                    required_body |= child_required

    elif operation_body.items and operation_body.type == "array":
        child_required = get_required_body_params(operation_body.items, prefix=prefix)
        if child_required:
            required_body |= child_required

    return required_body or set()

def get_body_params(body: 'ItemProperties', prefix: str = "") -> List[str]:
    if body is None:
        return []

    if body.properties or body.type == "object":
        body_params = []
        for key, value in body.properties.items():
            full_key = f"{prefix}.{key}" if prefix else key
            body_params.append(full_key)
            # nếu có nested object → đi sâu
            if value.type in ("object", "array"):
                body_params += get_body_params(value, prefix=full_key)
        return body_params

    elif body.items and body.type == "array":
        return get_body_params(body.items, prefix=prefix)

    return []

def get_request_body_params(
    operation_body: Dict[str, 'ItemProperties'],
) -> Dict[str, List[str]]:
    return (
        {k: get_body_params(v) for k, v in operation_body.items()}
        if operation_body is not None
        else {}
    )

def get_body_combinations(
    operation_body: 'ItemProperties',
) -> Dict[str, List[Tuple[str]]]:
    return get_combinations(get_body_params(operation_body), required=get_required_body_params(operation_body))

# def get_body_combinations(
#     operation_body: Dict[str, 'ItemProperties'],
# ) -> Dict[str, List[Tuple[str]]]:
#     return {
#         k: get_combinations(v, required=get_required_body_params(operation_body.get(k,[])))
#         for k, v in get_request_body_params(operation_body).items()
#     }

def get_body_object_combinations(
    body_schema: 'ItemProperties',
    required_body_params: Optional[Set[str]] = None,
    seed: Optional[str] = None,
) -> List[Tuple[str, ...]]:
    return get_combinations(
        get_body_params(body_schema), required=required_body_params, seed=seed
    )
