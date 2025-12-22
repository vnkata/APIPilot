"""
Introspection subpackage - OpenAPI spec analysis and querying

This module handles:
- Operation lookup
- Schema extraction
- Path analysis
- Parameter introspection
"""

from common.openapi.introspection.introspector import (
    EndpointInfo,
    SchemaInfo,
    SpecIntrospector,
)

__all__ = ["SpecIntrospector", "EndpointInfo", "SchemaInfo"]
