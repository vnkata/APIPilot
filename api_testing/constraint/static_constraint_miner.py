import json
import os
from api_testing.models.specification_model import ItemProperties
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
        self.logger = getLogger()
        # self.max_load = 
        self.operations = self.spec_parser.operations
        self.schemas = {k: v for opt in self.operations.values() for k, v in opt.schemas.items()}
        self.response_constraint = ResponseConstraints(llm=self.model)

    def reuest_response_constraints(self):
        # Implement mining constraints between request and response

        pass
      
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
                    