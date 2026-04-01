"""DeclsEnter model for Beet."""

from typing import TYPE_CHECKING
from .config import HIERARCHY_SEPARATOR



class DeclsEnter:
    """Represents an enter program point in Daikon format."""
    
    def __init__(
        self,
        endpoint: str,
        operation_name: str,
        variable_name_input: str,
        operation,  # OpenAPI operation object
        root_variable_name: str,
        name_suffix: str,
        status_code: str
    ):
        """Initialize DeclsEnter.
        
        Args:
            endpoint: API endpoint
            operation_name: Name of the operation
            variable_name_input: Input variable name
            operation: OpenAPI operation object
            root_variable_name: Root variable name
            name_suffix: Suffix for the name
            status_code: HTTP status code
        """
        from agora.beet.variable.enter_variables import get_list_of_decls_variables
        
        self.endpoint = endpoint
        self.operation_name = operation_name
        self.variable_name_input = variable_name_input
        self.name_suffix = name_suffix
        self.status_code = status_code
        
        # Generate declarations variables
        self.decls_variables = get_list_of_decls_variables(
            variable_name_input, 
            root_variable_name, 
            operation
        )
    
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
