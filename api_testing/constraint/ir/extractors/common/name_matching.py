"""
Name matching and normalization utilities for field/parameter matching.

Provides functions to compare field names across different naming conventions
(camelCase, snake_case, PascalCase) and calculate similarity scores.
"""

import re


def normalize_name(name: str) -> str:
    """Normalize a name to lowercase with underscores removed.

    Args:
        name: Name to normalize

    Returns:
        Normalized name
    """
    # Remove underscores and convert to lowercase
    return name.replace("_", "").replace("-", "").lower()


def to_snake_case(name: str) -> str:
    """Convert name to snake_case.

    Args:
        name: Name in any case

    Returns:
        snake_case name
    """
    # Insert underscore before uppercase letters
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(name: str) -> str:
    """Convert name to camelCase.

    Args:
        name: Name in any case (snake_case, kebab-case, etc.)

    Returns:
        camelCase name
    """
    parts = re.split(r"[_\-]", name.lower())
    if not parts:
        return name
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def extract_base_name(name: str) -> str:
    """Extract base name without common suffixes.

    Args:
        name: Field/parameter name

    Returns:
        Base name without Id, Code, etc. suffixes
    """
    name_lower = name.lower()

    # Remove common suffixes
    suffixes = ["id", "_id", "code", "_code", "key", "_key", "name", "_name"]
    for suffix in suffixes:
        if name_lower.endswith(suffix):
            return name[: -len(suffix)]

    return name


def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity score between two names.

    Uses multiple heuristics:
    - Exact match
    - Case-insensitive match
    - Normalized match (ignore case/underscores)
    - Substring match
    - Base name match (without suffixes)
    - Edit distance

    Args:
        name1: First name
        name2: Second name

    Returns:
        Similarity score between 0.0 and 1.0
    """
    # Exact match
    if name1 == name2:
        return 1.0

    # Case-insensitive match
    if name1.lower() == name2.lower():
        return 0.95

    # Normalized match (remove underscores, hyphens, case)
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    if norm1 == norm2:
        return 0.9

    # Convert both to same case and compare
    snake1 = to_snake_case(name1)
    snake2 = to_snake_case(name2)
    if snake1 == snake2:
        return 0.85

    camel1 = to_camel_case(name1)
    camel2 = to_camel_case(name2)
    if camel1 == camel2:
        return 0.85

    # Substring match
    name1_lower = name1.lower()
    name2_lower = name2.lower()
    if name1_lower in name2_lower or name2_lower in name1_lower:
        # Calculate overlap ratio
        overlap = min(len(name1_lower), len(name2_lower))
        total = max(len(name1_lower), len(name2_lower))
        return 0.6 + (0.2 * overlap / total)

    # Base name match (without suffixes like Id, Code)
    base1 = extract_base_name(name1)
    base2 = extract_base_name(name2)
    if base1 and base2 and normalize_name(base1) == normalize_name(base2):
        return 0.75

    # Edit distance (Levenshtein) for close matches
    distance = levenshtein_distance(norm1, norm2)
    max_len = max(len(norm1), len(norm2))
    if max_len > 0:
        similarity = 1.0 - (distance / max_len)
        if similarity > 0.6:  # Only return if reasonably similar
            return similarity * 0.7  # Scale down edit distance matches

    return 0.0


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein edit distance between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        Edit distance
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_best_match(
    target_name: str, candidate_names: list, threshold: float = 0.6
) -> tuple[str, float]:
    """Find the best matching name from a list of candidates.

    Args:
        target_name: Name to match
        candidate_names: List of candidate names
        threshold: Minimum similarity threshold

    Returns:
        Tuple of (best_match_name, similarity_score) or (None, 0.0) if no match above threshold
    """
    best_match = None
    best_score = 0.0

    for candidate in candidate_names:
        score = calculate_similarity(target_name, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    if best_score >= threshold:
        return best_match, best_score

    return None, 0.0


def is_id_field(name: str) -> bool:
    """Check if a name represents an ID field.

    Args:
        name: Field/parameter name

    Returns:
        True if likely an ID field
    """
    name_lower = name.lower()
    return (
        name_lower == "id"
        or name_lower.endswith("id")
        or name_lower.endswith("_id")
        or "identifier" in name_lower
        or name_lower.startswith("id_")
    )


def extract_entity_name(id_field_name: str) -> str:
    """Extract entity name from an ID field name.

    Examples:
        userId -> user
        province_id -> province
        projectId -> project

    Args:
        id_field_name: ID field name

    Returns:
        Entity name
    """
    name_lower = id_field_name.lower()

    # Remove common ID suffixes
    if name_lower.endswith("_id"):
        return id_field_name[:-3]
    elif name_lower.endswith("id") and len(id_field_name) > 2:
        # Check if it's camelCase (userId) or just ends with 'id'
        if id_field_name[-3].islower():
            return id_field_name[:-2]

    return id_field_name


def are_related_by_naming(name1: str, name2: str) -> bool:
    """Check if two names are semantically related by naming patterns.

    Examples of related names:
        - userId and user.id
        - provinceId and province.code
        - startDate and start

    Args:
        name1: First name
        name2: Second name

    Returns:
        True if names are likely related
    """
    # Extract base names
    base1 = extract_base_name(name1)
    base2 = extract_base_name(name2)

    # Check if bases are similar
    if base1 and base2:
        similarity = calculate_similarity(base1, base2)
        if similarity > 0.7:
            return True

    # Check if one is a substring of the other
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    if norm1 in norm2 or norm2 in norm1:
        return True

    # Check for common patterns: startDate/endDate, minValue/maxValue
    paired_patterns = [
        ("start", "end"),
        ("begin", "finish"),
        ("from", "to"),
        ("min", "max"),
        ("lower", "upper"),
        ("first", "last"),
    ]

    for pattern_a, pattern_b in paired_patterns:
        if (pattern_a in norm1 and pattern_b in norm2) or (
            pattern_b in norm1 and pattern_a in norm2
        ):
            return True

    return False


__all__ = [
    "normalize_name",
    "to_snake_case",
    "to_camel_case",
    "extract_base_name",
    "calculate_similarity",
    "levenshtein_distance",
    "find_best_match",
    "is_id_field",
    "extract_entity_name",
    "are_related_by_naming",
]
