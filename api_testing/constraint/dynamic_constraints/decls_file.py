from enum import Enum
from typing import Any, List

class Comparability(str, Enum):
    IMPLICIT = "implicit"
    NONE = "none"

class DeclsFile:
    def __init__(
        self,
        version: float,
        comparability: Comparability,
        decls_classes: List,
        spec_parser=None

    ):
        """Initialize DeclsFile.
        
        Args:
            version: Version of the declarations file
            comparability: Comparability level
            decls_classes: List of declarations classes
        """
        self.version = version
        self.comparability = comparability
        self.decls_classes = decls_classes
        self.spec_parser = spec_parser
        self.operations = self.spec_parser.operations

    def _parse_operations(self):
        """Parse operations to create DeclsClass instances."""
        # This method would contain logic to parse API operations and create DeclsClass instances
        for operation_name, operation in self.operations.items():
            endpoint = f"{operation.http_method.upper()}-{operation.endpoint_path}"
            variable_name_input = "input"  # This can be customized based on the operation
            self.set_decls_class_enter_and_exit(endpoint, operation_name, variable_name_input, operation)

        pass
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
        from agora.beet.model.decls_enter import DeclsEnter
        from agora.beet.model.decls_exit import DeclsExit
        from agora.beet.main import GenerateInstrumentation
        from agora.beet.pptNesting import NestedPpts
        from agora.beet.variable import EnterVariables
        
        # Create a new DeclsClass instance
        decls_class = DeclsClass(endpoint)
        
        # Get variables for the enter
        enter_variables = EnterVariables.get_list_of_decls_variables(
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
    
    def get_class_name(self) -> str:
        """Get the class name."""
        return self.class_name
    
    def set_class_name(self, class_name: str) -> None:
        """Set the class name."""
        self.class_name = class_name
    
    def get_decls_enters(self) -> List['DeclsEnter']:
        """Get the list of DeclsEnter instances."""
        return self.decls_enters
    
    def set_decls_enters(self, decls_enters: List['DeclsEnter']) -> None:
        """Set the list of DeclsEnter instances."""
        self.decls_enters = decls_enters
    
    def get_decls_exits(self) -> List['DeclsExit']:
        """Get the list of DeclsExit instances."""
        return self.decls_exits
    
    def set_decls_exits(self, decls_exits: List['DeclsExit']) -> None:
        """Set the list of DeclsExit instances."""
        self.decls_exits = decls_exits
    
    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        res = f"ppt {self.class_name}:::CLASS\nppt-type class\n"
        
        for enter in self.decls_enters:
            res += f"\n{enter}\n"
        
        for exit_ in self.decls_exits:
            res += f"\n{exit_}\n"
        
        return res
