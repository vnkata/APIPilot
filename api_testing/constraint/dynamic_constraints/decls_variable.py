"""Variable model for Beet."""

from dataclasses import dataclass, field
from typing import List, Optional
from .variable.variable_utils import encode_variable_name


@dataclass
class DeclsVariable:
    """Represents a variable declaration in Daikon format."""
    variable_name: str
    variable_path: Optional[str]
    var_kind: str
    dec_type: str
    rep_type: str
    enclosing_var: Optional[str] = None
    is_array: bool = False
    enclosed_variables: List['DeclsVariable'] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.variable_path:
            self.variable_name = f"{self.variable_path}.{encode_variable_name(self.variable_name)}"
        else:
            self.variable_name = encode_variable_name(self.variable_name)

        self.var_kind = encode_variable_name(self.var_kind)

        if self.is_array:
            self.dec_type = f"{self.dec_type}[]"
            self.rep_type = f"{self.rep_type}[]"

    def __str__(self) -> str:
        enclosing_var_str = f"\tenclosing-var {self.enclosing_var}\n" if self.enclosing_var else ""
        array_str = "\tarray 1\n" if self.is_array else ""

        output = (
            f"variable {self.variable_name}\n"
            f"\tvar-kind {self.var_kind}\n"
            f"{enclosing_var_str}"
            f"{array_str}"
            f"\tdec-type {self.dec_type}\n"
            f"\trep-type {self.rep_type}"
        )

        for var in self.enclosed_variables:
            output += f"\n{var}"

        return output
