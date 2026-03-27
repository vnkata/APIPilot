"""
Generator Models for API Testing

This module defines generator models that combine specification properties
with random value generation strategies for API testing.
"""

from dataclasses import dataclass, fields
from typing import Any, Dict, Optional, Union
from api_testing.inputs import RandomGeneratorFactory
from api_testing.inputs.random_generator import RandomGenerator
from .configuration_model import FieldConfiguration
from .specification_model import ItemProperties, ParameterProperties


@dataclass
class ParameterGenerator(ParameterProperties):
    """
    Generator for API parameter values.

    Combines parameter specification properties with a generation strategy
    to create appropriate random values for API parameters.
    """
    strategy: Optional[FieldConfiguration] = None
    _generator: Optional[RandomGenerator] = None

    @property
    def generator(self) -> Optional[RandomGenerator]:
        """
        Lazy-loaded random generator instance.

        Creates the generator on first access using the configured strategy.

        Returns:
            RandomGenerator instance or None if no strategy is set
        """
        if self._generator is None and self.strategy:
            try:
                self._generator = RandomGeneratorFactory.create(
                    self.strategy.type,
                    **self.strategy.genParameters
                )
            except Exception as e:
                raise ValueError(f"Failed to create generator for parameter '{self.name}': {e}") from e
        return self._generator

    def generate_value(self) -> Any:
        """
        Generate a random value for this parameter.

        Returns:
            Generated value according to the strategy

        Raises:
            ValueError: If no generator is available
        """
        if not self.generator:
            raise ValueError(f"No generator available for parameter '{self.name}'")
        return self.generator.generate()

    def has_generator(self) -> bool:
        """
        Check if a generator is available.

        Returns:
            True if generator can be created, False otherwise
        """
        return self.strategy is not None

    def reset_generator(self) -> None:
        """
        Reset the generator instance.

        This forces recreation of the generator on next access.
        Useful for testing or when strategy parameters change.
        """
        self._generator = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParameterGenerator":
        """
        Create a ParameterGenerator instance from a dictionary.

        Args:
            data: Dictionary containing parameter generator data

        Returns:
            ParameterGenerator instance

        Raises:
            ValueError: If data is invalid or required fields are missing
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        # Get all fields that this class (and its parents) accept
        class_fields = {f.name for f in fields(cls)}

        # Filter data to only include fields that the class accepts
        # Temporarily exclude 'schema' as it needs special handling
        filtered_data = {
            k: v for k, v in data.items()
            if k in class_fields and k not in ('schema', '_generator')
        }

        # Create instance with filtered data
        try:
            instance = cls(**filtered_data)
        except TypeError as e:
            raise ValueError(f"Invalid data for ParameterGenerator: {e}") from e

        # Handle schema conversion separately
        raw_schema = data.get('schema')
        if raw_schema is not None:
            if isinstance(raw_schema, dict):
                instance.schema = ItemProperties.from_dict(raw_schema)
            elif isinstance(raw_schema, ItemProperties):
                instance.schema = raw_schema
            else:
                raise ValueError("Schema must be a dictionary or ItemProperties instance")

        # Handle strategy conversion
        raw_strategy = data.get('strategy')
        if raw_strategy is not None:
            if isinstance(raw_strategy, dict):
                instance.strategy = FieldConfiguration.from_dict(raw_strategy)
            elif isinstance(raw_strategy, FieldConfiguration):
                instance.strategy = raw_strategy
            else:
                raise ValueError("Strategy must be a dictionary or FieldConfiguration instance")

        return instance

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the generator to a dictionary.

        Returns:
            Dictionary representation of the generator
        """
        result = super().to_dict() if hasattr(super(), 'to_dict') else {}
        if self.strategy:
            result['strategy'] = self.strategy.to_dict()
        return result

    def __str__(self) -> str:
        """String representation of the parameter generator."""
        strategy_info = f", strategy={self.strategy.type}" if self.strategy else ""
        return f"ParameterGenerator(name='{self.name}'{strategy_info})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ParameterGenerator(name='{self.name}', required={self.required}, "
                f"strategy={self.strategy.type if self.strategy else None})")


@dataclass
class ItemGenerator(ItemProperties):
    """
    Generator for API request body item values.

    Combines item specification properties with a generation strategy
    to create appropriate random values for request body fields.
    """
    strategy: Optional[FieldConfiguration] = None
    _generator: Optional[RandomGenerator] = None

    @property
    def generator(self) -> Optional[RandomGenerator]:
        """
        Lazy-loaded random generator instance.

        Creates the generator on first access using the configured strategy.

        Returns:
            RandomGenerator instance or None if no strategy is set
        """
        if self._generator is None and self.strategy:
            try:
                self._generator = RandomGeneratorFactory.create(
                    self.strategy.type,
                    **self.strategy.genParameters
                )
            except Exception as e:
                raise ValueError(f"Failed to create generator for item: {e}") from e
        return self._generator

    def generate_value(self) -> Any:
        """
        Generate a random value for this item.

        Returns:
            Generated value according to the strategy

        Raises:
            ValueError: If no generator is available
        """
        if not self.generator:
            raise ValueError("No generator available for item")
        return self.generator.generate()

    def has_generator(self) -> bool:
        """
        Check if a generator is available.

        Returns:
            True if generator can be created, False otherwise
        """
        return self.strategy is not None

    def reset_generator(self) -> None:
        """
        Reset the generator instance.

        This forces recreation of the generator on next access.
        Useful for testing or when strategy parameters change.
        """
        self._generator = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ItemGenerator":
        """
        Create an ItemGenerator instance from a dictionary.

        Args:
            data: Dictionary containing item generator data

        Returns:
            ItemGenerator instance

        Raises:
            ValueError: If data is invalid or required fields are missing
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        # Get all fields that this class (and its parents) accept
        class_fields = {f.name for f in fields(cls)}

        # Filter data to only include fields that the class accepts
        # Temporarily exclude 'strategy' and '_generator' as they need special handling
        filtered_data = {
            k: v for k, v in data.items()
            if k in class_fields and k not in ('strategy', '_generator')
        }

        # Create instance with filtered data
        try:
            instance = cls(**filtered_data)
        except TypeError as e:
            raise ValueError(f"Invalid data for ItemGenerator: {e}") from e

        # Handle strategy conversion
        raw_strategy = data.get('strategy')
        if raw_strategy is not None:
            if isinstance(raw_strategy, dict):
                instance.strategy = FieldConfiguration.from_dict(raw_strategy)
            elif isinstance(raw_strategy, FieldConfiguration):
                instance.strategy = raw_strategy
            else:
                raise ValueError("Strategy must be a dictionary or FieldConfiguration instance")

        return instance

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the generator to a dictionary.

        Returns:
            Dictionary representation of the generator
        """
        result = super().to_dict() if hasattr(super(), 'to_dict') else {}
        if self.strategy:
            result['strategy'] = self.strategy.to_dict()
        return result

    def __str__(self) -> str:
        """String representation of the item generator."""
        strategy_info = f", strategy={self.strategy.type}" if self.strategy else ""
        return f"ItemGenerator(type='{getattr(self, 'type', 'unknown')}'{strategy_info})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"ItemGenerator(type='{getattr(self, 'type', 'unknown')}', "
                f"strategy={self.strategy.type if self.strategy else None})")
    
