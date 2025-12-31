from dataclasses import asdict
from typing import List, Dict, Any, Union, Optional
import json
from api_testing.inputs import RandomGeneratorFactory
from api_testing.inputs.random_number_generator import DataType
from api_testing.models.configuration_model import FieldConfiguration, OperationConfiguration
from api_testing.models.specification_model import ItemProperties, ParameterProperties

class ConfigurationParser:
    def __init__(self, spec_parser=None, model=None):
        self.spec_parser = spec_parser
        self.model = model
        self.configurations: List[OperationConfiguration] = []

    def parse(self) -> List[OperationConfiguration]:
        operations = self.spec_parser.operations
        gpt_inferences = []
        for operation in operations.values():
            # Standardize naming access for OperationProperties
            method = getattr(operation, "http_method", None) 
            endpoint = getattr(operation, "endpoint_path", None) 

            op_config = OperationConfiguration(
                method=method,
                endpoint=endpoint
            )

            # --- 1. Process Parameters (Handles deepObject and Flat Params) ---
            for param_name, param_details in operation.parameters.items():
                # Check if the parameter is an object (deepObject style)
                schema = param_details.schema
                if schema and (schema.type == "object" or schema.properties):
                    flattened_params = self._flatten_schema(schema, prefix=param_name, location="params")
                    op_config.params.update(flattened_params)
                else: # to
                    self._process_field(param_details, op_config.params, "params", method, endpoint)
                 
            # --- 2. Process Request Body (Handles MIME types and Deep Nesting) ---
            if hasattr(operation, "request_body"):
                for schema in operation.request_body.values():
                    # This recursively flattens every property in the body
                    flattened_body = self._flatten_schema(schema, location="body")
                    op_config.reqbody.update(flattened_body)
                    break # Process the first valid MIME type (usually form-urlencoded)

            self.configurations.append(op_config)
        return self.configurations

    def _process_field(self, item: Union[ParameterProperties, ItemProperties], container: dict, location: str, method: str, endpoint: str, path: str):
        """Standard entry point for judging Heuristic vs GPT for a single field."""
        name = path or getattr(item, 'name', 'unknown')
        description = getattr(item, 'description', None)

        if description is None:
            container[name] = self.heuristic_parser(item, name_override=name)
        else:
            self.gpt_tasks.append({
                "endpoint": f"{method} {endpoint}",
                "location": location,
                "path": name,
                "parameter": item
            })
            container[name] = FieldConfiguration(name=name, type="PENDING_GPT")

    def _flatten_schema(self, schema: ItemProperties, prefix: str = "", location: str = "body") -> Dict[str, FieldConfiguration]:
        """Recursively traverses objects and arrays to produce dot-notation keys."""
        flattened = {}
        
        # 1. Handle Objects
        if schema.properties:
            for prop_name, prop_info in schema.properties.items():
                full_path = f"{prefix}.{prop_name}" if prefix else prop_name
                
                if prop_info.properties:
                    # Drill down into nested objects
                    flattened.update(self._flatten_schema(prop_info, prefix=full_path, location=location))
                else:
                    # Leaf Node: Pass to judgment
                    self._process_field(prop_info, flattened, location, "Nested", "Object", path=full_path)
        
        # 2. Handle Arrays (Optional: can be expanded if you need specific item counts)
        elif schema.type == "array" and schema.items:
            # We treat the array as a single field PENDING_GPT if it has a description
            self._process_field(schema, flattened, location, "Array", "Object", path=prefix)

        return flattened

    def heuristic_parser(self, item: Union[ParameterProperties, ItemProperties], name_override: str = None) -> FieldConfiguration:
        """Normalized parser: determines generator based on type/format/enum."""
        # Fix: Determine if we use the object itself or its nested schema (ParameterProperties)
        schema_source = getattr(item, "schema", item)
        
        p_type = getattr(schema_source, "type", "string")
        p_format = getattr(schema_source, "format", None)
        p_name = name_override or getattr(item, "name", "unknown")

        config = FieldConfiguration(name=p_name)

        match p_type:
            case "boolean":
                config.type = "RandomBooleanGenerator"
            case "integer" | "number":
                config.type = "RandomNumberGenerator"
                dt = DataType.INTEGER if p_type == "integer" else DataType.NUMBER
                if p_format == "int32": dt = DataType.INT32
                elif p_format == "int64" or p_format == "unix-time": dt = DataType.INT64
                elif p_format == "format": dt = DataType.FLOAT
                elif p_format == "double": dt = DataType.DOUBLE

                config.genParameters = {
                    "type": dt,
                    "min": getattr(schema_source, "minimum", None),
                    "max": getattr(schema_source, "maximum", None)
                }
            case "string":
                enum_vals = getattr(schema_source, "enum", None)
                if enum_vals:
                    config.type = "RandomInputGenerator"
                    config.genParameters = {"values": enum_vals}
                elif p_format in ["date", "date-time"]:
                    config.type = "RandomDateGenerator"
                    config.genParameters = {"format": "%Y-%m-%d %H:%M:%S"}
                else:
                    config.type = "RandomTextGenerator"
                    config.genParameters = {"mode": "sentence"}

        # Clean None values
        config.genParameters = {k: v for k, v in config.genParameters.items() if v is not None}
        return config

    def export_debug_log(self, file_path: str = "debug_config.json"):
        output = [asdict(conf) for conf in self.configurations]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, default=str)
        print(f"Debug log saved to: {file_path}")

    def gpt_parser(self, parameter: ParameterProperties):
        factory = RandomGeneratorFactory()
        descriptions = factory.gen_description()
        params = {
            "class_description": "\n".join([f"- {k}: {v}" for k, v in descriptions.items()]),
            "parameter_description": f"{parameter.name}: {parameter.to_human_readable()}"
        }
        print(params)
        results = self.parameter_random_mapper.exec(**params)
        print(results)
        print(descriptions)