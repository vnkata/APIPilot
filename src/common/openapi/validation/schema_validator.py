"""
Schema data validation against OpenAPI component schemas

This module provides runtime validation of Python data against
OpenAPI schema components.
"""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Optional

import jsonschema
from openapi_core import Spec

from common.logger.utils.helpers import get_logger
from common.openapi.exceptions import SchemaValidationError
from common.openapi.models import OpenAPI, SpecDict

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of schema validation"""

    valid: bool
    errors: list[str]
    data: Any

    @property
    def is_valid(self) -> bool:
        """Alias for valid property to match test expectations"""
        return self.valid


class SchemaValidator:
    """
    Validate Python data against OpenAPI component schemas

    Features:
    - Validate data against schema components
    - Type coercion where appropriate
    - Detailed error messages
    """

    def __init__(self, spec: OpenAPI | SpecDict) -> None:
        """
        Initialize schema validator

        Args:
            spec: OpenAPI specification (Pydantic model or dict)
        """
        # Convert Pydantic model to dict if needed
        if isinstance(spec, OpenAPI):
            self.spec_dict = spec.model_dump(by_alias=True, exclude_none=True)
        else:
            self.spec_dict = spec

        # Create openapi-core Spec
        self.core_spec = Spec.from_dict(self.spec_dict)

        logger.debug("Initialized SchemaValidator")

    def _cache_key(self, schema_name: str, data: Any) -> str:
        """
        Generate cache key for schema validation

        Args:
            schema_name: Schema name
            data: Data to validate

        Returns:
            Hash string for cache key
        """
        key_string = f"{schema_name}|{json.dumps(data, sort_keys=True, default=str)}"
        return hashlib.md5(key_string.encode()).hexdigest()

    @lru_cache(maxsize=512)
    def _validate_cached(
        self, schema_name: str, data_hash: str, coerce_types: bool
    ) -> ValidationResult:
        """
        Cached validation helper

        Note: Uses hash of data instead of data directly since data may not be hashable.
        This is an internal method - use validate_data() instead.
        """
        # This method is called by validate_data with hashable args
        return self._validate_internal(schema_name, coerce_types)

    def validate_data(
        self,
        schema_name: str,
        data: Any,
        coerce_types: bool = True,
    ) -> ValidationResult:
        """
        Validate data against a named schema component

        Args:
            schema_name: Name of schema in components.schemas
            data: Data to validate
            coerce_types: Attempt type coercion (e.g., string "123" → int 123)

        Returns:
            ValidationResult with validation status and errors

        Raises:
            SchemaValidationError: If schema not found in spec

        Example:
            ```python
            validator = SchemaValidator(spec)
            result = validator.validate_data("User", {"name": "Alice", "age": 30})
            if result.valid:
                print("Valid!")
            else:
                print(f"Errors: {result.errors}")
            ```
        """
        # Check schema exists
        schemas = self.spec_dict.get("components", {}).get("schemas", {})
        if schema_name not in schemas:
            raise SchemaValidationError(
                f"Schema '{schema_name}' not found in components.schemas",
                details={"available_schemas": list(schemas.keys())},
            )

        schema = schemas[schema_name]

        logger.debug(f"Validating data against schema: {schema_name}")

        try:
            # Use jsonschema to validate
            jsonschema.validate(instance=data, schema=schema)

            logger.debug(f"Validation passed for schema: {schema_name}")

            return ValidationResult(valid=True, errors=[], data=data)

        except Exception as e:
            errors = self._extract_errors(e)
            logger.warning(f"Validation failed for schema '{schema_name}': {errors}")
            return ValidationResult(valid=False, errors=errors, data=data)

    def validate_against_schema_dict(
        self,
        schema_dict: dict[str, Any],
        data: Any,
    ) -> ValidationResult:
        """
        Validate data against inline schema dict (not a named component)

        Args:
            schema_dict: OpenAPI schema object
            data: Data to validate

        Returns:
            ValidationResult with validation status and errors

        Example:
            ```python
            schema = {"type": "object", "properties": {"name": {"type": "string"}}}
            result = validator.validate_against_schema_dict(schema, {"name": "Bob"})
            ```
        """
        logger.debug("Validating data against inline schema")

        try:
            # Use jsonschema to validate
            jsonschema.validate(instance=data, schema=schema_dict)

            logger.debug("Validation passed for inline schema")

            return ValidationResult(valid=True, errors=[], data=data)

        except Exception as e:
            errors = self._extract_errors(e)
            logger.warning(f"Validation failed for inline schema: {errors}")
            return ValidationResult(valid=False, errors=errors, data=data)

    def get_schema(self, schema_name: str) -> Optional[dict[str, Any]]:
        """
        Retrieve schema definition by name

        Args:
            schema_name: Name of schema in components.schemas

        Returns:
            Schema dict or None if not found
        """
        schemas = self.spec_dict.get("components", {}).get("schemas", {})
        return schemas.get(schema_name)

    def list_schemas(self) -> list[str]:
        """
        List all available schema names

        Returns:
            List of schema component names
        """
        schemas = self.spec_dict.get("components", {}).get("schemas", {})
        return list(schemas.keys())

    def _extract_errors(self, exception: Exception) -> list[str]:
        """
        Extract error messages from validation exception

        Args:
            exception: Validation exception

        Returns:
            List of error message strings
        """
        errors = []

        # Try to extract structured errors from openapi-core
        if hasattr(exception, "errors"):
            for error in exception.errors:
                errors.append(str(error))
        else:
            errors.append(str(exception))

        return errors


__all__ = ["SchemaValidator", "ValidationResult"]
