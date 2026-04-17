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
        self.cache_dir = cache_dir
        self.logger = getLogger()
        self.operations = self.spec_parser.operations
        self.constraints = {}
        self.response_constraint = ResponseConstraints(llm=self.model)
        self.request_response_constraint = RequestResponseConstraint(llm=self.model)

    def mining(self):
        req_res_constraints = self.request_response_constraints()
        res_constraints = self.response_properties_constraints()
        self.constraints = {
            "request_response": req_res_constraints,
            "response_properties": res_constraints
        }
        constraints = {}
        for uuid, opt in self.operations.items():
            constraints[uuid] = {
               k: v for k, v in res_constraints.get(uuid, {}).items()
            }
            for req_res in req_res_constraints.get(uuid, []):
                property_name = req_res.get("property")
                for property in property_name.split(","):
                    property = property.strip()
                    if "return" not in property:
                        property = "return." + property
                    if property in constraints[uuid]:
                        constraints[uuid][property] = f"({constraints[uuid][property]}) and ({req_res.get('predicate')})"
                    else:
                        constraints[uuid][property] = req_res.get("predicate")
            
            # get all response properties constraints
        self.constraints["common"] = constraints   
        with open(self.cache_file, 'w', encoding='utf-8') as file:
            json.dump(self.constraints, file, ensure_ascii=False, indent=4)
        return self.constraints
    
    def request_response_constraints(self):
        cache_file = os.path.join(self.cache_dir, "static_constraint_miner_request_response.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as file:
                req_res_constraints = json.load(file)
            return req_res_constraints
        req_res_constraints = {}
        for opt in self.operations.values():
            successful_responses = opt.successful_responses
            if not successful_responses:
                continue
            main_xrefs = successful_responses.xrefs
            main_response = None
            if main_xrefs is not None:
                newSchema = copy.deepcopy(successful_responses)
                newSchema.xrefs = None
                cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n", "")
                cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                main_response = re.sub(r'\\+', "", cleaned_string)

            other_responses = {k: v for k, v in opt.schemas.items() if k != main_xrefs}
            for k, v in other_responses.items():
                newSchema = copy.deepcopy(v)
                newSchema.xrefs = None
                cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n", "")
                cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                cleaned_string = re.sub(r'\\+', "", cleaned_string)
                other_responses[k] = re.sub(r'\\+', "", cleaned_string)

            params_text = "\n".join(
                    [
                        f"- {k}::parameter : {v.to_human_readable()}" 
                        for k, v in opt.parameters.items() 
                    ] + [
                        f"- {k}::requestBody : {ItemProperties.from_dict(v).to_human_readable()}"
                        for k,v in opt.get_request_body().items()
                    ]
                )

            args={
                "endpoint": f"{opt.http_method.upper()} {opt.endpoint_path}",
                "summary": opt.summary or opt.description or "",
                "params": params_text,
                "main_response": f"{main_xrefs}: {main_response}",
                "other_responses": "\n".join([f"- {k}: {v}" for k, v in other_responses.items()])
            }
            response = self.request_response_constraint.exec(**args) 
            constraints = response.get("constraints", [])
            flatten_responses = flatten_json_schema(successful_responses.to_dict())
            for att, props in flatten_responses.items():
                for constraint in constraints:
                    property_name = constraint.get("property")
                    if not property_name:
                        continue
                    for property in map(str.strip, property_name.split(",")):
                        if is_nested_path_end_with(att, property):
                            req_res_constraints.setdefault(opt.uuid, []).append({
                                "property": f"return.{att}",
                                "predicate": constraint.get("predicate"),
                                "parameter": constraint.get("parameter"),
                            })

            # req_res_constraints[opt.uuid] = constraints
        
        with open(cache_file, 'w', encoding='utf-8') as file:
            json.dump(req_res_constraints, file, ensure_ascii=False, indent=4)
        return req_res_constraints
 
    def response_properties_constraints(self):
        # Implement mining constraints among response properties
        cache_file = os.path.join(self.cache_dir, "static_constraint_miner_response_properties.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as file:
                res_constraints = json.load(file)
            return res_constraints
        constraint = {}
        schemas = {k: v for opt in self.operations.values() for k, v in opt.schemas.items()}
        print(f"Total schemas to process: {len(schemas)}")
        for schema_name, schema in schemas.items():
            print(f"Processing schema: {schema_name}")
            flattened_schema = {
                field: values
                for field, values in flatten_json_schema(schema.to_dict()).items()
            }
            if len(flattened_schema) == 0:
                continue
            # map dict to string
            flatten_texts = [f"- {k}: {ItemProperties.from_dict(v).to_human_readable()}" for k,v in flattened_schema.items() if v is not None]
            params = {
                "schema": schema_name,
                "properties": "\n".join(flatten_texts)
            }
            response = self.response_constraint.exec(**params)
            constraint.update({schema_name: response})
        # convert from schema constraint to operation contraint
        final_contraints = {}
        for opt in self.operations.values():
            final_contraints[opt.uuid] = {}
            successful_responses = opt.successful_responses
            if not successful_responses:
                continue
            flatten_responses = flatten_json_schema(successful_responses.to_dict())
            for att, props in flatten_responses.items():
                for schema, rules in constraint.items():
                    if props.get("xrefs", None) == schema:
                        for attribute_name, attribute_rules in rules.items():
                            if is_nested_path_end_with(att, attribute_name):
                                final_contraints[opt.uuid]["return." + att] = attribute_rules
        
        with open(cache_file, 'w', encoding='utf-8') as file:
            json.dump(final_contraints, file, ensure_ascii=False, indent=4) 
        return final_contraints