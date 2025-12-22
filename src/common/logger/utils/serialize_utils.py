"""
Data Serialization Utilities for Enhanced Logger

Provides smart serialization for complex data types with:
- Hybrid formatting: pretty-print for console, compact for file
- Pydantic model support (v1 & v2)
- Circular reference detection
- Smart truncation with summary hints
- Unicode and bytes handling
"""

import json
from typing import Any, Dict, Optional, Set
from enum import Enum


class SerializationMode(Enum):
    """Serialization output modes"""

    CONSOLE = "console"  # Pretty-print for human readability
    FILE = "file"  # Compact JSON for machine parsing


class DataSerializer:
    """
    Smart data serializer for logging complex Python objects

    Features:
    - Auto-detect and handle dict, list, tuple, Pydantic models
    - Circular reference detection
    - Configurable truncation limits
    - Smart summary hints for large data
    """

    # Truncation limits
    CONSOLE_MAX_CHARS = 10_000  # 10KB for console
    FILE_MAX_CHARS = None  # Unlimited for files
    MAX_DEPTH = 10  # Max nesting depth
    MAX_ITEMS_PREVIEW = 100  # Max items to show before truncating
    MAX_KEYS_PREVIEW = 50  # Max dict keys to show

    @classmethod
    def serialize(
        cls,
        obj: Any,
        mode: SerializationMode = SerializationMode.CONSOLE,
        max_chars: Optional[int] = None,
        _depth: int = 0,
        _seen: Optional[Set[int]] = None,
    ) -> str:
        """
        Serialize an object to string with smart formatting

        Args:
            obj: Object to serialize
            mode: Output mode (CONSOLE or FILE)
            max_chars: Maximum characters (None for unlimited)
            _depth: Current recursion depth (internal)
            _seen: Set of seen object IDs for circular ref detection (internal)

        Returns:
            Serialized string representation
        """
        if _seen is None:
            _seen = set()

        # Set default max_chars based on mode
        if max_chars is None:
            max_chars = (
                cls.CONSOLE_MAX_CHARS
                if mode == SerializationMode.CONSOLE
                else cls.FILE_MAX_CHARS
            )

        # Check depth limit
        if _depth > cls.MAX_DEPTH:
            return "..." if mode == SerializationMode.CONSOLE else '"<max_depth>"'

        # Handle None
        if obj is None:
            return "null" if mode == SerializationMode.FILE else "None"

        # Handle primitives
        if isinstance(obj, (bool, int, float)):
            return json.dumps(obj)

        if isinstance(obj, str):
            return json.dumps(obj) if mode == SerializationMode.FILE else obj

        # Handle bytes
        if isinstance(obj, bytes):
            try:
                decoded = obj.decode("utf-8")
                if len(decoded) > 100:
                    preview = decoded[:100]
                    return f'b"{preview}..." ({len(obj)} bytes)'
                return f'b"{decoded}"'
            except UnicodeDecodeError:
                return f"<bytes: {len(obj)} bytes>"

        # Circular reference detection
        obj_id = id(obj)
        if obj_id in _seen:
            return (
                "<circular_ref>"
                if mode == SerializationMode.CONSOLE
                else '"<circular>"'
            )

        _seen.add(obj_id)

        try:
            # Handle Pydantic models (v1 & v2)
            if cls._is_pydantic_model(obj):
                return cls._serialize_pydantic(obj, mode, max_chars, _depth, _seen)

            # Handle dict
            if isinstance(obj, dict):
                return cls._serialize_dict(obj, mode, max_chars, _depth, _seen)

            # Handle list/tuple
            if isinstance(obj, (list, tuple)):
                return cls._serialize_sequence(obj, mode, max_chars, _depth, _seen)

            # Handle Enum
            if isinstance(obj, Enum):
                return json.dumps(obj.value)

            # Fallback: try json.dumps
            try:
                result = json.dumps(obj, ensure_ascii=False, default=str)
                if max_chars and len(result) > max_chars:
                    return cls._truncate_with_summary(result, max_chars, "object")
                return result
            except (TypeError, ValueError):
                # Last resort: repr()
                result = repr(obj)
                if max_chars and len(result) > max_chars:
                    return cls._truncate_with_summary(result, max_chars, "object")
                return result

        finally:
            _seen.discard(obj_id)

    @staticmethod
    def _is_pydantic_model(obj: Any) -> bool:
        """Check if object is a Pydantic model (v1 or v2)"""
        # Check for Pydantic v2
        if hasattr(obj, "model_dump"):
            return True
        # Check for Pydantic v1
        if hasattr(obj, "dict") and hasattr(obj, "__fields__"):
            return True
        return False

    @classmethod
    def _serialize_pydantic(
        cls,
        obj: Any,
        mode: SerializationMode,
        max_chars: Optional[int],
        depth: int,
        seen: Set[int],
    ) -> str:
        """Serialize Pydantic model (v1 or v2)"""
        try:
            # Try Pydantic v2 first
            if hasattr(obj, "model_dump_json"):
                json_str = obj.model_dump_json(
                    indent=2 if mode == SerializationMode.CONSOLE else None
                )
            elif hasattr(obj, "model_dump"):
                data = obj.model_dump()
                json_str = json.dumps(
                    data,
                    indent=2 if mode == SerializationMode.CONSOLE else None,
                    ensure_ascii=False,
                )
            # Fallback to Pydantic v1
            elif hasattr(obj, "json"):
                json_str = obj.json(
                    indent=2 if mode == SerializationMode.CONSOLE else None
                )
            elif hasattr(obj, "dict"):
                data = obj.dict()
                json_str = json.dumps(
                    data,
                    indent=2 if mode == SerializationMode.CONSOLE else None,
                    ensure_ascii=False,
                )
            else:
                return repr(obj)

            if max_chars and len(json_str) > max_chars:
                return cls._truncate_with_summary(json_str, max_chars, "pydantic_model")
            return json_str

        except Exception as e:
            return f"<pydantic_serialization_error: {e}>"

    @classmethod
    def _serialize_dict(
        cls,
        obj: Dict[str, Any],
        mode: SerializationMode,
        max_chars: Optional[int],
        depth: int,
        seen: Set[int],
    ) -> str:
        """Serialize dictionary with smart truncation"""
        if not obj:
            return "{}"

        total_keys = len(obj)

        # Check if we need to truncate keys
        if total_keys > cls.MAX_KEYS_PREVIEW:
            # Take first N keys
            preview_keys = list(obj.keys())[: cls.MAX_KEYS_PREVIEW]
            preview_dict = {k: obj[k] for k in preview_keys}
            remaining = total_keys - cls.MAX_KEYS_PREVIEW

            # Serialize preview
            serialized_items = []
            for key, value in preview_dict.items():
                key_str = json.dumps(key)
                value_str = cls.serialize(value, mode, None, depth + 1, seen)
                serialized_items.append(f"{key_str}: {value_str}")

            if mode == SerializationMode.CONSOLE:
                items_str = ",\n  ".join(serialized_items)
                result = f"{{\n  {items_str}\n  ... {remaining} more keys\n}}"
            else:
                items_str = ", ".join(serialized_items)
                result = f'{{{items_str}, "...": "{remaining} more keys"}}'

        else:
            # Serialize all items
            serialized_items = []
            for key, value in obj.items():
                key_str = json.dumps(key)
                value_str = cls.serialize(value, mode, None, depth + 1, seen)
                serialized_items.append(f"{key_str}: {value_str}")

            if mode == SerializationMode.CONSOLE:
                items_str = ",\n  ".join(serialized_items)
                result = f"{{\n  {items_str}\n}}"
            else:
                items_str = ", ".join(serialized_items)
                result = f"{{{items_str}}}"

        # Apply max_chars truncation
        if max_chars and len(result) > max_chars:
            return cls._truncate_with_summary(
                result, max_chars, f"dict[{total_keys} keys]"
            )

        return result

    @classmethod
    def _serialize_sequence(
        cls,
        obj: Any,
        mode: SerializationMode,
        max_chars: Optional[int],
        depth: int,
        seen: Set[int],
    ) -> str:
        """Serialize list/tuple with smart truncation"""
        is_tuple = isinstance(obj, tuple)
        if not obj:
            return "()" if is_tuple else "[]"

        total_items = len(obj)

        # Check if we need to truncate items
        if total_items > cls.MAX_ITEMS_PREVIEW:
            preview_items = obj[: cls.MAX_ITEMS_PREVIEW]
            remaining = total_items - cls.MAX_ITEMS_PREVIEW

            # Serialize preview
            serialized_items = [
                cls.serialize(item, mode, None, depth + 1, seen)
                for item in preview_items
            ]

            if mode == SerializationMode.CONSOLE:
                items_str = ",\n  ".join(serialized_items)
                bracket_open = "(" if is_tuple else "["
                bracket_close = ")" if is_tuple else "]"
                result = f"{bracket_open}\n  {items_str}\n  ... {remaining} more items\n{bracket_close}"
            else:
                items_str = ", ".join(serialized_items)
                bracket_open = "(" if is_tuple else "["
                bracket_close = ")" if is_tuple else "]"
                result = f'{bracket_open}{items_str}, "... {remaining} more items"{bracket_close}'

        else:
            # Serialize all items
            serialized_items = [
                cls.serialize(item, mode, None, depth + 1, seen) for item in obj
            ]

            if mode == SerializationMode.CONSOLE:
                items_str = ",\n  ".join(serialized_items)
                bracket_open = "(" if is_tuple else "["
                bracket_close = ")" if is_tuple else "]"
                result = f"{bracket_open}\n  {items_str}\n{bracket_close}"
            else:
                items_str = ", ".join(serialized_items)
                bracket_open = "(" if is_tuple else "["
                bracket_close = ")" if is_tuple else "]"
                result = f"{bracket_open}{items_str}{bracket_close}"

        # Apply max_chars truncation
        if max_chars and len(result) > max_chars:
            type_name = "tuple" if is_tuple else "list"
            return cls._truncate_with_summary(
                result, max_chars, f"{type_name}[{total_items} items]"
            )

        return result

    @staticmethod
    def _truncate_with_summary(text: str, max_chars: int, type_hint: str) -> str:
        """Truncate text with summary hint"""
        if len(text) <= max_chars:
            return text

        # Calculate how much to show
        preview_size = max_chars - 100  # Reserve space for summary
        if preview_size < 100:
            preview_size = 100

        preview = text[:preview_size]
        remaining_chars = len(text) - preview_size

        return f"{preview}... <truncated: {remaining_chars} more chars, {type_hint}>"


