"""
Path resolution utilities for project directories.

This module provides helpers to resolve paths relative to the project root,
ensuring consistent directory locations regardless of where scripts are executed.
"""

from pathlib import Path
from typing import Union
from common.file.utils import find_project_root


def get_project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path to project root directory
    """
    return find_project_root()


def get_project_log_dir() -> Path:
    """
    Get the project log directory (project_root/logs).

    The directory is created if it doesn't exist.

    Returns:
        Path to logs directory
    """
    log_dir = get_project_root() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_project_cache_dir() -> Path:
    """
    Get the project cache directory (project_root/.cache).

    The directory is created if it doesn't exist.

    Returns:
        Path to .cache directory
    """
    cache_dir = get_project_root() / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def resolve_to_project_root(path: Union[str, Path]) -> Path:
    """
    Resolve a path relative to project root, or return as-is if absolute.

    Args:
        path: Path to resolve (can be relative or absolute)

    Returns:
        Resolved Path object

    Examples:
        >>> resolve_to_project_root(".cache")  # Returns project_root/.cache
        >>> resolve_to_project_root("/absolute/path")  # Returns /absolute/path as-is
        >>> resolve_to_project_root("logs/app.log")  # Returns project_root/logs/app.log
    """
    path_obj = Path(path)

    # If path is absolute, return as-is
    if path_obj.is_absolute():
        return path_obj

    # Otherwise, resolve relative to project root
    return get_project_root() / path_obj


__all__ = [
    "get_project_root",
    "get_project_log_dir",
    "get_project_cache_dir",
    "resolve_to_project_root",
]
