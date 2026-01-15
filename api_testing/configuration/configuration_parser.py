from dataclasses import asdict
import os
from typing import List, Dict, Any, Union, Optional
import json
from api_testing.inputs import RandomGeneratorFactory
from api_testing.inputs.random_number_generator import DataType
from api_testing.models.configuration_model import FieldConfiguration, OperationConfiguration
from api_testing.models.specification_model import ItemProperties, ParameterProperties
from api_testing.prompts.parameter_random_mapper import ParameterRandomMapper
from api_testing.utils import flatten_json_schema
from api_testing.utils.log import getLogger

class ConfigurationParser:
    def __init__(self, spec_parser=None, model=None, cache_dir=None):
        self.spec_parser = spec_parser
        self.model = model
        self.configurations: List[OperationConfiguration] = []
        self.cache_file = os.path.join(
            cache_dir, "configuration.json")
        self.parameter_random_mapper = ParameterRandomMapper(llm=model)
        self.logger = getLogger(__name__)
        self.load_or_initialize()

    def update_conf(self):
        pass
    def load_or_initialize(self):
        if os.path.exists(self.cache_file):
            print(f"Loading Configuration from cache: {self.cache_file}")
            with open(self.cache_file, "r") as file:
                data = json.load(file)
                self.configurations = [ OperationConfiguration.from_dict(item) for item in data]

        else:
            print("Cache file not found. Initializing Configuration...")
            self.parse()
            self.json_output()
    
    def parse(self) -> List[OperationConfiguration]:
        operations = self.spec_parser.operations
        for operation in operations.values():
            gpt_inferences = {
                "params": {},
                "request_body": {}
            }    
            # Standardize naming access for OperationProperties
            self.logger.debug("Conf for Prompt: " + operation.uuid)
            op_config = OperationConfiguration(
                method= getattr(operation, "http_method", None),
                endpoint= getattr(operation, "endpoint_path", None) 
            )
            # --- 1. Process Parameters (Handles deepObject and Flat Params) ---
            for param_name, param_details in operation.parameters.items():
                # Check if the parameter is an object (deepObject style)
                op_config.params[param_name] = self._process_field(param_details)
                if op_config.params[param_name].type == "PENDING_GPT":
                    gpt_inferences["params"][param_name] = param_details
            # --- 2. Process Request Body (Handles MIME types and Deep Nesting) ---
            if hasattr(operation, "request_body"):
                body_schemas = {}
                for schema in operation.request_body.values():
                    flattened_body = flatten_json_schema(schema.to_dict())
                    body_schemas.update(flattened_body)
                
                for property,details in body_schemas.items():
                    item_details = ItemProperties(**details)
                    op_config.request_body[property] = self._process_field(item_details, path=property)
                    if op_config.request_body[property].type == "PENDING_GPT":
                        gpt_inferences["request_body"][property] = item_details
            # --- 3. Process Parameters & Request Body with GPT ---
            for part, items in gpt_inferences.items():
                if len(items) > 0:
                    for result in self.gpt_parser(items):
                        field_cfg = FieldConfiguration(
                            name=result.property,
                            type=result.generator.className,
                            genParameters=result.generator.args,
                        )
                        getattr(op_config, part)[result.property] = field_cfg
                # 
            self.configurations.append(op_config)  
        return self.configurations

    def _process_field(self, item: Union[ParameterProperties, ItemProperties], path: str = None):
        """Standard entry point for judging Heuristic vs GPT for a single field."""
        name = path or getattr(item, 'name', 'unknown')
        if getattr(item, 'description', None) is None:
            return self.heuristic_parser(item, name_override=name)
        else:
            return FieldConfiguration(name=name, type="PENDING_GPT")

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

    def json_output(self):
        output = [asdict(conf) for conf in self.configurations]
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, default=str)
        print(f"Configuration saved to: {self.cache_file}")

    def gpt_parser(self, data: Union[Dict[str, ParameterProperties], Dict[str, ItemProperties]]):
        factory = RandomGeneratorFactory()
        descriptions = factory.gen_description() 
        params = {
            "genFunction": "\n".join([f"- {k}: {v}" for k, v in descriptions.items()]),
            "attributes":  "\n".join([f"- {k}: {v.to_human_readable()}" for k,v in data.items()])
        }
        results = self.parameter_random_mapper.exec(**params)
        return results