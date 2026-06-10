from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from api_testing.constraint.dynamic_constraints.decls_class import DeclsClass
from api_testing.constraint.dynamic_constraints.variable.variable_utils import HIERARCHY_SEPARATOR
from api_testing.utils.http import isSuccessful
from .decls_enter import DeclsEnter
from .decls_exit import DeclsExit
from .nested_ppts import get_all_nested_decls_exits
from .variable import get_list_of_decls_variables


class Comparability(str, Enum):
    IMPLICIT = "implicit"
    NONE = "none"


@dataclass
class DeclsFile:
    """Model for Daikon declaration file generation."""
    version: float
    comparability: Comparability
    decls_classes: List = field(default_factory=list)
    spec_parser: Optional[Any] = None

    operations: Dict[str, Any] = field(init=False, repr=False)

    def __init__(
        self,
        version: float,
        comparability: Comparability = Comparability.IMPLICIT,
        decls_classes: Optional[List[DeclsClass]] = [],
        spec_parser: Optional[Any] = None,
        cache_dir=None
    ) -> None:
        self.version = version
        self.comparability = comparability
        self.decls_classes = decls_classes if decls_classes is not None else []
        self.spec_parser = spec_parser
        self.cache_file = os.path.join(
            cache_dir, "declsFiles.decls")

        if not self.spec_parser or not hasattr(self.spec_parser, "operations"):
            raise ValueError("spec_parser with operations attribute is required")

        self.operations = self.spec_parser.operations

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------
    def parse_operations(self) -> None:
        """Parse OpenAPI operations and generate DeclsClass definitions."""
        decls_classes = []
        # paths = [ opt.endpoint_path for opt in self.operations.values()]
        # common_path  = os.path.commonprefix(paths).rstrip("/")

        for operation_name, operation in (self.operations or {}).items():
            # endpoint_path = operation.endpoint_path.replace(common_path, "") # only get relative path
            # operation.endpoint_path = endpoint_path
            endpoint = f"{operation.http_method.lower()}-{operation.endpoint_path}"
            # endpoint = f"{operation.http_method.upper()}-{endpoint_path}"
            decls_classes.append(self._process_operation(endpoint, operation_name, operation))
        self.decls_classes = decls_classes
        # self.common_path =  common_path
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
        decls_class.add_decls_enters(decls_enters)
        decls_class.add_decls_exits(decls_exits)
        return decls_class

    def save_to_file(self) -> None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", encoding="utf-8") as f:
            # Input header lines for compatibility with Daikon
            f.write("input-language OpenAPI\n")
            f.write(str(self.decls_file))

    def __str__(self) -> str:
        """Convert to Daikon declarations format."""
        res = f"decl-version {self.version}\nvar-comparability {self.comparability.lower()}\n"

        for decls_class in self.decls_classes:
            res += f"\n{decls_class}\n"

        return res
