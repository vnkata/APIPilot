from typing import Iterable, TypeAlias

def isEmpty(value):
    return value == '-' or value is None or value == [] or value == ['-'] or value == ''

from collections.abc import Iterable

def remove_nulls(item):
    # object có to_dict
    if hasattr(item, "to_dict"):
        return remove_nulls(item.to_dict())

    # dict
    if isinstance(item, dict):
        result = {}
        for k, v in item.items():
            cleaned = remove_nulls(v)
            if not isEmpty(cleaned):
                result[k] = cleaned
        return result

    # tuple → giữ nguyên tuple
    if isinstance(item, tuple):
        cleaned_items = []
        for i in item:
            cleaned = remove_nulls(i)
            if not isEmpty(cleaned):
                cleaned_items.append(cleaned)
        return tuple(cleaned_items)

    # list / iterable (trừ str, bytes)
    if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        result = []
        for i in item:
            cleaned = remove_nulls(i)
            if not isEmpty(cleaned):
                result.append(cleaned)
        return result

    # giữ nguyên primitive (including bytes)
    return item
    
ParameterKey: TypeAlias = tuple[str, str | None]


def make_param_key(name: str | None, in_value: str | None) -> ParameterKey:
    """
    Build a canonical parameter key from name and in_value.
    """
    return (name or "", in_value or None)

def param_key_to_label(key: ParameterKey) -> str:
    """
    Create a stable string label for a parameter key (for JSON/LLM prompts).
    """
    name, in_value = key
    loc = in_value if in_value is not None else "unspecified"
    return f"{name}::{loc}"


def label_to_param_key(label: str) -> ParameterKey:
    """
    Convert a parameter label back into a key tuple.
    """
    if "::" in label:
        name, loc = label.split("::", 1)
        loc = None if loc == "unspecified" else loc
    else:
        name, loc = label, None
    return make_param_key(name, loc)