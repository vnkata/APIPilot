import json
import os
from dataclasses import asdict, dataclass
from typing import List, Dict

from api_testing.models.specification_model import ItemProperties, OperationProperties

from api_testing.utils import to_dict_helper
import networkx as nx
import pyvis.network as net
import time
import re
from difflib import SequenceMatcher
import copy

def remove_path_variables(string):
    pattern = r'\{.*?\}'
    result = re.sub(pattern, '', string)
    return result

def preprocess_string(s):
    s = s.lower()
    s = re.sub(r"[_]", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def levenshtein_ratio(s1, s2):
    return SequenceMatcher(None, s1, s2).ratio()

@dataclass
class OperationNode(OperationProperties):
    in_degree: int = 0
    out_degree: int = 0

    def __repr__(self):
        return f"OperationNode({self.uuid})"

    def to_dict(self):
        result = {k: to_dict_helper(
            v) for k, v in self.__dict__.items() if v is not None}
        if 'parameters' in result and self.parameters:
            result['parameters'] = {k: v.to_dict()
                                    for k, v in self.parameters.items()}
        if 'request_body' in result and self.request_body:
            result['request_body'] = {
                k: v.to_dict() for k, v in self.request_body.items()}
        return result


@dataclass
class OperationEdge:
    def __init__(self, from_node, to_node, similar_parameters):
        self.from_node = from_node
        self.to_node = to_node
        self.similar_parameters = similar_parameters

    def __repr__(self):
        return f"OperationEdge({self.from_node} -> {self.to_node})"

    def to_dict(self):
        return {
            "from_node": self.from_node.uuid,
            "to_node": self.to_node.uuid,
            "similar_parameters": to_dict_helper(self.similar_parameters)
        }


@dataclass
class SimilarityValue:
    value1: str = ""
    value2: str = ""
    in_value: str = ""

    def to_dict(self):
        return {
            "value1": self.value1,
            "value2": self.value2,
            "in_value": self.in_value,
        }

# def make_humanreadable_params(params):
#     humaneadable = []
#     for p in params:
#         str = f"{p.get("")}"
#         humaneadable.append(f"{p.value1} -> {p.value2} (in {p.in_value})")
#     return s.replace("_", " ").title()
def flatten_json_schema(schema, parent_key='', sep='.', ref=""):
            flat_schema = {}
            if schema is None:
                return
            newRef = ref
            if 'properties' in schema:
                if "xrefs" in schema:
                    ref = schema.get("xrefs", "")    
                # root
                for key, value in schema['properties'].items():
                    new_key = f"{parent_key}{sep}{key}" if parent_key else key
                    if value is None:
                        continue

                    if value.get('type') == 'object' and 'properties' in value:
                        # Recursively flatten nested object
                        if "xrefs" in value:
                            newRef = value.get("xrefs", "")
                        flat_schema.update(
                            flatten_json_schema(value, new_key, sep=sep, ref=newRef))

                    elif value.get('type') == 'array':
                        items = value.get('items', {})
                        array_key = f"{new_key}"
                        # if "xrefs" in value.get("items",[]):
                        #     ref = value.get("xrefs")
                        if items.get('type') == 'object' and 'properties' in items:
                            # Flatten object inside array
                            if "xrefs" in value.get("items", {}):
                                newRef = value.get("items", {}).get("xrefs", "")
                            flat_schema.update(flatten_json_schema(
                                items, array_key, sep=sep, ref=newRef))
                        else:
                            if ref != "":
                                items["xrefs"] = ref
                            # Array of primitives
                            flat_schema[array_key] = items
                    else:
                        # Primitive field
                        if ref != "":
                            value["xrefs"] = ref
                        flat_schema[new_key] = value
            elif schema.get('type') == 'array':
                # nested
                items = schema.get('items', {})
                newRef = ref
                if "xrefs" in items:
                    newRef = items.get("xrefs", "")
                flat_schema.update(
                    flatten_json_schema(items, parent_key, sep=sep, ref=newRef))
            return flat_schema

@dataclass
class OperationGraph:
    def __init__(self, spec_parser=None, model=None, embedding_model=None, threshold=0.6, cache_dir=None):
        self.spec_parser = spec_parser
        self.embedding_model = embedding_model
        self.model = model  # llm model

        self.nodes = {}
        self.edges = []
        self.threshold = threshold

        self.cache_file = os.path.join(
            cache_dir, "semantic_property_dependency_graph.json")
        # self.create_graph()
        from api_testing.log import logger
        self.logger = logger
        self.load_or_initialize_graph()

    def add_node(self, operation):
        data = asdict(operation)
        self.nodes[operation.uuid] = OperationNode(
            **{k: data[k] for k in OperationProperties.__dataclass_fields__})

    def add_edge(self, from_node, to_node, parameters):
        if len(parameters) == 0:
            return
        source_node = self.nodes.get(from_node, None)
        destination_node = self.nodes.get(to_node, None)
        edge = OperationEdge(
            from_node=source_node, to_node=destination_node, similar_parameters=parameters)
        self.edges.append(edge)

    def load_or_initialize_graph(self):
        # Check if the cache file exists
        if False and os.path.exists(self.cache_file):
            print(f"Loading graph from cache: {self.cache_file}")
            with open(self.cache_file, "r") as file:
                data = json.load(file)
                # Load nodes and edges from the cache file (implementation depends on your data structure)
                #
                operations = self.spec_parser.operations
                for operation_properties in data.get("nodes", []):
                    self.add_node(operations[operation_properties])
                for edge in data.get("edges", []):
                    similarities = [
                        SimilarityValue(
                            value1=item.get("value1"),
                            value2=item.get("value2"),
                            in_value=item.get("in_value"),
                        )
                        for item in edge['similar_parameters'] if item.get("check") is None or item.get("check") == True
                    ]
                    if len(similarities) > 0:
                        self.add_edge(
                            edge['from_node'],
                            edge['to_node'],
                            similarities
                        )

        else:
            print("Cache file not found. Initializing graph...")
            self.create_graph()
            self.save_graph_to_cache()
    # def save_graph_to_cache(self, edges):
    #     # Save the graph to the cache file
    #     data = {
    #         "nodes": [to_dict_helper(node) for node in self.nodes],
    #         "edges": [to_dict_helper(edge) for edge in edges],
    #     }
    #     # print(data)
    #     with open(self.cache_file, "w") as file:
    #         json.dump(data, file, indent=4)
    #     print(f"Graph saved to cache: {self.cache_file}")

    def save_graph_to_cache(self):
        # Save the graph to the cache file
        data = {
            "nodes": [to_dict_helper(node) for node in self.nodes],
            "edges": [to_dict_helper(edge) for edge in self.edges],
        }
        # print(data)
        with open(self.cache_file, "w") as file:
            json.dump(data, file, indent=4)
        print(f"Graph saved to cache: {self.cache_file}")

    # def heuristic_similarities(self, u: OperationProperties, v: OperationProperties):
    #     #  has connection u -> v
    #     self.logger.debug("HEURISTIC CHECK BETWEEN: " + u.http_method.upper() + " " +  u.endpoint_path + " TO " +  v.http_method.upper()+ " "+ v.endpoint_path)
    #     similar_parameters = []
    #     if v.http_method.lower() == "delete":  # delete operation is end of flow
    #         return similar_parameters
    #     if u.endpoint_path.startswith(v.endpoint_path):
    #         if ["post", "get", "put", "delete"].index(v.http_method.lower()) > ["post", "get", "put", "delete"].index(u.http_method.lower()):
    #             return similar_parameters
    #         parameters = v.get_parameters(required=True) 
    #         dependent_response = u.get_responses()

    #         for param in parameters: 
    #             for response in dependent_response:
    #                 if param.get("name") == response.get("name"):
    #                     similar_parameters.append(SimilarityValue(
    #                         value1=response.get("name"), 
    #                         value2=param.get("name"), 
    #                         in_value="response to parameter via heuristic"
    #                     ))
    #     return similar_parameters
    
    
    # def gpt_similarities(self, u: OperationProperties,  operations: List[OperationProperties]):
    #     # GPT similarity check has connection u -> v
    #     self.logger.debug("GPT CHECK BETWEEN: "+ u.http_method.upper()+ " "+  u.endpoint_path)
    #     similar_parameters = []
    #     if u.http_method.lower() == "delete":  # delete operation is end of flow
    #         return similar_parameters
    #     operation_parameters = u.parameters

    #     schemas = { opt.uuid: opt.successful_responses for opt in operations }
    #     # mapping to schemas name and operations_id
    #     schema_map = {}
    #     schema_string = []
    #     for op_id, schema in schemas.items():
    #         if schema is None:
    #             continue
    #         # flattened_schema = flatten_json_schema(schema.to_dict())
    #         cleaned_string = schema.to_human_readable().replace('\\n', '').replace("\n","")
    #         cleaned_string = re.sub(r'\\+', "", cleaned_string)
    #         cleaned_string = re.sub(r'\s+', ' ', cleaned_string)
    #         cleaned_string = cleaned_string[cleaned_string.find('{'):]
    #         schema_map[schema.xrefs] = {
    #             "operation_id": op_id,
    #             "schema": schema,
    #             "human_readable": cleaned_string
    #         }
    #         schema_string.append(f"- Schema of {schema.xrefs}: {cleaned_string}")
    #     params = {
    #         "endpoint": f"{u.http_method.upper()} {u.endpoint_path}",
    #         "summary": u.summary + " " + (u.description if u.description else ""),
    #         "specific_endpoint_params": "\n".join([ f"- {k} : {v.to_human_readable()}" for k,v in operation_parameters.items() if v.schema.type in ["string", "integer"]]),
    #         "data_schemas":  "\n".join(schema_string)
    #     }
    #     PROMPT = """
    #     Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.
    #     Please review the following details for the endpoint and its associated parameters to identify the corresponding schemas needed for data retrieval:
    #     Endpoint: {endpoint}
    #     Description: {summary}
    #     Specific Endpoint Parameters:
    #     {specific_endpoint_params}
    #     Additionally, you are provided with a list of all data schemas and their attributes as described in the Swagger Specification of the API application:
    #     {data_schemas}
    #     Follow these steps below to complete your task:
    #     STEP 1: Review the provided API endpoint and describe each parameter briefly based on its function or purpose.
    #     STEP 2: Review the provided API endpoint along with its parameters and brief descriptions from STEP 1 to identify and select only the parameters that function as identifying, contextual, or foreign key parameters. Exclude generic filtering parameters
    #     STEP 3: Review the data schemas and their attributes to locate potential matches for each endpoint parameter key from STEP 2. Then, map each parameter to the schema attribute(s) that can best provide the required information.
    #     FINAL OUTPUT:
    #     The response is in the format below, no explanation is needed:
    #     ```json 
    #     {{
    #         "schema_1": {{
    #             "parameter_name_1": "attribute_name_1, attribute_name_2", 
    #             "parameter_name_2": "attribute_name_3, attribute_name_4"
    #         }}
    #     }}```
    #     """  
    #     self.logger.debug("GPT PROMPT" + PROMPT.format(**params))
    #     # print( PROMPT.format(**params))
    #     str = "response to parameter via GPT"
    #     # if u.operation_id == v.operation_id:
    #     #     str =  "response to parameter via GPT same operation"
    #     for i in range(3):
    #         try:
    #             response, _ = self.model.generate(
    #                         PROMPT.format(**params))
    #             self.logger.debug("GPT RESPONSE" + response)
    #             start, end  = -1, -1
    #             # start = response.find('json') 
    #             start = response.find('{') # vị trí dấu { đầu tiên 
    #             end = response.rfind('}') # vị trí ``` cuối cùng
    #             if start != -1 and end != -1:
    #                 json_str = response[start:end+1].strip()   
    #                 data = json.loads(json_str)
    #                 for schema_name, mappings in data.items():
    #                     if schema_name in schema_map:
    #                         similar_parameters = []
    #                         for param_name, attr_names in mappings.items():
    #                             attr_list = [attr.strip() for attr in attr_names.split(",")]
    #                             for attr_name in attr_list:
    #                                 similar_parameters.append(SimilarityValue(
    #                                     value1=param_name,
    #                                     value2=attr_name,
    #                                     in_value=str
    #                                 ))
    #                         # mapping
    #                         op_id = schema_map[schema_name]["operation_id"]
    #                         self.add_edge(
    #                             op_id, u.uuid, similar_parameters)
    #             # response_lines = response.split("\n")
    #             # for line in response_lines:
    #             #     if ":" in line:
    #             #         param_name, attr_names = line.split(":", 1)
    #             #         param_name = param_name.strip()
    #             #         attr_names = [attr.strip() for attr in attr_names.split(",")]
    #             #         for attr_name in attr_names:
    #             #             similar_parameters.append(SimilarityValue(
    #             #                 value1=attr_name,
    #             #                 value2=param_name,
    #             #                 in_value=str
    #             #             ))
    #             break
    #         except Exception as e:
    #             print("Error during GPT similarity check: ", e)
    #             time.sleep(10)  
    #     return similar_parameters
    
    # def gpt_similarities(self, u: OperationProperties,  v: OperationProperties):
    #     # GPT similarity check has connection u -> v
    #     self.logger.debug("GPT CHECK BETWEEN: "+ u.http_method.upper()+ " "+  u.endpoint_path + " TO "+ v.http_method.upper()+ " "+ v.endpoint_path)
    #     similar_parameters = []
    #     if v.http_method.lower() == "delete":  # delete operation is end of flow
    #         return similar_parameters
    #     operation_parameters = v.parameters
    #     dependent_operation_responses = u.successful_responses # get all parameters
    #     #
    #     if not dependent_operation_responses:  
    #         return similar_parameters   
    #     data_schemas = dependent_operation_responses.to_human_readable() if dependent_operation_responses else ""
    #     cleaned_string = data_schemas.replace('\\n', '\n')
    #     cleaned_string = re.sub(r'\\+', "", cleaned_string)
    #     params = {
    #         "endpoint": f"{v.http_method.upper()} {v.endpoint_path}",
    #         "summary": v.summary + " " + (v.description if v.description else ""),
    #         "specific_endpoint_params": "\n".join([ f"- {k} : {v.to_human_readable()}" for k,v in operation_parameters.items()]),
    #         "data_schemas":  cleaned_string
    #     }
    #     PROMPT = """
    #     Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.
    #     Please review the following details for the endpoint and its associated parameters to identify the corresponding schemas needed for data retrieval:
    #     Endpoint: {endpoint}
    #     Description: {summary}
    #     Specific Endpoint Parameters:
    #     {specific_endpoint_params}
    #     Additionally, you are provided with a data schemas and their attributes as described in the Swagger Specification of the API application:
    #     {data_schemas}
    #     Follow these steps below to complete your task:
    #     STEP 1: Review the provided API endpoint and describe each parameter briefly based on its function or purpose.
    #     STEP 2: Review the provided API endpoint along with its parameters and brief descriptions from STEP 1 to identify and select only the parameters that function as identifying, contextual, or foreign key parameters. Exclude generic filtering parameters
    #     STEP 3: Review the data schemas and their attributes to locate potential matches for each endpoint parameter key from STEP 2. Then, map each parameter to the schema attribute(s) that can best provide the required information.
    #     FINAL OUTPUT:
    #     The response is in the format below, no explanation is needed:
    #     parameter_name_1: attribute_name_1, attribute_name_2,..

    #     """  
    #     self.logger.debug("GPT PROMPT for similarity check for " + v.http_method.upper() + " " +  v.endpoint_path + " : \n" + PROMPT.format(**params))
    #     # print( PROMPT.format(**params))
    #     str = "response to parameter via GPT"
    #     if u.operation_id == v.operation_id:
    #         str =  "response to parameter via GPT same operation"
    #     for i in range(3):
    #         try:
    #             response, _ = self.model.generate(
    #                         PROMPT.format(**params))
                
    #             response_lines = response.split("\n")
    #             for line in response_lines:
    #                 if ":" in line:
    #                     param_name, attr_names = line.split(":", 1)
    #                     param_name = param_name.strip()
    #                     attr_names = [attr.strip() for attr in attr_names.split(",")]
    #                     for attr_name in attr_names:
    #                         similar_parameters.append(SimilarityValue(
    #                             value1=attr_name,
    #                             value2=param_name,
    #                             in_value=str
    #                         ))
    #             break
    #         except Exception as e:
    #             print("Error during GPT similarity check: ", e)
    #             time.sleep(10)  
    #     return similar_parameters
    
    # def rank_operations_by_endpoint_similarity(self, operation: OperationProperties, operations: List[OperationProperties]): # type: ignore
    #     # 
    #     endpoint = operation.endpoint_path
    #     paths = [ opt.endpoint_path for opt in operations]
    #     path_tree  = os.path.commonprefix(paths) 
    #     endpoint = endpoint.replace(path_tree, "") # only get relative path
    #     endpoint = endpoint.lower()
    #     endpoint = re.sub(r'\{.*?\}', '', endpoint)
    #     endpoint = re.sub(r"[_]", " ", endpoint)
    #     endpoint = re.sub(r"[^\w\s]", "", endpoint) 
    #     endpoint = re.sub(r"\s+", " ", endpoint).strip()
    #     similarity_scores = [0] * len(operations)
    #     # mapping opperations to schemas
    #     schemas = [  opt.successful_responses for opt in operations ]
    #     operations_list = [ opt.uuid for opt in operations ]
    #     for idx, schema in enumerate(schemas):  
    #         if schema is None:
    #             continue
    #         schemas[idx] = flatten_json_schema(schema.to_dict())


    #     for params in operation.parameters.values():
    #         base_str = f"{params.name}_{endpoint}"
    #         for schema_i, schema in enumerate(schemas):
    #             # schema_name = schema.lower()
    #             # schema_name = ""
    #             if schema is not None:
    #                 similarity_scores[schema_i] += max([levenshtein_ratio(base_str, f"{field.split(".")[-1]}_{values.get("xrefs","").lower()}") for field, values in schema.items()]+[0])
       
    #     sort_object = sorted(zip(similarity_scores, operations_list), reverse=True)
    #     _, sorted_schemas = zip(*sort_object)
    #     return list(sorted_schemas)

    #         # for i, op in enumerate(operaions):
    #         #     dep_endpoint = op.endpoint_path
    #         #     dep_endpoint = dep_endpoint.replace(path_tree, "") # only get relative path
    #         #     dep_endpoint = dep_endpoint.lower()
    #         #     dep_endpoint = re.sub(r'\{.*?\}', '', dep_endpoint)
    #         #     dep_endpoint = re.sub(r"[_]", " ", dep_endpoint)
    #         #     dep_endpoint = re.sub(r"[^\w\s]", "", dep_endpoint)
    #         #     dep_endpoint = re.sub(r"\s+", " ", dep_endpoint).strip()
    #         #     similarity_scores[i] += levenshtein_ratio(
    #         #         base_str, f"{params.name}_{dep_endpoint}")
            

    #     # endpoint = remove_path_variables(operation.endpoint_path)
    #     # endpoint = preprocess_string(endpoint)
    #     # similarity_scores = []
    #     # for op_id, op_properties in operaions.items():
    #     #     dep_endpoint = remove_path_variables(op_properties.endpoint_path)
    #     #     dep_endpoint = preprocess_string(dep_endpoint)
    #     #     similarity = levenshtein_ratio(endpoint, dep_endpoint)
    #     #     similarity_scores.append((similarity, op_id, op_properties))
    #     # similarity_scores.sort(reverse=True, key=lambda x: x[0])
    #     # ranked_operations = [(op_id, op_properties)
    #     #                      for _, op_id, op_properties in similarity_scores]
    #     # return ranked_operations


    def heuristic_similarities(self, operations: List[OperationProperties]):
        edges = []
        for op_properties in operations.values():
            if len(op_properties.parameters) == 0 and len(op_properties.request_body) == 0:
                continue
            for dep_op_properties in operations.values():
                if  dep_op_properties.successful_responses is None:
                    continue
                similar_parameters = []
                #  has connection u -> v
                self.logger.debug("HEURISTIC CHECK BETWEEN: " + dep_op_properties.http_method.upper() + " " +  dep_op_properties.endpoint_path + " TO " +  op_properties.http_method.upper()+ " "+ op_properties.endpoint_path)
                if dep_op_properties.http_method.lower() == "delete":  # delete operation is end of flow
                    continue
                if op_properties.endpoint_path.startswith(dep_op_properties.endpoint_path):
                    if ["post", "get", "put", "delete"].index(op_properties.http_method.lower()) > ["post", "get", "put", "delete"].index(dep_op_properties.http_method.lower()):
                        continue
                    parameters = op_properties.get_parameters(required=True) # heuristic on required parameters 
                    dependent_response = dep_op_properties.get_responses()
                    for param in parameters: 
                        for response in dependent_response:
                            if param.get("name") == response.get("name"):
                                similar_parameters.append(SimilarityValue(
                                    value1=response.get("name"), 
                                    value2=param.get("name"), 
                                    in_value="response to parameter via heuristic"
                                ))
                # temporal edges
                #edge from dep_op to op
                if len(similar_parameters) > 0:
                    edges.append(OperationEdge(dep_op_properties, op_properties, similar_parameters))
        return edges
    
    def get_best_mathching_schema(self, operation: OperationProperties, schemas: Dict[str, ItemProperties], top_k: int =3):
        endpoint = operation.endpoint_path

        endpoint = endpoint.replace(self.path_tree, "") # only get relative path
        endpoint = endpoint.lower()
        endpoint = re.sub(r'\{.*?\}', '', endpoint)
        endpoint = re.sub(r"[_]", " ", endpoint)
        endpoint = re.sub(r"[^\w\s]", "", endpoint) 
        endpoint = re.sub(r"\s+", " ", endpoint).strip()
        similarity_scores = [0] * len(schemas)
        for params in operation.parameters.values():
            base_str = f"{params.name}_{endpoint}".lower()
            for schema_i, (schema_name, schema) in enumerate(schemas.items()):
                # schema_name = schema.lower()
                # schema_name = ""
                if schema is not None:
                    flattened_schema = flatten_json_schema(schema.to_dict())
                    similarity_scores[schema_i] += max([levenshtein_ratio(base_str, f"{field.split('.')[-1]}_{values.get('xrefs','').lower()}") for field, values in flattened_schema.items()]+[0])
        
        sort_object = sorted(zip(similarity_scores, schemas.keys()), reverse=True)
        _, sorted_schemas = zip(*sort_object)
        # 
        # return list(sorted_schemas[:top_k])
        return list(sorted_schemas)
    
    def get_subschemas_of_schema(self, schema: ItemProperties):
        relevant_schemas = {}

        def get_schema_recursive(item_properties: ItemProperties):
            if item_properties.xrefs and item_properties.type in ['object', 'array']:
                schema_name = item_properties.xrefs
                if schema_name not in relevant_schemas:
                    relevant_schemas[schema_name] = item_properties

            if item_properties.items:
                get_schema_recursive(item_properties.items)
            if item_properties.properties:
                for prop in item_properties.properties.values():
                    get_schema_recursive(prop)

        get_schema_recursive(schema)
        return relevant_schemas
    
    def gpt_similarities(self, operations: List[OperationProperties]):
        
        edges = []
        schemas = {k: v for opt in operations.values() for k, v in opt.schemas.items()}
        for operation in operations.values(): 
            #par
            if len(operation.parameters) == 0 and len(operation.request_body) == 0:
                print(
                    f"SKIP NODE {operation.http_method.upper()} {operation.endpoint_path} DUE TO NO PARAMETERS AND REQUEST BODY")
                continue
 
            params = {
                "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
                "summary": ((operation.summary or "") + " " + (operation.description or "")).strip(),
                "specific_endpoint_params": "\n".join([ f"- {k} : {v.to_human_readable()}" for k,v in operation.parameters.items() if v.schema.type not in ("boolean")]), # experiences filter params
            }
            relavant_schemas = self.get_best_mathching_schema(operation, schemas, top_k = 7)
            self.logger.debug("RELEVANT SCHEMAS FOR OPERATION " + operation.uuid + " : " + ", ".join(relavant_schemas))
            # only consider top k schemas
            # get extension relavant schemas: example: User schema -> Profile schema
            relavant_schemas_dict = { schema_name: schemas.get(schema_name) for schema_name in relavant_schemas}
            for schema_name in relavant_schemas:
                schema = schemas.get(schema_name)
                if schema is not None:
                    subschemas = self.get_subschemas_of_schema(schema)
                    relavant_schemas_dict.update(subschemas)
            # print
            data_schemas = []
            for schema_name, schema in relavant_schemas_dict.items():
                if schema is not None:
                    newSchema = copy.deepcopy(schema)
                    newSchema.xrefs = None
                    cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n","")
                    cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                    cleaned_string = re.sub(r'\\+', "", cleaned_string)
                    data_schemas.append(f"- {schema_name}: {cleaned_string}")
            params["data_schemas"] = "\n".join(data_schemas)
            
            PROMPT = """
                Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.
                Please review the following details for the endpoint and its associated parameters to identify the corresponding schemas needed for data retrieval:
                Endpoint: {endpoint}
                Description: {summary}
                Specific Endpoint Parameters:
                {specific_endpoint_params}
                Additionally, you are provided with a list of all data schemas and their attributes as described in the Swagger Specification of the API application:
                {data_schemas}
                Follow these steps below to complete your task:
                **STEP 1**: Review the provided API endpoint and describe each parameter briefly based on its function or purpose.
                **STEP 2**: Review the provided API endpoint along with its parameters and brief descriptions from STEP 1 to identify and select only the parameters that function as identifying, contextual, or foreign key parameters. Exclude generic filtering parameters
                **STEP 3**: Review the data schemas and their attributes to locate potential matches for each endpoint parameter key from **STEP 2** and verify whether these parameters serve as identifiers or foreign keys. Then, map each parameter to the schema attribute(s) that can best provide the required information.
                FINAL OUTPUT:
                The response is in the format below, no explanation is needed:
                ```json 
                {{
                    "schema_1": {{
                        "parameter_name_1": "attribute_name_1, attribute_name_2", 
                        "parameter_name_2": "attribute_name_3, attribute_name_4"
                    }}
                }}```
            """  
            
            # PROMPT = """
            #     Your task is to analyze a specific endpoint within an API application, as defined in its Swagger Specification, and determine the necessary data schemas and matching keys required to obtain information pertinent to the endpoint's parameters.
            #     Please review the following details for the endpoint and its associated parameters to identify the corresponding schemas needed for data retrieval:
            #     Endpoint: {endpoint}
            #     Description: {summary}
            #     Specific Endpoint Parameters:
            #     {specific_endpoint_params}
            #     Additionally, you are provided with a list of all data schemas and their attributes as described in the Swagger Specification of the API application:
            #     {data_schemas}
            #     Follow these steps below to complete your task:
            #     **STEP 1**: Review the provided API endpoint and describe each parameter briefly based on its function or purpose.
            #     **STEP 2**: Review the provided API endpoint along with its parameters and brief descriptions from STEP 1 to identify and select only the parameters that function as identifying, contextual, or foreign key parameters. Exclude generic filtering parameters. Perform the same process for the schema attributes as well.
            #     **STEP 3**: Review the data schemas and their attributes to locate potential matches for each endpoint parameter key from **STEP 2** and verify whether these parameters serve as identifiers or foreign keys. Then, map each parameter to the schema attribute(s) from **STEP 2** that can best provide the required information.
            #     FINAL OUTPUT:
            #     The response is in the format below, no explanation is needed:
            #     ```json 
            #     {{
            #         "schema_1": {{
            #             "parameter_name_1": "attribute_name_1, attribute_name_2", 
            #             "parameter_name_2": "attribute_name_3, attribute_name_4"
            #         }}
            #     }}```
            # """  
            self.logger.debug("GPT PROMPT" + PROMPT.format(**params))
            # print( PROMPT.format(**params))
            str = "response to parameter via GPT"
            # if u.operation_id == v.operation_id:
            #     str =  "response to parameter via GPT same operation"
            for _ in range(3):
                try:
                    response, _ = self.model.generate(
                                PROMPT.format(**params))
                    self.logger.debug("GPT RESPONSE" + response)
                    start, end  = -1, -1
                    # start = response.find('json') 
                    start = response.find('{') # vị trí dấu { đầu tiên 
                    end = response.rfind('}') # vị trí ``` cuối cùng
                    if start != -1 and end != -1:
                        json_str = response[start:end+1].strip()   
                        data = json.loads(json_str) # response mapping
                        for schema_name, mappings in data.items():
                            for dep_operation in operations.values():
                                if schema_name in dep_operation.schemas:
                                    self.logger.debug("MAPPING SCHEMA " + schema_name + " TO OPERATION " + dep_operation.uuid)
                                    # flatten schemas: 
                                    flattened_schema = flatten_json_schema(dep_operation.successful_responses.to_dict())
                                    similar_parameters = []
                                    for param_name, attr_names in mappings.items():
                                        attr_list = [attr.strip() for attr in attr_names.split(",")]
                                        
                                        for attr_name in attr_list:
                                            # mapping attributes to real attributes path in schema
                                            # 
                                            attributes = []
                                            for field, values in flattened_schema.items():
                                                if field.endswith(attr_name) and schema_name == values.get("xrefs", ""):
                                                    attributes.append(field)

                                            self.logger.debug("ATTRIBUTES FOUND FOR " + attr_name + " : " + ", ".join(attributes))
                                            for attribute in attributes:        
                                                similar_parameters.append(SimilarityValue(
                                                    value1=attribute,
                                                    value2=param_name,
                                                    in_value=str
                                                ))
                                    # mapping
                                    edges.append(OperationEdge(
                                        from_node=dep_operation,
                                        to_node=operation,
                                        similar_parameters=similar_parameters
                                    ))
                    break
                except Exception as e:
                    print("Error during GPT similarity check: ", e)
                    time.sleep(10)
        return edges
    
                    

        #  has connection u -> v
        # self.logger.debug("HEURISTIC CHECK BETWEEN: " + u.http_method.upper() + " " +  u.endpoint_path + " TO " +  v.http_method.upper()+ " "+ v.endpoint_path)
        # similar_parameters = []
        # if v.http_method.lower() == "delete":  # delete operation is end of flow
        #     return similar_parameters
        # if u.endpoint_path.startswith(v.endpoint_path):
        #     if ["post", "get", "put", "delete"].index(v.http_method.lower()) > ["post", "get", "put", "delete"].index(u.http_method.lower()):
        #         return similar_parameters
        #     parameters = v.get_parameters(required=True) 
        #     dependent_response = u.get_responses()

        #     for param in parameters: 
        #         for response in dependent_response:
        #             if param.get("name") == response.get("name"):
        #                 similar_parameters.append(SimilarityValue(
        #                     value1=response.get("name"), 
        #                     value2=param.get("name"), 
        #                     in_value="response to parameter via heuristic"
        #                 ))
        # return similar_parameters
    def deduplicate_similarity_values(self, similarity_list: List[SimilarityValue]) -> List[SimilarityValue]:
        """
        Removes duplicate SimilarityValue objects from a list based on the
        unique combination of (value1, value2).
        """
        unique_keys = {}
        # deduplicated_list = []

        for item in similarity_list:
            key = (item.value1, item.value2)
            if key not in unique_keys:
                unique_keys[key] = item
                # deduplicated_list.append(item)
        return list(unique_keys.values())

    def merge_operation_edges(self, heuristic_edges, gpt_edges):
        """
        Merges two lists of OperationEdge objects based on their (from_node, to_node) key.
        If a key exists in both, it combines the 'similar_parameters' lists.
        """
        merged_edges = {}

        # 1. Process heuristic_edges
        for edge in heuristic_edges:
            # Create the key from the nodes
            key = (edge.from_node.uuid, edge.to_node.uuid)
            merged_edges[key] = OperationEdge(
                edge.from_node, edge.to_node, list(edge.similar_parameters) # Use a copy/new list
            )

        # 2. Process gpt_edges and merge
        for edge in gpt_edges:
            key = (edge.from_node.uuid, edge.to_node.uuid)

            if key in merged_edges:
                # Key exists: Merge the similar_parameters (e.g., extend the list)
                existing_edge = merged_edges[key]
                existing_edge.similar_parameters.extend(edge.similar_parameters)
            else:
                # Key does not exist: Add the new edge
                merged_edges[key] = OperationEdge(
                    edge.from_node, edge.to_node, list(edge.similar_parameters)
                )
        # edges = list(merged_edges.values())
        # 2. Iterate through all merged edges and deduplicate their parameters
        final_edges = []
        for edge in merged_edges.values():
            # Apply the deduplication logic to the combined list of parameters
            edge.similar_parameters = self.deduplicate_similarity_values(edge.similar_parameters)
            final_edges.append(edge)

        return final_edges
                
    def determine_dependencies(self, operations: Dict[str, OperationProperties]):
        paths = [ opt.endpoint_path for opt in operations.values()]
        self.path_tree  = os.path.commonprefix(paths) 
        heuristic_edges = self.heuristic_similarities(operations)
        gpt_edges = self.gpt_similarities(operations)
        # merge duplicate edges
        print(f"HEURISTIC EDGES: {len(heuristic_edges)}")
        print(f"GPT EDGES: {len(gpt_edges)}")
        with open(self.cache_file.replace("semantic_property_dependency_graph", "heuristic_edges"), "w") as f:
            json.dump([to_dict_helper(edge) for edge in heuristic_edges], f, indent=4)
        with open(self.cache_file.replace("semantic_property_dependency_graph", "gpt_edges"), "w") as f:
            json.dump([to_dict_helper(edge) for edge in gpt_edges], f, indent=4)
            
        edges = self.merge_operation_edges(heuristic_edges, gpt_edges)
        self.edges = edges
        
        # group edges

        # for op_id, op_properties in operations.items():
        #     print(
        #         f"PROCESS NODE {op_properties.http_method.upper()} {op_properties.endpoint_path}")
        #     # 
        #     if len(op_properties.parameters) == 0 and len(op_properties.request_body) == 0:
        #         print(
        #             f"SKIP NODE {op_properties.http_method.upper()} {op_properties.endpoint_path} DUE TO NO PARAMETERS AND REQUEST BODY")
        #         continue
        #     # reranking endpoints related to current operation
        #     # ranked_operations = self.rank_operations_by_endpoint_similarity(op_properties, operations.values())
        #     # print(ranked_operations)
        #     # only get relative path
        #     # gpt
        #     gpt_similarities = self.gpt_similarities(op_properties, operations.values())
        #     # # self.add_edge(
        #     # #         dep_op_id,op_id, gpt_similarities)

        #     for dep_op_id, dep_op_properties in operations.items():
        #         # ignore if not have response 
        #         successful_responses = dep_op_properties.successful_responses
        #         if successful_responses is None:
        #             print(
        #             f" SKIP DEPENDENCY NODE {dep_op_properties.http_method.upper()} {dep_op_properties.endpoint_path} DUE TO NO RESPONSES OR SAME NODE")
        #             continue
        #         heuristic_similarities = self.heuristic_similarities(
        #             dep_op_properties, op_properties )
        #         self.add_edge(
        #             dep_op_id, op_id, heuristic_similarities)
                # GPT inferences

            #         # gpt
            #     # GPT Embedding
                
            #     # GPT Edge
                # if has_heuristic_connect(operation_properties, dependent_operation_properties)
                # parameter_similarities: List[SimilarityValue] = self.compare_similarities(
                #     operation_properties, dependent_operation_properties)
                # #  LLM check
                # self.add_edg               e(
                #     operation_id, dependent_operation_id, parameter_similarities)

            # if op_properties.parameters.length == 0 or op_properties.request_body.length == 0:
            #     print(
            #         f"SKIP NODE {op_properties.http_method.upper()} {op_properties.endpoint_path} DUE TO NO PARAMETERS")
            #     continue
            # 
        # normalize edge weights or other post-processing if needed
        # edges = self.edges
        # dicts_edges =  {}
        # for edge in edges:
        #     key = f"{edge.from_node.uuid}--{edge.to_node.uuid}"
        #     if key not in dicts_edges:
        #         dicts_edges[key] = edge
        #     else:
        #         dicts_edges[key].similar_parameters.extend(edge.similar_parameters)
        
    def create_graph(self):
        operations: Dict[str,
                         OperationProperties] = self.spec_parser.operations
        
        for operation in operations.values():
            self.add_node(operation)
        self.determine_dependencies(operations)

    def plot_graph(self):
        G = nx.DiGraph(directed=True)
        ODG_pyvis = net.Network(height="100vh", width="100vw", bgcolor="white",
                                font_color="black", notebook=True, directed=True, neighborhood_highlight=True)
        ODG_pyvis.barnes_hut(gravity=-8000, central_gravity=1.5,
                             spring_length=200, spring_strength=0.05)

        ODG_pyvis_opt = net.Network(height="100vh", width="100vw", bgcolor="white",
                                font_color="black", notebook=True, directed=True, neighborhood_highlight=True)
        ODG_pyvis_opt.barnes_hut(gravity=-8000, central_gravity=1.5,
                             spring_length=200, spring_strength=0.05)
        
        for operation_id, operation_node in self.nodes.items():
            G.add_node(operation_id)
            ODG_pyvis.add_node(
                operation_id, label=operation_id, title=operation_id)
            ODG_pyvis_opt.add_node(
                operation_id, label=operation_id, title=operation_id)
        for edge in self.edges:
            G.add_edge(edge.from_node.uuid, edge.to_node.uuid, capacity=', '.join(list(set([f"{similar.value1} -> {similar.value2}" for similar in edge.similar_parameters]))))
            # if edges
            # ODG_pyvis.add_edge(edge.from_node.uuid, edge.to_node.uuid, title=', '.join(list(set(
            #         [f"{similar.value1} -> {similar.value2}" for similar in edge.similar_parameters]))))
                
            required_similar_parameters = [ similar for similar in edge.similar_parameters if similar.value2 in edge.to_node.required_parameters]
            if len(required_similar_parameters):
                ODG_pyvis.add_edge(edge.from_node.uuid, edge.to_node.uuid, title=', '.join(list(set(
                    [f"{similar.value1} -> {similar.value2}" for similar in required_similar_parameters]))))
            optional_similar_parameters = [ similar for similar in edge.similar_parameters if similar.value2 in edge.to_node.optional_parameters]
            if len(optional_similar_parameters):
                ODG_pyvis_opt.add_edge(edge.from_node.uuid, edge.to_node.uuid, title=', '.join(list(set(
                    [f"{similar.value1} -> {similar.value2}" for similar in optional_similar_parameters]))))

        nx.write_graphml(G, self.cache_file.replace("json", "graphml"))
        ODG_pyvis.show(self.cache_file.replace("json", "html"))
        ODG_pyvis_opt.show(self.cache_file.replace("json", "optional.html"))

        # add 2 graphs

    def print_graph(self):
        for operation_id, operation_node in self.nodes.items():
            print("=====================================")
            print(f"Operation: {operation_id}")
            for edge in filter(lambda x: x.from_node.uuid == operation_id, self.edges):
                print(
                    f"Edge: {edge.from_node.uuid} -> {edge.to_node.uuid} with parameters: {edge.similar_parameters}")


    # def get_best_mathching_schema(self, operation):
    #     if "parameters" not in self.simplified_swagger[operation]:
    #         return []

    #     similarity_score_array = [0]*len(self.simplified_schemas)
        
    #     endpoint = "-".join(operation.split('-')[1:])
    #     endpoint = endpoint.replace(self.path_common_prefix, "")
    #     endpoint = remove_path_variables(endpoint)
    #     endpoint = preprocess_string(endpoint)
        
    #     schema_list = list(self.simplified_schemas.keys())
    #     for p in self.simplified_swagger[operation]["parameters"]:
    #         base_str = f"{p}_{endpoint}".lower()
    #         for schema_i, schema in enumerate(schema_list):
    #             similarity_score_array[schema_i] += max([levenshtein_ratio(base_str, f"{field.split(".")[-1]}_{values.get("xrefs").lower()}") for field, values in schema.items()]+[0])
        
    #     sort_object = sorted(zip(similarity_score_array, schema_list), reverse=True)
    #     _, sorted_schemas = zip(*sort_object)
    #     return list(sorted_schemas)
    