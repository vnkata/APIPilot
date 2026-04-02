from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from api_testing.constraint.dynamic_constraints.decls_class import DeclsClass
from api_testing.constraint.dynamic_constraints.variable.variable_utils import HIERARCHY_SEPARATOR
from api_testing.utils.http import isSuccessful


class Comparability(str, Enum):
    IMPLICIT = "implicit"
    NONE = "none"


class GenerateInstrumentation:
    """Minimal local instrumentation implementation for dynamic constraints."""
    HIERARCHY_SEPARATOR = HIERARCHY_SEPARATOR
    decls_classes = []
    
    def add_new_decls_class(decls_class: DeclsClass) -> None:
        """Add a new declarations class.
        
        Args:
            decls_class: DeclsClass object to add
        """
        # self.decls_classes.append(decls_class)


@dataclass
class DeclsFile:
    """Model for Daikon declaration file generation."""
    version: float
    comparability: Comparability
    decls_classes: List
    spec_parser: Optional[Any] = None

    operations: Dict[str, Any] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.spec_parser or not hasattr(self.spec_parser, "operations"):
            raise ValueError("spec_parser with operations attribute is required")

        self.operations = self.spec_parser.operations

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def parse_operations(self) -> None:
        """Parse OpenAPI operations and generate DeclsClass definitions."""
        decls_classes = []
        for operation_name, operation in (self.operations or {}).items():
            endpoint = f"{operation.http_method.upper()}-{operation.endpoint_path}"
            decls_classes.append(self._process_operation(endpoint, operation_name, operation))
        self.decls_classes = decls_classes
        return decls_classes
    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------
    def _process_operation(
        self,
        endpoint: str,
        operation_name: str,
        operation: Any,
        variable_name_input: str = "input",
    ) -> None:
        """Parse a single operation and inject declarations into instrumentation."""
        from .decls_enter import DeclsEnter
        from .decls_exit import DeclsExit
        from .nested_ppts import get_all_nested_decls_exits
        from .variable import get_list_of_decls_variables

        decls_class = DeclsClass(endpoint)

        enter_variables = get_list_of_decls_variables(
            variable_name_input,
            "input",
            operation,
        )

        decls_exits: List[DeclsExit] = []

        for status_code, api_response in (operation.responses or {}).items():
            suffix = (
                f"{operation_name}"
                f"{HIERARCHY_SEPARATOR}Output"
                f"{HIERARCHY_SEPARATOR}{status_code}"
            )
            print(suffix)
            if isSuccessful(status_code) and api_response.content:
                for media_type in api_response.content.values():
                    nested_exits = get_all_nested_decls_exits(
                        endpoint,
                        operation_name,
                        variable_name_input,
                        enter_variables,
                        suffix,
                        media_type,
                        status_code,
                    )
                    decls_exits.extend(nested_exits)

        decls_enters = [
            DeclsEnter(
                endpoint,
                operation_name,
                variable_name_input,
                operation,
                "input",
                exit_.name_suffix,
                exit_.status_code,
            )
            for exit_ in decls_exits
        ]
        print(decls_enters)
        decls_class.add_decls_enters(decls_enters)
        decls_class.add_decls_exits(decls_exits)
        return decls_class

    # ----------------------------------------------------------------------
    # Property helpers
    # ----------------------------------------------------------------------
    @property
    def class_name(self) -> str:
        return getattr(self, "_class_name", "")

    @class_name.setter
    def class_name(self, value: str) -> None:
        self._class_name = value

    @property
    def decls_enters(self) -> List[Any]:
        return getattr(self, "_decls_enters", [])

    @decls_enters.setter
    def decls_enters(self, value: List[Any]) -> None:
        self._decls_enters = value

    @property
    def decls_exits(self) -> List[Any]:
        return getattr(self, "_decls_exits", [])

    @decls_exits.setter
    def decls_exits(self, value: List[Any]) -> None:
        self._decls_exits = value

    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        res = f"decl-version {self.version}\nvar-comparability {self.comparability}\n"
        
        for decls_class in self.decls_classes:
            res += f"\n{decls_class}\n"
        
        return res
