"""DeclsEnter model for Beet.

Represents an ENTER point in a Daikon declarations file.
Generates dtrace entries for API test case inputs.

Author: Juan C. Alonso (Java), converted to Python
"""

from dataclasses import dataclass, field
from typing import Any, List

from api_testing.constraint.dynamic_constraints.variable.variable_utils import HIERARCHY_SEPARATOR


@dataclass
class DeclsEnter:
    """Represents an ENTER point in a Daikon declarations file.
    
    Handles the generation of ENTER program points for API operations,
    including variable declarations and dtrace generation.
    """
    endpoint: str
    operation_name: str
    variable_name_input: str
    operation: Any
    root_variable_name: str
    name_suffix: str
    status_code: str
    decls_variables: List[Any] = field(init=False)

    def __post_init__(self) -> None:
        """Initialize decls_variables after object creation."""
        from .variable.enter_variables import get_list_of_decls_variables
        self.decls_variables = get_list_of_decls_variables(
            self.variable_name_input,
            self.root_variable_name,
            self.operation,
        )

    def get_enter_name(self) -> str:
        """Get the enter method name in Daikon format.
        
        Returns:
            Formatted enter method name: endpoint.operation.status_code_suffix()
        """
        return (
            f"{self.endpoint}{HIERARCHY_SEPARATOR}{self.operation_name}"
            f"{HIERARCHY_SEPARATOR}{self.status_code}{self.name_suffix}()"
        )

    def __str__(self) -> str:
        """Convert to Daikon declarations format.
        
        Returns:
            String representation in .decls file format
        """
        return (
            f"ppt {self.get_enter_name()}:::ENTER\n"
            f"ppt-type enter\n"
            f"{self.decls_variables}"
        )

    def generate_dtrace(self, test_case: Any) -> str:
        """Generate dtrace content for this enter point based on the test case.
        
        Based on Java implementation:
        public String generateDtrace(TestCase testCase) {
            String res = this.getEnterName() + ":::ENTER";
            res = res + "\n" + declsVariables.generateDtraceEnter(testCase);
            res = res + "\n";
            return res;
        }
        """
        res = f"{self.get_enter_name()}:::ENTER"
        
        # Generate dtrace enter for the decls variables (single DeclsVariable object)
        if hasattr(self.decls_variables, 'generate_dtrace_enter'):
            res += "\n" + self.decls_variables.generate_dtrace_enter(test_case)
        
        res += "\n"
        
        return res
