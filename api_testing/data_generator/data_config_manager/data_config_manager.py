import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Union

from api_testing.data_generator.heuristic_data_generator.HeuristicGenerator import HeuristicDataGenerator
from api_testing.utils.swagger_utils import extract_endpoint_identifier

@dataclass
class FieldConfig:
    function: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APIField:
    name: str
    config: Any 

@dataclass
class EndpointConfig:
    endpoint_id: str
    params: List[APIField] = field(default_factory=list)
    body: List[APIField] = field(default_factory=list)

class DataConfigManager:
    @staticmethod
    def extract_on_rule_based(spec: Dict[str, Any]) -> List[EndpointConfig]:
        endpoints_config = []
        paths = spec.get("paths", {})

        for path_url, path_item in paths.items():
            for method, op in path_item.items():
                # Use your unique ID function here
                ep_id = extract_endpoint_identifier(method, path_url)
                endpoint = EndpointConfig(endpoint_id=ep_id)

                # --- Process Params ---
                for param in op.get("parameters", []):
                    name = param.get("name")
                    location = param.get("in", "")
                    has_desc = bool(param.get("description"))
                    p_type = param.get("schema", {}).get("type", "string")
                    enum_vals = param.get("schema", {}).get("enum")

                    if location == "path" or has_desc:
                        config = {}
                    else:
                        config = HeuristicDataGenerator.infer_generation_rule(p_type, name, enum_vals)

                    endpoint.params.append(APIField(name=name, config=config))

                # --- Process Body ---
                request_body = op.get("requestBody", {})
                content = request_body.get("content", {})
                
                body_schema = {}
                for mime in ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]:
                    if mime in content:
                        body_schema = content[mime].get("schema", {})
                        break
                
                if body_schema.get("type") == "object":
                    for prop_name, prop_info in body_schema.get("properties", {}).items():
                        has_desc = bool(prop_info.get("description"))
                        b_type = prop_info.get("type", "string")
                        b_enum = prop_info.get("enum")

                        if has_desc:
                            config = {}
                        else:
                            config = HeuristicDataGenerator.infer_generation_rule(b_type, prop_name, b_enum)
                        
                        endpoint.body.append(APIField(name=prop_name, config=config))

                endpoints_config.append(endpoint)
        return endpoints_config
    @staticmethod
    def save_config_to_file(endpoints_config: List[EndpointConfig], output_path: Union[str, Path]):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([asdict(ep) for ep in endpoints_config], f, indent=4)