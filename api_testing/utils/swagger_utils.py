from typing import Dict, Any, List

def extract_endpoint_identifier(method: str, path: str) -> str:
    """
    Takes a specific method and path and returns the dedicated 
    string identifier in 'method-path' format.
    
    Example Input: "GET", "/projects/{id}"
    Example Output: "get-/projects/{id}"
    """
    # Standardize method to lowercase and concatenate with path
    return f"{method.lower()}-{path}"

def get_all_identifiers(swagger_spec: Dict[str, Any]) -> List[str]:
    """
    Utility to extract all valid 'method-path' identifiers from a spec.
    """
    identifiers = []
    paths = swagger_spec.get('paths', {})
    valid_methods = ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']
    
    for path, methods in paths.items():
        for method in methods:
            if method.startswith('x-') or method.lower() not in valid_methods:
                continue
            identifiers.append(extract_endpoint_identifier(method, path))
            
    return identifiers