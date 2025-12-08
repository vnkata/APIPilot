import json
import os
from dataclasses import asdict, dataclass
from typing import List, Dict

from api_testing.models.specification_model import ItemProperties, OperationProperties

from api_testing.prompts import OpSchemaDeps
from api_testing.utils import to_dict_helper
import networkx as nx
import pyvis.network as net
import time
import re
from difflib import SequenceMatcher
import copy
from api_testing.log import getLogger


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
        self.logger = getLogger()

        self.op_schema_deps = OpSchemaDeps(self.model)
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
        results = list(sorted_schemas[:top_k]) 
        results = { schema_name: schemas.get(schema_name) for schema_name in results}
        for schema_name in results:
                schema = schemas.get(schema_name)
                if schema is not None:
                    subschemas = self.get_subschemas_of_schema(schema)
                    results.update(subschemas)

        return results
        # return list(sorted_schemas)
    
    def get_subschemas_of_schema(self, schema: ItemProperties):
        relevant_schemas = {}

        def get_schema_recursive(item_properties: ItemProperties):
            if item_properties is None:
                return
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
    
    def gpt_similarities(self, operations: List[OperationProperties], schemas: Dict[str,ItemProperties]):
        
        edges = []
        
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
            # only consider top k schemas
            # get extension relavant schemas: example: User schema -> Profile schema

            data_schemas = []
            for schema_name, schema in relavant_schemas.items():
                if schema is not None:
                    newSchema = copy.deepcopy(schema)
                    newSchema.xrefs = None
                    cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n","")
                    cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                    cleaned_string = re.sub(r'\\+', "", cleaned_string)
                    data_schemas.append(f"- {schema_name}: {cleaned_string}")
            params["data_schemas"] = "\n".join(data_schemas)
            results = self.op_schema_deps.exec(**params)
            print(results)
            
        return edges
    
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
        schemas = {k: v for opt in operations.values() for k, v in opt.schemas.items()} # extract all schemas
        heuristic_edges = self.heuristic_similarities(operations)
        gpt_edges = self.gpt_similarities(operations, schemas)
        # merge duplicate edges
        print(f"HEURISTIC EDGES: {len(heuristic_edges)}")
        print(f"GPT EDGES: {len(gpt_edges)}")
        with open(self.cache_file.replace("semantic_property_dependency_graph", "heuristic_edges"), "w") as f:
            json.dump([to_dict_helper(edge) for edge in heuristic_edges], f, indent=4)
        with open(self.cache_file.replace("semantic_property_dependency_graph", "gpt_edges"), "w") as f:
            json.dump([to_dict_helper(edge) for edge in gpt_edges], f, indent=4)
            
        edges = self.merge_operation_edges(heuristic_edges, gpt_edges)
        self.edges = edges
        
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
