"""DeclsEnter model for Beet."""

from typing import TYPE_CHECKING

from dataclasses import dataclass, field
from typing import Any, List

from api_testing.constraint.dynamic_constraints.variable.variable_utils import HIERARCHY_SEPARATOR
from .variable.variable_utils import HIERARCHY_SEPARATOR


@dataclass
class DeclsEnter:
    """Represents an ENTER point in a Daikon declarations file."""
    endpoint: str
    operation_name: str
    variable_name_input: str
    operation: Any
    root_variable_name: str
    name_suffix: str
    status_code: str
    decls_variables: List[Any] = field(init=False)

    def __post_init__(self) -> None:
        from .variable.enter_variables import get_list_of_decls_variables
        self.decls_variables = get_list_of_decls_variables(
            self.variable_name_input,
            self.root_variable_name,
            self.operation,
        )

    def get_enter_name(self) -> str:
        return (
            f"{self.endpoint}{HIERARCHY_SEPARATOR}{self.operation_name}"
            f"{HIERARCHY_SEPARATOR}{self.status_code}{self.name_suffix}()"
        )

    def __str__(self) -> str:
        return (
            f"ppt {self.get_enter_name()}:::ENTER\n"
            f"ppt-type enter\n"
            f"{self.decls_variables}"
        )

    def generate_dtrace(self, test_case: Any) -> str:
        return f"{self.get_enter_name()}:::ENTER\n\n"    
    def get_enter_name(self) -> str:
        """Get the enter method name.
        
        Returns:
            Enter method name in Daikon format
        """
        return (f"{self.endpoint}{HIERARCHY_SEPARATOR}{self.operation_name}"
                f"{HIERARCHY_SEPARATOR}{self.status_code}{self.name_suffix}()")
    
    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        return (f"ppt {self.get_enter_name()}:::ENTER\n"
                f"ppt-type enter\n"
                f"{self.decls_variables}")
    
    def generate_dtrace(self, test_case: 'TestCase') -> str:
        """Generate dtrace entry for test case.
        
        Args:
            test_case: Test case to generate dtrace for
            
        Returns:
            Dtrace entry string
        """
        res = f"{self.get_enter_name()}:::ENTER\n"
        # This would require implementing dtrace generation logic
        res += "\n"
        return res
