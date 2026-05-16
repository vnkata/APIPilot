"""
Configuration Parser Module

This module provides functionality to parse and generate configurations for API testing operations.
It uses heuristic-based and GPT-assisted parsing to determine appropriate random value generators
for API parameters and request bodies.
"""

from collections import defaultdict
from dataclasses import asdict
import json
import os
from typing import Dict, List, Optional, Union

from api_testing.inputs import RandomGeneratorFactory
from api_testing.inputs.random_number_generator import DataType
from api_testing.models.configuration_model import FieldConfiguration, OperationConfiguration
from api_testing.models.specification_model import ItemProperties, ParameterProperties
from api_testing.prompts.parameter_random_mapper import ParameterRandomMapper
from api_testing.utils import flatten_json_schema
from api_testing.utils.log import getLogger


# Constants
RANDOM_TYPES = {
    "RandomBooleanGenerator",
    "RandomDateGenerator",
    "RandomFileGenerator",
    "RandomInputGenerator",
    "RandomTextGenerator",
}
CACHE_FILE_NAME = "configuration.json"
DEFAULT_BATCH_SIZE = 50


class ConfigurationParser:
    """
    Parser for generating API testing configurations.

    This class handles the parsing of API specifications to create configurations
    that include appropriate random value generators for parameters and request bodies.
    It supports both heuristic-based and GPT-assisted parsing strategies.
    """

    def __init__(self, spec_parser=None, model=None, cache_dir=None):
        """
        Initialize the ConfigurationParser.

        Args:
            spec_parser: The specification parser instance.
            model: The language model instance for GPT parsing.
            cache_dir: Directory path for caching configurations.
        """
        self.spec_parser = spec_parser
        self.model = model
        self.configurations: List[OperationConfiguration] = []
        self.cache_file = os.path.join(cache_dir, CACHE_FILE_NAME) if cache_dir else None
        if cache_dir and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.parameter_random_mapper = ParameterRandomMapper(llm=model)
        self.logger = getLogger(__name__)
        self.load_or_initialize()

    def update_conf(self, graph: "OperationGraph" = None, producer_map=None):
        """
        Update configurations based on operation graph and producer mappings.

        Args:
            graph: The operation graph containing edges and nodes.
            producer_map: Mapping of producer operations.
        """
        if graph is None:
            return
        if producer_map is None:
            producer_map = {}

        # Group edges by consumer operation
        edges_by_operation = defaultdict(list)
        for edge in graph.edges:
            edges_by_operation[edge.to_node.uuid].append(edge)

        # Build dependency map (consumer -> producer)
        operation_dependencies = {}

        for operation, edges in edges_by_operation.items():
            consumer_map = defaultdict(list)
            seen = defaultdict(set)

            for edge in edges:
                from_uuid = edge.from_node.uuid
                producer_lookup = producer_map.get(from_uuid, {})

                for sp in edge.similar_parameters:
                    producer = producer_lookup.get(sp.value1)
                    if not producer:
                        continue

                    key_name = sp.value1.split(".")[-1]
                    dedup_key = (producer, key_name)

                    param_config = edge.to_node.parameters.get(sp.value2)
                    is_optional = (
                        param_config.in_value != "path"
                        if param_config else False
                    )

                    if dedup_key in seen[sp.value2]:
                        continue
                    for p in producer.split(","):
                        consumer_map[sp.value2].append({
                            "resource": p,
                            "key": key_name,
                            "optional": is_optional,
                            "in_value": sp.in_value,
                        })
                    seen[sp.value2].add(dedup_key)

            operation_dependencies[operation] = consumer_map

        # Apply to endpoint configurations
        for endpoint in self.configurations:
            op_key = f"{endpoint.method}-{endpoint.endpoint}"
            consumer = operation_dependencies.get(op_key)

            if not consumer:
                continue

            for param, producers in consumer.items():
                in_value = producers[0].get("in_value") if producers else None

                # Determine source and mutator
                source = None
                mutator = None
                if in_value and "requestBody" in in_value:
                    source = "request_body"
                    mutator = endpoint.request_body.get(param)
                else:
                    source = "params"
                    mutator = endpoint.params.get(param)

                if not mutator:
                    continue

                keep_original = (
                    producers
                    and producers[0].get("optional")
                    and mutator.type in RANDOM_TYPES
                )

                clean_producers = [
                    {k: v for k, v in p.items() if k != "optional"}
                    for p in producers
                ]

                if keep_original:
                    continue

                new_field = FieldConfiguration(
                    name=param,
                    type="ProducerGenerator",
                    genParameters={"pool": clean_producers},
                )

                # Update the correct source
                if source == "params":
                    endpoint.params[param] = new_field
                elif source == "request_body":
                    endpoint.request_body[param] = new_field

        self.json_output()
    
    def load_or_initialize(self):
        """Load configurations from cache or initialize by parsing specifications."""
        if self.cache_file and os.path.exists(self.cache_file):
            self.logger.debug(f"Loading Configuration from cache: {self.cache_file}")
            try:
                with open(self.cache_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    self.configurations = [OperationConfiguration.from_dict(item) for item in data]
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.error(f"Failed to load cache file: {e}. Initializing from scratch.")
                self.parse()
                self.json_output()
        else:
            self.logger.debug("Cache file not found. Initializing Configuration...")
            self.parse()
            self.json_output()
    
    def parse(self, batch_size: int = DEFAULT_BATCH_SIZE) -> List[OperationConfiguration]:
        """
        Parse all operations and generate configurations.

        Collects fields that need GPT inference and processes them in batches.

        Args:
            batch_size: Number of fields to process in each GPT batch.

        Returns:
            List of operation configurations.
        """
        operations = self.spec_parser.operations
        pending_fields = []

        # Collect fields from all operations
        for operation in operations.values():
            self.logger.debug(f"Processing operation: {operation.uuid}")
            op_config = self._create_operation_config(operation)
            self._collect_fields_from_operation(operation, op_config, pending_fields)
            self.configurations.append(op_config)

        # Process pending fields in batches using GPT
        self._process_pending_fields_in_batches(pending_fields, batch_size)

        return self.configurations

    def _create_operation_config(self, operation) -> OperationConfiguration:
        """Create a basic operation configuration from an operation object."""
        return OperationConfiguration(
            method=getattr(operation, "http_method", None),
            endpoint=getattr(operation, "endpoint_path", None)
        )

    def _collect_fields_from_operation(self, operation, op_config: OperationConfiguration, pending_fields: list):
        """Collect fields from operation parameters and request body."""
        # Process parameters
        for param_name, param_details in operation.parameters.items():
            field_cfg = self._process_field(param_details)
            op_config.params[param_name] = field_cfg

            if field_cfg.type == "PENDING_GPT":
                pending_fields.append({
                    "operation": op_config,
                    "part": "params",
                    "field_name": param_name,
                    "item": param_details
                })

        # Process request body
        if hasattr(operation, "request_body"):
            self._collect_fields_from_request_body(operation, op_config, pending_fields)

    def _collect_fields_from_request_body(self, operation, op_config: OperationConfiguration, pending_fields: list):
        """Collect fields from the request body schema."""
        body_schemas = {}
        for mime_type, schema in operation.request_body.items():
            flattened = flatten_json_schema(schema.to_dict())
            body_schemas.update(flattened)

        for prop, details in body_schemas.items():
            field_name = prop if prop else "body"
            item_details = ItemProperties.from_dict(details)

            field_cfg = self._process_field(item_details, path=field_name)
            op_config.request_body[field_name] = field_cfg

            if field_cfg.type == "PENDING_GPT":
                pending_fields.append({
                    "operation": op_config,
                    "part": "request_body",
                    "field_name": field_name,
                    "item": item_details
                })

    def _process_pending_fields_in_batches(self, pending_fields: list, batch_size: int):
        """Process pending fields using GPT in batches."""
        for i in range(0, len(pending_fields), batch_size):
            batch = pending_fields[i:i + batch_size]
            batch_data_list = [
                {"name": meta["field_name"], "item": meta["item"]}
                for meta in batch
            ]

            results = self.gpt_parser(batch_data_list)

            for result in results:
                batch_index = int(result.idx) - 1
                if 0 <= batch_index < len(batch):
                    meta = batch[batch_index]
                    field_cfg = FieldConfiguration(
                        name=meta["field_name"],
                        type=result.generator.className,
                        genParameters=result.generator.args
                    )
                    getattr(meta["operation"], meta["part"])[meta["field_name"]] = field_cfg


    def _process_field(self, item: Union[ParameterProperties, ItemProperties], path: str = None) -> FieldConfiguration:
        """
        Determine whether to use heuristic or GPT parsing for a field.

        Args:
            item: The field item to process.
            path: Optional path override for the field name.

        Returns:
            FieldConfiguration for the field.
        """
        name = path if path is not None else getattr(item, 'name', 'unknown')
        required = getattr(item, 'required', False)
        nullable = getattr(item, 'nullable', False)
        description = getattr(item, 'description', None)

        should_use_heuristic = (
            description is None
            and (not required or nullable)
        )

        if should_use_heuristic:
            return self.heuristic_parser(item, name_override=name)
        return FieldConfiguration(name=name, type="PENDING_GPT")

    def heuristic_parser(self, item: Union[ParameterProperties, ItemProperties], name_override: str = None) -> FieldConfiguration:
        """
        Parse field using heuristic rules based on type, format, and enum values.

        Args:
            item: The field item to parse.
            name_override: Optional name override.

        Returns:
            FieldConfiguration with appropriate generator.
        """
        schema_source = getattr(item, "schema", item)

        field_type = getattr(schema_source, "type", "string")
        field_format = getattr(schema_source, "format", None)
        field_name = name_override if name_override is not None else getattr(item, "name", "unknown")

        config = FieldConfiguration(name=field_name)

        if field_type == "boolean":
            config.type = "RandomBooleanGenerator"
        elif field_type in ("integer", "number"):
            config.type = "RandomNumberGenerator"
            data_type = DataType.INTEGER if field_type == "integer" else DataType.NUMBER
            if field_format == "int32":
                data_type = DataType.INT32
            elif field_format in ("int64", "unix-time"):
                data_type = DataType.INT64
            elif field_format == "float":
                data_type = DataType.FLOAT
            elif field_format == "double":
                data_type = DataType.DOUBLE

            config.genParameters = {
                "type": data_type,
                "min": getattr(schema_source, "minimum", None),
                "max": getattr(schema_source, "maximum", None)
            }
        elif field_type == "string":
            enum_values = getattr(schema_source, "enum", None)
            if enum_values:
                config.type = "RandomInputGenerator"
                config.genParameters = {"values": enum_values}
            elif field_format in ("date", "date-time"):
                config.type = "RandomDateGenerator"
            elif field_format == "file":
                config.type = "RandomFileGenerator"
            else:
                config.type = "RandomTextGenerator"
                config.genParameters = {"mode": "sentence"}

        # Remove None values from parameters
        if config.genParameters:
            config.genParameters = {k: v for k, v in config.genParameters.items() if v is not None}

        return config

    def json_output(self):
        """Save configurations to the cache file."""
        if not self.cache_file:
            return
        output = [asdict(conf) for conf in self.configurations]
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=4, default=str)
            self.logger.debug(f"Configuration saved to: {self.cache_file}")
        except IOError as e:
            self.logger.error(f"Failed to save configuration: {e}")

    def gpt_parser(self, batch_data_list: list):
        """
        Use GPT to parse a batch of fields.

        Args:
            batch_data_list: List of field data to process.

        Returns:
            GPT parsing results.
        """
        factory = RandomGeneratorFactory()
        descriptions = factory.gen_description()
        attributes_lines = [
            f"# {idx} {f['name']}: {f['item'].to_human_readable()}"
            for idx, f in enumerate(batch_data_list, start=1)
        ]

        params = {
            "genFunction": "\n".join([f"- {k}: {v}" for k, v in descriptions.items()]),
            "attributes": "\n".join(attributes_lines)
        }
        return self.parameter_random_mapper.exec(**params)

    def export_debug_log(self, filepath: str):
        """
        Export configurations to a debug log file.

        Args:
            filepath: Path to the debug log file.
        """
        output = [asdict(conf) for conf in self.configurations]
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=4, default=str)
            self.logger.debug(f"Debug log exported to: {filepath}")
        except IOError as e:
            self.logger.error(f"Failed to export debug log: {e}")