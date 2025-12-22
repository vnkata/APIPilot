from pathlib import Path
from typing import Optional

# Cache project root to avoid repeated directory traversal
_project_root_cache: Optional[Path] = None


def find_project_root(start_path: Optional[Path] = None) -> Path:
    """
    Find the project root directory by looking for 'pyproject.toml', '.git', or 'requirements.txt'.

    Results are cached for performance. The cache is cleared on first call or can be manually
    cleared by setting the cache to None.

    Args:
        start_path: Starting path for search (defaults to this file's parent directory)

    Returns:
        Path to project root directory
    """
    global _project_root_cache

    # Return cached value if available
    if _project_root_cache is not None:
        return _project_root_cache

    if start_path is None:
        # Start from this file's directory and walk up to find project root
        start_path = Path(__file__).parent

    current = Path(start_path).resolve()

    # Traverse up the directory tree
    while current != current.parent:  # Stop at filesystem root
        if (
            (current / "pyproject.toml").exists()
            or (current / ".git").exists()
            or (current / "requirements.txt").exists()
        ):
            _project_root_cache = current
            return current
        current = current.parent

    # Fallback: if no markers found, use start_path
    result = Path(start_path).resolve()
    _project_root_cache = result
    return result
