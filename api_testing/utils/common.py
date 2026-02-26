from typing import Iterable, TypeAlias

def isEmpty(value):
    return value == '-' or value is None or value == [] or value == ['-'] or value == ''

def remove_nulls(item):
    if hasattr(item, 'to_dict'):
        return item.to_dict()
    elif isinstance(item, dict):
        return {k: remove_nulls(v) for k, v in item.items() if not isEmpty(v) and remove_nulls(v)}
    elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
        return [remove_nulls(i) for i in item if remove_nulls(i) is not None]
    else:
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