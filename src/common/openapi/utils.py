"""
Utility functions for OpenAPI operations
"""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from common.openapi.exceptions import SpecLoadError


def is_url(source: str) -> bool:
    """
    Check if source string is a URL

    Args:
        source: Source string to check

    Returns:
        True if source is a valid HTTP/HTTPS URL
    """
    try:
        result = urlparse(source)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except Exception:
        return False


def detect_format(file_path: Path) -> str:
    """
    Detect OpenAPI format (JSON or YAML) from file extension

    Args:
        file_path: Path to OpenAPI file

    Returns:
        'json' or 'yaml'

    Raises:
        SpecLoadError: If format cannot be determined
    """
    suffix = file_path.suffix.lower()
    if suffix in (".json",):
        return "json"
    elif suffix in (".yaml", ".yml"):
        return "yaml"
    else:
        raise SpecLoadError(
            f"Cannot determine format from file extension: {suffix}",
            details={"file_path": str(file_path), "suffix": suffix},
        )


def load_spec_from_file(file_path: str | Path) -> dict[str, Any]:
    """
    Load OpenAPI specification from local file (JSON or YAML)

    Args:
        file_path: Path to OpenAPI specification file

    Returns:
        Parsed specification as dict

    Raises:
        SpecLoadError: If file cannot be loaded or parsed
    """
    path = Path(file_path)

    if not path.exists():
        raise SpecLoadError(
            f"Specification file not found: {path}",
            details={"file_path": str(path)},
        )

    try:
        fmt = detect_format(path)
        content = path.read_text(encoding="utf-8")

        if fmt == "json":
            return json.loads(content)
        else:  # yaml
            return yaml.safe_load(content)

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise SpecLoadError(
            f"Failed to parse specification file: {e}",
            details={"file_path": str(path), "error": str(e)},
        ) from e
    except Exception as e:
        raise SpecLoadError(
            f"Failed to load specification: {e}",
            details={"file_path": str(path), "error": str(e)},
        ) from e


def normalize_path(path: str) -> str:
    """
    Normalize OpenAPI path (ensure leading slash, remove trailing slash)

    Args:
        path: OpenAPI path string

    Returns:
        Normalized path

    Example:
        >>> normalize_path("api/users/")
        "/api/users"
        >>> normalize_path("/api/users")
        "/api/users"
    """
    path = path.strip()
    if not path.startswith("/"):
        path = "/" + path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return path


def normalize_method(method: str) -> str:
    """
    Normalize HTTP method (lowercase)

    Args:
        method: HTTP method string

    Returns:
        Lowercase method name

    Example:
        >>> normalize_method("GET")
        "get"
    """
    return method.lower().strip()


def get_operation_id(path: str, method: str) -> str:
    """
    Generate operation ID from path and method

    Args:
        path: OpenAPI path
        method: HTTP method

    Returns:
        Generated operation ID

    Example:
        >>> get_operation_id("/api/users/{id}", "get")
        "get_api_users_id"
    """
    # Remove leading slash and replace special chars
    normalized = path.lstrip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f"{normalize_method(method)}_{normalized}"


def safe_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dict value with default fallback

    Args:
        data: Dict to query
        *keys: Nested keys to traverse
        default: Default value if key not found

    Returns:
        Value at nested key or default

    Example:
        >>> safe_get({"a": {"b": {"c": 123}}}, "a", "b", "c")
        123
        >>> safe_get({"a": {}}, "a", "b", "c", default=0)
        0
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


__all__ = [
    "is_url",
    "detect_format",
    "load_spec_from_file",
    "normalize_path",
    "normalize_method",
    "get_operation_id",
    "safe_get",
]
