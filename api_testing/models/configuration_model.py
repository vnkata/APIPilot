"""
Configuration Models for API Testing

This module defines data models for API operation configurations and field generators.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Union
from copy import deepcopy


@dataclass
class FieldConfiguration:
    """
    Configuration for a single API field generator.

    Represents the configuration needed to generate values for a specific
    API parameter or request body field using various generator types.
    """
    name: str = ""
    type: str = ""  # Name of the Generator class (e.g., "RandomTextGenerator")
    genParameters: Dict[str, Any] = field(default_factory=dict)  # Parameters for the generator

    def __post_init__(self):
        """Validate the configuration after initialization."""
        if not isinstance(self.name, str):
            raise ValueError("Field name must be a string")
        if not isinstance(self.type, str):
            raise ValueError("Field type must be a string")
        if not isinstance(self.genParameters, dict):
            raise ValueError("Generator parameters must be a dictionary")

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["FieldConfiguration"]:
        """
        Create a FieldConfiguration instance from a dictionary.

        Args:
            data: Dictionary containing field configuration data

        Returns:
            FieldConfiguration instance or None if data is None

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if data is None:
            return None

        try:
            # Extract and validate required fields
            name = data.get("name", "")
            field_type = data.get("type", "")
            gen_params = data.get("genParameters", {})

            # Ensure genParameters is a dict
            if not isinstance(gen_params, dict):
                gen_params = {}

            return cls(
                name=name,
                type=field_type,
                genParameters=gen_params
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid field configuration data: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        return asdict(self)

    def copy(self) -> "FieldConfiguration":
        """
        Create a deep copy of the configuration.

        Returns:
            New FieldConfiguration instance with copied data
        """
        return FieldConfiguration(
            name=self.name,
            type=self.type,
            genParameters=deepcopy(self.genParameters)
        )

    def update_parameters(self, **kwargs: Any) -> None:
        """
        Update generator parameters.

        Args:
            **kwargs: Parameters to update
        """
        self.genParameters.update(kwargs)

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """
        Get a generator parameter value.

        Args:
            key: Parameter name
            default: Default value if parameter not found

        Returns:
            Parameter value or default
        """
        return self.genParameters.get(key, default)

    def __str__(self) -> str:
        """String representation of the field configuration."""
        return f"FieldConfiguration(name='{self.name}', type='{self.type}')"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"FieldConfiguration(name='{self.name}', type='{self.type}', "
                f"genParameters={self.genParameters})")


@dataclass
class OperationConfiguration:
    """
    Configuration for a complete API operation.

    Contains the HTTP method, endpoint, and configurations for all parameters
    and request body fields that need value generation.
    """
    method: str
    endpoint: str
    params: Dict[str, FieldConfiguration] = field(default_factory=dict)
    request_body: Dict[str, FieldConfiguration] = field(default_factory=dict)

    def __post_init__(self):
        """Validate the configuration after initialization."""
        if not isinstance(self.method, str) or not self.method:
            raise ValueError("HTTP method must be a non-empty string")
        if not isinstance(self.endpoint, str) or not self.endpoint:
            raise ValueError("Endpoint must be a non-empty string")
        if not isinstance(self.params, dict):
            raise ValueError("Params must be a dictionary")
        if not isinstance(self.request_body, dict):
            raise ValueError("Request body must be a dictionary")

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> Optional["OperationConfiguration"]:
        """
        Create an OperationConfiguration instance from a dictionary.

        Args:
            data: Dictionary containing operation configuration data

        Returns:
            OperationConfiguration instance or None if data is None

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if data is None:
            return None

        try:
            # Extract required fields
            method = data.get("method", "")
            endpoint = data.get("endpoint", "")

            # Create instance with basic fields
            config = cls(method=method, endpoint=endpoint)

            # Process params
            params_data = data.get("params", {})
            if isinstance(params_data, dict):
                config.params = {}
                for key, value in params_data.items():
                    field_config = FieldConfiguration.from_dict(value)
                    if field_config:
                        config.params[key] = field_config

            # Process request_body
            body_data = data.get("request_body", {})
            if isinstance(body_data, dict):
                config.request_body = {}
                for key, value in body_data.items():
                    field_config = FieldConfiguration.from_dict(value)
                    if field_config:
                        config.request_body[key] = field_config

            return config

        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid operation configuration data: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        result = asdict(self)
        # Convert FieldConfiguration objects to dicts
        result["params"] = {k: v.to_dict() for k, v in self.params.items()}
        result["request_body"] = {k: v.to_dict() for k, v in self.request_body.items()}
        return result

    def copy(self) -> "OperationConfiguration":
        """
        Create a deep copy of the configuration.

        Returns:
            New OperationConfiguration instance with copied data
        """
        return OperationConfiguration(
            method=self.method,
            endpoint=self.endpoint,
            params={k: v.copy() for k, v in self.params.items()},
            request_body={k: v.copy() for k, v in self.request_body.items()}
        )

    def get_field_config(self, field_name: str, location: str = "params") -> Optional[FieldConfiguration]:
        """
        Get field configuration by name and location.

        Args:
            field_name: Name of the field
            location: Location of the field ("params" or "request_body")

        Returns:
            FieldConfiguration if found, None otherwise
        """
        if location == "params":
            return self.params.get(field_name)
        elif location == "request_body":
            return self.request_body.get(field_name)
        else:
            raise ValueError(f"Invalid location: {location}. Must be 'params' or 'request_body'")

    def set_field_config(self, field_name: str, config: FieldConfiguration, location: str = "params") -> None:
        """
        Set field configuration.

        Args:
            field_name: Name of the field
            config: FieldConfiguration to set
            location: Location of the field ("params" or "request_body")

        Raises:
            ValueError: If location is invalid
        """
        if location == "params":
            self.params[field_name] = config
        elif location == "request_body":
            self.request_body[field_name] = config
        else:
            raise ValueError(f"Invalid location: {location}. Must be 'params' or 'request_body'")

    def remove_field_config(self, field_name: str, location: str = "params") -> bool:
        """
        Remove field configuration.

        Args:
            field_name: Name of the field to remove
            location: Location of the field ("params" or "request_body")

        Returns:
            True if field was removed, False if not found

        Raises:
            ValueError: If location is invalid
        """
        if location == "params":
            return self.params.pop(field_name, None) is not None
        elif location == "request_body":
            return self.request_body.pop(field_name, None) is not None
        else:
            raise ValueError(f"Invalid location: {location}. Must be 'params' or 'request_body'")

    def get_all_field_configs(self) -> Dict[str, FieldConfiguration]:
        """
        Get all field configurations from both params and request_body.

        Returns:
            Dictionary mapping field names to configurations
        """
        all_configs = {}
        all_configs.update(self.params)
        all_configs.update(self.request_body)
        return all_configs

    def has_field(self, field_name: str) -> bool:
        """
        Check if a field exists in either params or request_body.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field exists, False otherwise
        """
        return field_name in self.params or field_name in self.request_body

    def get_operation_key(self) -> str:
        """
        Get a unique key for this operation.

        Returns:
            String in format "METHOD-endpoint"
        """
        return f"{self.method.upper()}-{self.endpoint}"

    def __str__(self) -> str:
        """String representation of the operation configuration."""
        return f"OperationConfiguration(method='{self.method}', endpoint='{self.endpoint}')"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"OperationConfiguration(method='{self.method}', endpoint='{self.endpoint}', "
                f"params_count={len(self.params)}, body_count={len(self.request_body)})")