"""
Type definitions and re-exports from openapi-pydantic

This module provides typed access to OpenAPI specification models
using Pydantic v2 from the openapi-pydantic library.
"""

from typing import Any, Union

# Core OpenAPI models from openapi-pydantic
from openapi_pydantic import (
    Components,
    Contact,
    Discriminator,
    Encoding,
    Example,
    ExternalDocumentation,
    Header,
    Info,
    License,
    Link,
    MediaType,
    OAuthFlow,
    OAuthFlows,
    OpenAPI,
    Operation,
    Parameter,
    PathItem,
    Paths,
    Reference,
    RequestBody,
    Response,
    Responses,
    Schema,
    SecurityRequirement,
    SecurityScheme,
    Server,
    ServerVariable,
    Tag,
    XML,
)

# Type aliases for common use cases
SpecDict = dict[str, Any]
PathsDict = dict[str, PathItem]
SchemasDict = dict[str, Union[Schema, Reference]]
ParametersDict = dict[str, Union[Parameter, Reference]]
ResponsesDict = dict[str, Union[Response, Reference]]
RequestBodiesDict = dict[str, Union[RequestBody, Reference]]
HeadersDict = dict[str, Union[Header, Reference]]
SecuritySchemesDict = dict[str, Union[SecurityScheme, Reference]]
LinksDict = dict[str, Union[Link, Reference]]
CallbacksDict = dict[str, Union[PathItem, Reference]]

# HTTP Methods supported in OpenAPI
HTTPMethod = str  # get, post, put, delete, patch, options, head, trace


# Helper type guards
def is_reference(obj: Any) -> bool:
    """Check if object is a Reference (has $ref)"""
    return isinstance(obj, Reference) or (isinstance(obj, dict) and "$ref" in obj)


def get_ref_name(ref: Union[Reference, str]) -> str:
    """
    Extract component name from $ref

    Args:
        ref: Reference object or $ref string

    Returns:
        Component name

    Example:
        >>> get_ref_name("#/components/schemas/User")
        "User"
    """
    ref_str = ref.ref if isinstance(ref, Reference) else ref
    return ref_str.split("/")[-1]


__all__ = [
    # Core models
    "OpenAPI",
    "Info",
    "Contact",
    "License",
    "Server",
    "ServerVariable",
    "Components",
    "Paths",
    "PathItem",
    "Operation",
    "ExternalDocumentation",
    "Parameter",
    "RequestBody",
    "MediaType",
    "Encoding",
    "Responses",
    "Response",
    "Link",
    "Header",
    "Tag",
    "Reference",
    "Schema",
    "Discriminator",
    "XML",
    "SecurityScheme",
    "OAuthFlows",
    "OAuthFlow",
    "SecurityRequirement",
    "Example",
    # Type aliases
    "SpecDict",
    "PathsDict",
    "SchemasDict",
    "ParametersDict",
    "ResponsesDict",
    "RequestBodiesDict",
    "HeadersDict",
    "SecuritySchemesDict",
    "LinksDict",
    "CallbacksDict",
    "HTTPMethod",
    # Helpers
    "is_reference",
    "get_ref_name",
]
