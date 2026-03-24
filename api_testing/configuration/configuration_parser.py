from collections import defaultdict
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
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        self.parameter_random_mapper = ParameterRandomMapper(llm=model)
        self.logger = getLogger(__name__)
        self.load_or_initialize()

    def update_conf(self, graph: "OperationGraph" = None, producer_map=None):
        if graph is None:
            return
        if producer_map is None:
            producer_map = {}

        # Step 1: group edges by consumer operation
        edges_by_operation = defaultdict(list)
        for edge in graph.edges:
            edges_by_operation[edge.to_node.uuid].append(edge)

        # Step 2: build dependency map (consumer -> producer)
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

                    key_name = sp.value1.split(".")[-1] # {"value1": "category.id","value2": "category.id","in_value": "response to requestBody via gpt"},
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
                            "in_value": sp.in_value,  # 🔥 thêm dòng này
                        })
                    seen[sp.value2].add(dedup_key)

            operation_dependencies[operation] = consumer_map

        # Step 3: apply to endpoint config
        RANDOM_TYPES = {
            "RandomBooleanGenerator",
            "RandomDateGenerator",
            "RandomFileGenerator",
            "RandomInputGenerator",
            "RandomTextGenerator",
        }

        for endpoint in self.configurations:
            op_key = f"{endpoint.method}-{endpoint.endpoint}"
            consumer = operation_dependencies.get(op_key)

            if not consumer:
                continue

            for param, producers in consumer.items():
                in_value = producers[0].get("in_value") if producers else None

                # 🔥 tìm mutator ở cả params và request_body
                source = None
                mutator = None
                if in_value and "requestBody" in in_value:
                    source  = "request_body"
                    mutator = endpoint.request_body.get(param)
                else:
                    source  = "params"
                    mutator = endpoint.params.get(param)


                # if mutator:
                #     source = "params"
                # else:
                #     mutator = endpoint.request_body.get(param) if endpoint.request_body else None
                #     if mutator:
                #         

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

                # 🔥 update đúng source
                if source == "params":
                    endpoint.params[param] = new_field
                elif source == "request_body":
                    endpoint.request_body[param] = new_field

        self.json_output()
    
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
    
    def parse(self, batch_size: int = 50) -> List[OperationConfiguration]:
        """
        Parse all operations, collect fields that need GPT inference,
        and batch them (no deduplication).
        """

        operations = self.spec_parser.operations
        pending_fields = []

        # ------------------ COLLECT FIELDS ------------------
        for operation in operations.values():
            self.logger.debug("Processing operation: " + operation.uuid)

            op_config = OperationConfiguration(
                method=getattr(operation, "http_method", None),
                endpoint=getattr(operation, "endpoint_path", None)
            )

            # ---- Parameters ----
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

            # ---- Request Body ----
            if hasattr(operation, "request_body"):
                body_schemas = {}
                for mime_type, schema in operation.request_body.items():
                    # if mime_type == "application/octet-stream":
                    #     body_schemas.update({
                    #         "_raw_binary": schema.to_dict()
                    #     })
                    # else:
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

            self.configurations.append(op_config)

        # ------------------ BATCH GPT INFERENCE ------------------

        for i in range(0, len(pending_fields), batch_size):
            batch = pending_fields[i:i + batch_size]

            # prepare batch_data for GPT
            batch_data_list = []
            for meta in batch:
                batch_data_list.append({
                    "name": meta["field_name"],
                    "item": meta["item"]
                })

            # call GPT once per batch
            results = self.gpt_parser(batch_data_list)

            # map results back to the operation configuration
            for result in results:
                # idx từ GPT là zero-based
                batch_index = int(result.idx) - 1
                if batch_index < 0 or batch_index >= len(batch):
                    continue  # tránh lỗi nếu idx ngoài range

                meta = batch[batch_index]  # lấy meta đúng theo thứ tự batch
                # tạo FieldConfiguration
                field_cfg = FieldConfiguration(
                    name=meta["field_name"],        # tên field gốc
                    type=result.generator.className,
                    genParameters=result.generator.args
                )

                # cập nhật vào đúng operation / part / field_name
                getattr(meta["operation"], meta["part"])[meta["field_name"]] = field_cfg

        return self.configurations


    def _process_field(self, item: Union[ParameterProperties, ItemProperties], path: str = None):
        """Standard entry point for judging Heuristic vs GPT for a single field."""
        # Use 'is not None' to handle empty string path correctly (empty string is falsy but valid)
        name = path if path is not None else getattr(item, 'name', 'unknown')
        required = getattr(item, 'required', False)
        nullable = getattr(item, 'nullable', False)
        description = getattr(item, 'description', None) # 
        should_use_heuristic = (
            description is None
            and (required is False or nullable is True)
        )
        if should_use_heuristic:
            return self.heuristic_parser(item, name_override=name)
        return FieldConfiguration(name=name, type="PENDING_GPT")

    def heuristic_parser(self, item: Union[ParameterProperties, ItemProperties], name_override: str = None) -> FieldConfiguration:
        """Normalized parser: determines generator based on type/format/enum."""
        # Fix: Determine if we use the object itself or its nested schema (ParameterProperties)
        schema_source = getattr(item, "schema", item)
        
        p_type = getattr(schema_source, "type", "string")
        p_format = getattr(schema_source, "format", None)
        # Use 'is not None' to handle empty string name correctly
        p_name = name_override if name_override is not None else getattr(item, "name", "unknown")

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
                elif p_format and p_format in ["date", "date-time"]:
                    config.type = "RandomDateGenerator"
                    config.genParameters = {"format": "%Y-%m-%d %H:%M:%S"}
                elif p_format and p_format in ["file"]:
                    config.type = "RandomFileGenerator"
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

    def gpt_parser(self, batch_data_list: list):
        factory = RandomGeneratorFactory()
        descriptions = factory.gen_description() 
        attributes_lines = []
        for idx, f in enumerate(batch_data_list, start=1):
            attributes_lines.append(f"# {idx} {f['name']}: {f['item'].to_human_readable()}")

        params = {
            "genFunction": "\n".join([f"- {k}: {v}" for k, v in descriptions.items()]),
            "attributes":  "\n".join(attributes_lines)
        }
        results = self.parameter_random_mapper.exec(**params)
        return results
    def export_debug_log(self, filepath: str):
        output = [asdict(conf) for conf in self.configurations]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=4, default=str)
        print(f"Debug log exported to: {filepath}")