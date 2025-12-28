import inspect
from typing import Dict, Any

class BaseProvider:
    """
    Base class for all heuristic providers. 
    Provides self-documentation capabilities for LLM prompt generation.
    """
    def get_report(self) -> Dict[str, Any]:
        """
        Scans class methods and extracts descriptions and parameters.
        """
        report = {}
        # Get all routines (methods) of the instance
        methods = inspect.getmembers(self, predicate=inspect.isroutine)
        
        for name, method in methods:
            # Skip private methods and the report function itself
            if name.startswith('_') or name == 'get_report':
                continue
            
            # 1. Extract description from Docstring
            description = inspect.getdoc(method) or "No description provided."
            
            # 2. Extract parameters and default values
            signature = inspect.signature(method)
            params = {}
            for p_name, param in signature.parameters.items():
                if p_name == 'self':
                    continue
                
                # Check if the parameter is mandatory
                is_required = param.default == inspect.Parameter.empty
                default_val = "REQUIRED" if is_required else param.default
                
                params[p_name] = {
                    "default": default_val,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "any"
                }

            report[name] = {
                "description": description,
                "parameters": params
            }
        return report