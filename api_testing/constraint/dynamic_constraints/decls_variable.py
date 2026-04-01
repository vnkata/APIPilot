"""Variable model for Beet."""

from typing import List, Optional


class DeclsVariable:
    """Represents a variable declaration in Daikon format."""
    
    def __init__(
        self,
        variable_name: str,
        variable_path: Optional[str],
        var_kind: str,
        dec_type: str,
        rep_type: str,
        enclosing_var: Optional[str],
        is_array: bool = False
    ):
        """Initialize a DeclsVariable.
        
        Args:
            variable_name: Name of the variable
            variable_path: Path to the variable (can be None)
            var_kind: Kind of variable (field, variable, array, etc.)
            dec_type: Declaration type
            rep_type: Representation type
            enclosing_var: Name of enclosing variable
            is_array: Whether this is an array type
        """
        from agora.beet.variable.variable_utils import encode_variable_name
        
        if variable_path is None:
            self.variable_name = encode_variable_name(variable_name)
        else:
            self.variable_name = f"{variable_path}.{encode_variable_name(variable_name)}"
        
        self.var_kind = encode_variable_name(var_kind)
        
        if is_array:
            self.dec_type = f"{dec_type}[]"
            self.rep_type = f"{rep_type}[]"
        else:
            self.dec_type = dec_type
            self.rep_type = rep_type
        
        self.enclosing_var = enclosing_var
        self.enclosed_variables: List[DeclsVariable] = []
        self.is_array = is_array
    
    @property
    def variable_name(self) -> str:
        """Get the variable name."""
        return self._variable_name
    
    @variable_name.setter
    def variable_name(self, value: str) -> None:
        """Set the variable name."""
        self._variable_name = value
    
    @property
    def var_kind(self) -> str:
        """Get the variable kind."""
        return self._var_kind
    
    @var_kind.setter
    def var_kind(self, value: str) -> None:
        """Set the variable kind."""
        self._var_kind = value
    
    @property
    def dec_type(self) -> str:
        """Get the declaration type."""
        return self._dec_type
    
    @dec_type.setter
    def dec_type(self, value: str) -> None:
        """Set the declaration type."""
        self._dec_type = value
    
    @property
    def rep_type(self) -> str:
        """Get the representation type."""
        return self._rep_type
    
    @rep_type.setter
    def rep_type(self, value: str) -> None:
        """Set the representation type."""
        self._rep_type = value
    
    @property
    def enclosing_var(self) -> Optional[str]:
        """Get the enclosing variable."""
        return self._enclosing_var
    
    @enclosing_var.setter
    def enclosing_var(self, value: Optional[str]) -> None:
        """Set the enclosing variable."""
        self._enclosing_var = value
    
    @property
    def enclosed_variables(self) -> List['DeclsVariable']:
        """Get the enclosed variables."""
        return self._enclosed_variables
    
    @enclosed_variables.setter
    def enclosed_variables(self, value: List['DeclsVariable']) -> None:
        """Set the enclosed variables."""
        self._enclosed_variables = value
    
    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        enclosing_var_str = ""
        if self.enclosing_var is not None:
            enclosing_var_str = f"\tenclosing-var {self.enclosing_var}\n"
        
        array_str = ""
        if self.var_kind == "array" or self.is_array:
            array_str = "\tarray 1\n"
        
        res = (f"variable {self.variable_name}\n"
               f"\tvar-kind {self.var_kind}\n"
               f"{enclosing_var_str}"
               f"{array_str}"
               f"\tdec-type {self.dec_type}\n"
               f"\trep-type {self.rep_type}")
        
        for var in self.enclosed_variables:
            res += f"\n{var}"
        
        return res
