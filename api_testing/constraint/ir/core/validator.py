"""
IR schema validation utilities.

Validates Constraint IR documents against the JSON Schema meta-schema.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as SchemaValidationError

from common.logger import get_logger

logger = get_logger(__name__)


class IRSchemaValidator:
    """Validates Constraint IR against JSON Schema."""

    def __init__(self, schema_version: str = "v2"):
        """Initialize validator with specified schema version.

        Args:
            schema_version: IR schema version ('v1' or 'v2')
        """
        self.schema_version = schema_version
        self.schema = self._load_schema(schema_version)
        self.validator = Draft202012Validator(self.schema)

    @staticmethod
    def _load_schema(version: str) -> Dict[str, Any]:
        """Load JSON Schema for specified version.

        Args:
            version: Schema version

        Returns:
            JSON Schema dictionary

        Raises:
            FileNotFoundError: If schema file doesn't exist
        """
        schema_path = Path(__file__).parent / f"constraint_ir_{version}.schema.json"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")

        with open(schema_path, encoding="utf-8") as f:
            return json.load(f)

    def validate(self, ir_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate IR document against schema.

        Args:
            ir_dict: IR document as dictionary

        Returns:
            Tuple of (is_valid, errors)
        """
        errors = []

        try:
            self.validator.validate(ir_dict)
            logger.debug(f"IR validation passed (version={self.schema_version})")
            return (True, [])
        except SchemaValidationError as e:
            error_msg = f"Path {'.'.join(str(p) for p in e.absolute_path)}: {e.message}"
            errors.append(error_msg)
            logger.error(
                "IR validation failed",
                path=list(e.absolute_path),
                message=e.message,
                schema_path=list(e.schema_path),
            )
            return (False, errors)

    def validate_strict(self, ir_dict: Dict[str, Any]) -> None:
        """Validate IR and raise exception if invalid.

        Args:
            ir_dict: IR document as dictionary

        Raises:
            ValueError: If validation fails
        """
        is_valid, errors = self.validate(ir_dict)
        if not is_valid:
            raise ValueError(f"Invalid Constraint IR: {'; '.join(errors)}")


__all__ = ["IRSchemaValidator"]
