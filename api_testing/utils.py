from datetime import time
import itertools
import os
import json
from typing import Iterable, Dict, List, Any, Optional, Tuple, Set
import re
import hashlib


def remove_nulls(item):
    if hasattr(item, 'to_dict'):
        return item.to_dict()
    elif isinstance(item, dict):
        return {k: remove_nulls(v) for k, v in item.items() if not isEmpty(v) and remove_nulls(v)}
    elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        return [remove_nulls(i) for i in item if remove_nulls(i) is not None]
    else:
        return item


def isEmpty(value):
    return value == '-' or value is None or value == [] or value == ['-'] or value == ''

#  HTTP Status Code

def isSuccessful(code) -> bool:
    if isinstance(code, str):
        return code[0] == '2'
    return code >= 200 and code < 300


def isInformational(code: int):
    return code >= 100 and code < 200


def isRedirection(code: int):
    return code >= 300 and code < 400


def isClientError(code: int):
    return code >= 400 and code < 500


def isServerError(code: int):
    return code >= 500 and code < 600


def flatten_json_schema(schema, parent_key='', sep='.'):
    flat_schema = {}
    if 'properties' in schema:
        for key, value in schema['properties'].items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if not value:
                continue
            if value.get('type') == 'object' and 'properties' in value:
                # Recursively flatten nested object
                flat_schema.update(
                    flatten_json_schema(value, new_key, sep=sep))

            elif value.get('type') == 'array':
                items = value.get('items', {})
                array_key = f"{new_key}[]"

                if items.get('type') == 'object' and 'properties' in items:
                    # Flatten object inside array
                    flat_schema.update(flatten_json_schema(
                        items, array_key, sep=sep))
                else:
                    # Array of primitives
                    flat_schema[array_key] = items
            else:
                # Primitive field
                flat_schema[new_key] = value

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


def trim_and_load_json(
    input_string: str,
) -> Dict:

    start = input_string.find("{")
    end = input_string.rfind("}") + 1
    if end == 0 and start != -1:
        input_string = input_string + "}"
        end = len(input_string)
    jsonStr = input_string[start:end] if start != -1 and end != 0 else ""
    jsonStr = re.sub(r",\s*([\]}])", r"\1", jsonStr)
    try:
        return json.loads(jsonStr)
    except json.JSONDecodeError:
        error_str = "Evaluation LLM outputted an invalid JSON. Please use a better evaluation model."
        print(input_string)
        raise ValueError(error_str)
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")


def call_with_retry(func, max_retries=3, sleep_time=10, fallback_return=None, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            return func(**kwargs)
        except Exception as e:
            print(e)
            if attempt < max_retries:
                time.sleep(sleep_time)
            else:
                print(
                    "Max retries reached, returning fallback_return.")
                return fallback_return

#### MARKDOWN TABLES PROCESSING ####