def serialize_for_console(obj: Any, max_chars: Optional[int] = None) -> str:
    """
    Serialize object for console output (pretty-print)

    Args:
        obj: Object to serialize
        max_chars: Max characters (default: 10KB)

    Returns:
        Pretty-printed string
    """
    return DataSerializer.serialize(obj, SerializationMode.CONSOLE, max_chars)


def serialize_for_file(obj: Any, max_chars: Optional[int] = None) -> str:
    """
    Serialize object for file output (compact JSON)

    Args:
        obj: Object to serialize
        max_chars: Max characters (default: unlimited)

    Returns:
        Compact JSON string
    """
    return DataSerializer.serialize(obj, SerializationMode.FILE, max_chars)


# Convenience function for kwargs serialization
def serialize_kwargs(
    kwargs: Dict[str, Any],
    mode: SerializationMode = SerializationMode.CONSOLE,
    max_chars: Optional[int] = None,
) -> Dict[str, str]:
    """
    Serialize all values in kwargs dict

    Args:
        kwargs: Dictionary of key-value pairs
        mode: Serialization mode
        max_chars: Max characters per value

    Returns:
        Dictionary with serialized string values
    """
    return {
        key: DataSerializer.serialize(value, mode, max_chars)
        for key, value in kwargs.items()
    }
