"""
Data models for constraint extraction

Defines Pydantic v2 models for representing extracted constraints
from OpenAPI specifications.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class PropertyConstraint:
    """Represents constraints on a single property"""

    spec_name: str
    component_name: str
    property_name: str
    property_path: str  # e.g., "user.profile.email" for nested properties
    type_: str
    format_: Optional[str] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    exclusive_minimum: Optional[float] = None
    exclusive_maximum: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[list[Any]] = None
    description: Optional[str] = None
    is_required: bool = False
    default_value: Optional[Any] = None
    validation_notes: Optional[str] = None

    def to_csv_row(self) -> dict[str, Any]:
        """Convert to CSV row dictionary"""
        return {
            "spec_name": self.spec_name,
            "component_name": self.component_name,
            "property_name": self.property_name,
            "property_path": self.property_path,
            "type": self.type_,
            "format": self.format_ or "",
            "minimum": self.minimum if self.minimum is not None else "",
            "maximum": self.maximum if self.maximum is not None else "",
            "exclusive_minimum": (
                self.exclusive_minimum if self.exclusive_minimum is not None else ""
            ),
            "exclusive_maximum": (
                self.exclusive_maximum if self.exclusive_maximum is not None else ""
            ),
            "min_length": self.min_length if self.min_length is not None else "",
            "max_length": self.max_length if self.max_length is not None else "",
            "pattern": self.pattern or "",
            "enum_values": (
                ",".join(str(v) for v in self.enum_values) if self.enum_values else ""
            ),
            "description": self.description or "",
            "is_required": str(self.is_required),
            "default_value": (
                self.default_value if self.default_value is not None else ""
            ),
            "validation_notes": self.validation_notes or "",
        }


@dataclass
class EndpointConstraint:
    """Represents mapping between request and response components at endpoint level"""

    spec_name: str
    endpoint_path: str
    http_method: str
    request_body_component: Optional[str]
    response_component: Optional[str]
    response_status_code: str
    constraint_notes: Optional[str] = None
    validation_notes: Optional[str] = None

    def to_csv_row(self) -> dict[str, Any]:
        """Convert to CSV row dictionary"""
        return {
            "spec_name": self.spec_name,
            "endpoint_path": self.endpoint_path,
            "http_method": self.http_method,
            "request_body_component": self.request_body_component or "N/A",
            "response_component": self.response_component or "N/A",
            "response_status_code": self.response_status_code,
            "constraint_notes": self.constraint_notes or "",
            "validation_notes": self.validation_notes or "",
        }


__all__ = ["PropertyConstraint", "EndpointConstraint"]
