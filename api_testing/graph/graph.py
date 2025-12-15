import json
import os
from dataclasses import asdict, dataclass
from typing import List, Dict

from api_testing.models.graph_model import OperationEdge, OperationNode, SimilarityValue
from api_testing.models.specification_model import ItemProperties, OperationProperties

from api_testing.prompts import OpSchemaDeps
from api_testing.utils import flatten_json_schema, to_dict_helper
import networkx as nx
import pyvis.network as net
import time
import re
from difflib import SequenceMatcher
import copy
from api_testing.log import getLogger
from sentence_transformers import util

from api_testing.utils.graph import get_best_mathching_schema, is_nested_path_end_with

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
        self.logger = getLogger()
        # prompt for operation-schema dependencies
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
                        for item in edge['similar_parameters']
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
            if operation.uuid in ("get-/api/v1/holidays","get-/api/v1/provinces"):
                continue
            #par
            self.logger.debug("GPT CHECK FOR OPERATION: " + operation.http_method.upper() + " " + operation.endpoint_path)
            if len(operation.parameters) == 0 and len(operation.request_body) == 0:
                print(
                    f"SKIP NODE {operation.http_method.upper()} {operation.endpoint_path} DUE TO NO PARAMETERS AND REQUEST BODY")
                continue
 
            params = {
                "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
                "summary": ((operation.summary or "") + " " + (operation.description or "")).strip(),
                "specific_endpoint_params": "\n".join([ f"- {k} : {v.to_human_readable()}" for k,v in operation.parameters.items() if v.schema.type not in ("boolean")]), # experiences filter params
            }
            relavant_schemas = get_best_mathching_schema(embedding_model=self.embedding_model, operation=operation, schemas=schemas, threshold=self.threshold, path_tree=self.path_tree)
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
            for schema_name, mapping in results.items():
                similarities = []
                for opt in operations.values():
                    if schema_name in opt.schemas:
                        self.logger.debug("CHECK MAPPING FOR SCHEMA: " + schema_name + " IN OPERATION: " + opt.http_method.upper() + " " + opt.endpoint_path)
                        for param_name, attribute_names in mapping.items():
                            for attribute_name in attribute_names.split(", "):
                                # attribute_name
                                successful_responses = opt.successful_responses
                                flatten = flatten_json_schema(successful_responses.to_dict())
                                attributes = [ att for att, props in flatten.items() if is_nested_path_end_with(att, attribute_name) and props.get("xrefs", None) == schema_name ]
                                for attr in attributes:
                                    self.logger.debug(f"Mapping parameter {param_name} to attribute {attr} via GPT")
                                    similarities.append(SimilarityValue(
                                        value1=attr,
                                        value2=param_name,
                                        in_value=f"response to parameter via gpt"
                                    ))
                        if len(similarities) > 0:
                            edges.append(OperationEdge(
                                from_node=opt,
                                to_node=operation,
                                similar_parameters=similarities
                            ))
                
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
        edges = self.merge_operation_edges(heuristic_edges, gpt_edges)
        print(f"HEURISTIC EDGES: {len(heuristic_edges)}")
        print(f"GPT EDGES: {len(gpt_edges)}")
        with open(self.cache_file.replace("semantic_property_dependency_graph", "heuristic_edges"), "w") as f:
            json.dump([to_dict_helper(edge) for edge in heuristic_edges], f, indent=4)
        with open(self.cache_file.replace("semantic_property_dependency_graph", "gpt_edges"), "w") as f:
            json.dump([to_dict_helper(edge) for edge in gpt_edges], f, indent=4)
            
        
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
