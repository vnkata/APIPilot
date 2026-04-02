import copy
import json
import os
import re
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.request_response_constraint import RequestResponseConstraint
from api_testing.prompts.response_constraints import ResponseConstraints
from api_testing.utils import flatten_json_schema
from api_testing.utils.graph import is_nested_path_end_with
from api_testing.utils.log import getLogger

class StaticConstraintMiner:
    def __init__(self, spec_parser=None, model=None, embedding_model=None,cache_dir=None):
        self.spec_parser = spec_parser
        self.model = model
        self.embedding_model = embedding_model
        self.cache_file = os.path.join(
            cache_dir, "static_constraint_miner.json")
        self.logger = getLogger(__name__)
        # self.max_load = 
        self.operations = self.spec_parser.operations
        self.schemas = {k: v for opt in self.operations.values() for k, v in opt.schemas.items()}
        self.response_constraint = ResponseConstraints(llm=self.model)
        self.request_response = RequestResponseConstraint(llm=self.model)

    def request_response_constraints(self):
        # Implement mining constraints between request and response
        constraint = {}
        for opt_name, operation in self.operations.items():
            print(f"Processing operation: {opt_name}")
            params = {
                "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
                "summary": ((operation.summary or "") + " " + (operation.description or "")).strip(),
                "params": "\n".join(
                    [
                        f"- {k}::parameter : {v.to_human_readable()}" 
                        for k, v in operation.parameters.items() 
                    ] + [
                        f"- {k}::requestBody : {ItemProperties.from_dict(v).to_human_readable()}"
                        for k,v in operation.get_request_body().items()
                    ]
                ),
            }
            endpoint_response = operation.successful_responses
            if endpoint_response:
                main_schemas = endpoint_response.xrefs if endpoint_response.xrefs is not None else None
                newSchema = copy.deepcopy(endpoint_response)
                newSchema.xrefs = None
                cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n", "")
                cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                cleaned_string = re.sub(r'\\+', "", cleaned_string)
                params["main_response"] = f"- {main_schemas}: {cleaned_string}"
                operation_schemas = {k: v for k, v in operation.schemas.items() if k != main_schemas}
                data_schemas = []
                for k, v in operation_schemas.items():
                    v_schemas = copy.deepcopy(v)
                    v_schemas.xrefs = None
                    cleaned_string = v_schemas.to_human_readable().replace('\\n', '').replace("\n", "")
                    cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                    cleaned_string = re.sub(r'\\+', "", cleaned_string)
                    operation_schemas[k] = cleaned_string
                    data_schemas.append(f"- {k}: {cleaned_string}")
                params["other_responses"] = "\n".join(data_schemas)
                response = self.request_response.exec(**params)
        return constraint
            

    def response_properties_constraints(self):
        # Implement mining constraints among response properties
        constraint = {}
        for schema_name, schema in self.schemas.items():
            flattened_schema = {
                field: values
                for field, values in flatten_json_schema(schema.to_dict()).items()
                if (
                    (schema.xrefs is None and values.get("xrefs") is None)
                    or (schema.xrefs is not None and values.get("xrefs") == schema.xrefs)
                )
            }
            # map dict to string
            flatten_texts = [f"- {k}: {ItemProperties(**v).to_human_readable(True)}" for k,v in flattened_schema.items() if v is not None]
            params = {
                "schema": schema_name,
                "attributes": "\n".join(flatten_texts)
            }
            response = self.response_constraint.exec(**params)
            constraint.update({schema_name: response.get("constraints")})
        # convert from schema constraint to operation contraint
        final_contraints = {}
        for opt in self.operations.values():
            final_contraints[opt.uuid] = {}
            successful_responses = opt.successful_responses
            if not successful_responses:
                continue
            flatten_responses = flatten_json_schema(successful_responses.to_dict())
            for schema, rules in constraint.items():
                attribute_rules = rules.keys()
                for attribute_name in attribute_rules:
                    attributes = { att: rules.get(attribute_name) for att, props in flatten_responses.items() if is_nested_path_end_with(att, attribute_name) and props.get("xrefs", None) == schema }
                    final_contraints[opt.uuid].update(attributes)
        outs = {
            "response_properties_constraints": final_contraints
        }
        with open(self.cache_file, 'w', encoding='utf-8') as file:
            json.dump(outs, file, ensure_ascii=False, indent=4) 
                    