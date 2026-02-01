"""
Registry loader that merges predicates from multiple JSON files.

Provides a unified registry by loading and merging predicate definitions
from category-specific JSON files organized in primitives/ and relations/ subdirectories.
"""

import json
from pathlib import Path
from typing import Dict, List

from common.logger import get_logger

logger = get_logger(__name__)


def load_merged_registry() -> dict:
    """Load and merge all predicate registries from JSON files.

    Returns:
        Dictionary with 'version' and 'predicates' keys containing merged registry data

    Raises:
        FileNotFoundError: If registry directory structure is missing
        json.JSONDecodeError: If any JSON file is malformed
    """
    base_dir = Path(__file__).parent

    # Load primitive types
    primitives_dir = base_dir / "primitives"
    relations_dir = base_dir / "relations"

    if not primitives_dir.exists():
        raise FileNotFoundError(f"Primitives directory not found: {primitives_dir}")
    if not relations_dir.exists():
        raise FileNotFoundError(f"Relations directory not found: {relations_dir}")

    all_predicates: list[dict] = []
    loaded_files = []

    # Load all JSON files from both directories
    for json_file in sorted(
        list(primitives_dir.glob("*.json")) + list(relations_dir.glob("*.json"))
    ):
        try:
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                predicates = data.get("predicates", [])
                all_predicates.extend(predicates)
                loaded_files.append(json_file.name)
                logger.debug(
                    f"Loaded {len(predicates)} predicates from {json_file.name}",
                    file=str(json_file),
                )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file: {json_file}", error=str(e))
            raise
        except Exception as e:
            logger.error(f"Failed to load registry file: {json_file}", error=str(e))
            raise

    logger.info(
        f"Loaded registry with {len(all_predicates)} predicates from {len(loaded_files)} files",
        files=loaded_files,
    )

    return {"version": "1.0", "predicates": all_predicates}


__all__ = ["load_merged_registry"]
