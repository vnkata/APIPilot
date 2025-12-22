"""
Parsing subpackage - OpenAPI spec parsing, conversion, and resolution

This module handles:
- Spec parsing (JSON/YAML)
- $ref resolution
- Swagger 2.0 → OpenAPI 3.x conversion
- Caching (file + memory)
"""

from common.openapi.parsing.parser import SpecParser

__all__ = ["SpecParser"]
