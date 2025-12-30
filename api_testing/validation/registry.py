"""
Validator registry with auto-discovery.

Automatically discovers and registers validator primitives from the primitives package.
Validators are registered by their kind@version (e.g., 'int.range@v1').
"""

from typing import Callable, Dict, List, Any
import importlib
import pkgutil
from api_testing.validation import primitives
from api_testing.validation.models import Violation, ValidationContext
from common.logger import get_logger

logger = get_logger(__name__)

# Type alias for validator function signature
ValidatorFn = Callable[[Any, Dict[str, Any], ValidationContext], List[Violation]]


class ValidatorRegistry:
    """Auto-discovering registry for validator primitives.

    Automatically discovers validators from the primitives package by:
    1. Iterating through all modules in api_testing.validation.primitives
    2. Finding functions matching pattern: {kind}_{version} (e.g., int_range_v1)
    3. Registering them as {kind}@{version} (e.g., int.range@v1)

    Example:
        >>> registry = ValidatorRegistry()
        >>> validator_fn = registry.get("int.range", "v1")
        >>> violations = validator_fn(value=5, args={"min": 1, "max": 10}, ctx=ctx)
    """

    def __init__(self):
        """Initialize registry and auto-discover built-in validators."""
        self._validators: Dict[str, ValidatorFn] = {}
        self._discover_builtin_validators()

    def _discover_builtin_validators(self):
        """Auto-discover validators from primitives package.

        Scans all modules in api_testing.validation.primitives and registers
        functions matching the pattern {kind}_{version}.
        """
        discovered_count = 0

        try:
            # Iterate through all modules in primitives package
            for _, module_name, _ in pkgutil.iter_modules(primitives.__path__):
                try:
                    module = importlib.import_module(
                        f"api_testing.validation.primitives.{module_name}"
                    )

                    # Find functions matching pattern: {kind}_{version}
                    for attr_name in dir(module):
                        # Check if it's a versioned function (ends with _v{N})
                        if "_v" in attr_name and not attr_name.startswith("_"):
                            func = getattr(module, attr_name)

                            # Ensure it's callable
                            if not callable(func):
                                continue

                            # Extract version from function name
                            if not any(
                                attr_name.endswith(f"_v{i}") for i in range(1, 10)
                            ):
                                continue

                            try:
                                # Convert function name to kind@version
                                # e.g., int_range_v1 → int.range@v1
                                # e.g., date_iso_date_v1 → date.iso_date@v1
                                parts = attr_name.rsplit("_v", 1)
                                kind = parts[0].replace("_", ".")
                                version = "v" + parts[1]
                                key = f"{kind}@{version}"

                                self.register(key, func)
                                discovered_count += 1

                            except (IndexError, ValueError) as e:
                                logger.warning(
                                    f"Failed to parse validator name: {attr_name}",
                                    error=str(e),
                                )

                except Exception as e:
                    logger.warning(
                        f"Failed to load primitives module: {module_name}",
                        error=str(e),
                        error_type=type(e).__name__,
                    )

            logger.info(
                f"Validator registry initialized",
                validators_discovered=discovered_count,
            )

        except Exception as e:
            logger.error(
                "Failed to discover builtin validators",
                error=str(e),
                error_type=type(e).__name__,
            )

    def register(self, kind_version: str, fn: ValidatorFn):
        """Register a validator primitive.

        Args:
            kind_version: Validator identifier (e.g., 'int.range@v1')
            fn: Validator function

        Raises:
            ValueError: If validator is already registered
        """
        if kind_version in self._validators:
            logger.warning(f"Duplicate validator registration: {kind_version}")
            raise ValueError(f"Duplicate validator: {kind_version}")

        self._validators[kind_version] = fn
        logger.debug(f"Registered validator: {kind_version}")

    def get(self, kind: str, version: str) -> ValidatorFn:
        """Get validator by kind and version.

        Args:
            kind: Validator kind (e.g., 'int.range')
            version: Validator version (e.g., 'v1')

        Returns:
            Validator function

        Raises:
            KeyError: If validator not found
        """
        key = f"{kind}@{version}"
        if key not in self._validators:
            raise KeyError(
                f"Unknown validator: {key}. Available validators: {self.list_validators()}"
            )
        return self._validators[key]

    def list_validators(self) -> List[str]:
        """List all registered validators.

        Returns:
            Sorted list of validator identifiers (e.g., ['int.enum@v1', 'int.range@v1'])
        """
        return sorted(self._validators.keys())

    def has_validator(self, kind: str, version: str) -> bool:
        """Check if validator exists.

        Args:
            kind: Validator kind
            version: Validator version

        Returns:
            True if validator is registered
        """
        key = f"{kind}@{version}"
        return key in self._validators


__all__ = ["ValidatorRegistry", "ValidatorFn"]
