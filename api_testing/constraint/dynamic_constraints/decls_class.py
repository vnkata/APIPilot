"""DeclsClass model for Beet.

@author: Juan C. Alonso
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING
from .variable.variable_utils import HIERARCHY_SEPARATOR

if TYPE_CHECKING:
    from .decls_enter import DeclsEnter
    from .decls_exit import DeclsExit


class GenerateInstrumentation:
    """Minimal local instrumentation placeholder."""
    HIERARCHY_SEPARATOR = HIERARCHY_SEPARATOR

    @classmethod
    def add_new_decls_class(cls, decls_class: Any) -> None:
        # Placeholder: if user needs global registry, extend here
        pass


@dataclass
class DeclsClass:
    """Represents a Daikon declarations class."""

    class_name: str
    decls_enters: List['DeclsEnter'] = field(default_factory=list)
    decls_exits: List['DeclsExit'] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Validate required fields
        if not self.class_name:
            raise ValueError("class_name is required")
    
    @staticmethod
    def set_decls_class_enter_and_exit(
        endpoint: str,
        operation_name: str, 
        variable_name_input: str,
        operation: Any
    ) -> None:
        """Set declarations for enter and exit program points.
        
        Args:
            endpoint: API endpoint
            operation_name: Operation name
            variable_name_input: Input variable name
            operation: OpenAPI operation object
        """
        from .decls_enter import DeclsEnter
        from .decls_exit import DeclsExit
        from .nested_ppts import NestedPpts
        from .variable import get_list_of_decls_variables

        # Create a new DeclsClass instance
        decls_class = DeclsClass(endpoint)
        
        # Get variables for the enter
        enter_variables = get_list_of_decls_variables(
            variable_name_input, "input", operation
        )
        
        # List for all possible sub-exits
        decls_exits: List[DeclsExit] = []
        
        # Process all API responses
        api_responses = operation.responses
        if api_responses:
            for status_code, api_response in api_responses.items():
                output_object_name = (
                    f"{operation_name}"
                    f"{GenerateInstrumentation.HIERARCHY_SEPARATOR}Output"
                    f"{GenerateInstrumentation.HIERARCHY_SEPARATOR}{status_code}"
                )
                
                # Get nested declarations for this response
                if api_response.content:
                    for media_type in api_response.content.values():
                        nested_decls_exits = (
                            NestedPpts.get_all_nested_decls_exits(
                                endpoint,
                                operation_name,
                                variable_name_input,
                                enter_variables,
                                output_object_name,
                                media_type,
                                status_code,
                            )
                        )
                        decls_exits.extend(nested_decls_exits)
        
        # Create DeclsEnter instances based on exits
        decls_enters: List[DeclsEnter] = []
        for decls_exit in decls_exits:
            decls_enter = DeclsEnter(
                endpoint,
                operation_name,
                variable_name_input,
                operation,
                "input",
                decls_exit.get_name_suffix(),
                decls_exit.get_status_code(),
            )
            decls_enters.append(decls_enter)
        
        decls_class.set_decls_enters(decls_enters)
        decls_class.set_decls_exits(decls_exits)
        GenerateInstrumentation.add_new_decls_class(decls_class)
    
    def add_decls_enters(self, decls_enters: List['DeclsEnter']) -> None:
        """Add declarations for enter program points."""
        self.decls_enters.extend(decls_enters)

    def add_decls_exits(self, decls_exits: List['DeclsExit']) -> None:
        """Add declarations for exit program points."""
        self.decls_exits.extend(decls_exits)

    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        res = f"ppt {self.class_name}:::CLASS\nppt-type class\n"
        
        for enter in self.decls_enters:
            res += f"\n{enter}\n"
        
        for exit_ in self.decls_exits:
            res += f"\n{exit_}\n"
        
        return res
