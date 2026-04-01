"""DeclsExit model for Beet."""

from typing import TYPE_CHECKING, Optional, List
from agora.beet.variable.variable_utils import HIERARCHY_SEPARATOR

if TYPE_CHECKING:
    from agora.beet.model.decls_variable import DeclsVariable
    from agora.beet.model.test_case import TestCase


class DeclsExit:
    """Represents an exit program point in Daikon format."""
    
    # Class variable to track exit numbers
    _exit_counter = 1
    
    def __init__(
        self,
        endpoint: str,
        operation_name: str,
        variable_name_input: str,
        enter_decls_variables: 'DeclsVariable',
        variable_name_output: str,
        schema_or_type,  # Can be Schema object or string
        name_suffix: str,
        status_code: str,
        variable_name: Optional[str] = None
    ):
        """Initialize DeclsExit.
        
        Args:
            endpoint: API endpoint
            operation_name: Name of the operation
            variable_name_input: Input variable name
            enter_decls_variables: Enter variables
            variable_name_output: Output variable name
            schema_or_type: Schema object or type string
            name_suffix: Suffix for the name
            status_code: HTTP status code
            variable_name: Optional variable name for array schemas
        """
        self.endpoint = endpoint
        self.operation_name = operation_name
        self.variable_name_input = variable_name_input
        self.name_suffix = name_suffix
        self.status_code = status_code
        
        self.exit_number = DeclsExit._exit_counter
        DeclsExit._exit_counter += 1
        
        self.enter_decls_variables = enter_decls_variables
        self.is_nested_array = False
        
        # Handle different types of schemas
        # This would need implementation based on the schema type
        self.exit_decls_variables = None
    
    def get_exit_name(self) -> str:
        """Get the exit method name.
        
        Returns:
            Exit method name in Daikon format
        """
        return (f"{self.endpoint}{HIERARCHY_SEPARATOR}{self.operation_name}"
                f"{HIERARCHY_SEPARATOR}{self.status_code}{self.name_suffix}()")
    
    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        res = f"ppt {self.get_exit_name()}:::EXIT\n"
        res += "ppt-type exit\n"
        if self.exit_decls_variables:
            res += str(self.exit_decls_variables)
        return res
    
    def generate_dtrace(self, test_case: 'TestCase') -> str:
        """Generate dtrace entry for test case.
        
        Args:
            test_case: Test case to generate dtrace for
            
        Returns:
            Dtrace entry string
        """
        res = f"{self.get_exit_name()}:::EXIT\n"
        # This would require implementing dtrace generation logic
        res += "\n"
        return res
    
    @classmethod
    def reset_exit_counter(cls) -> None:
        """Reset the exit counter. Useful for testing."""
        cls._exit_counter = 1
