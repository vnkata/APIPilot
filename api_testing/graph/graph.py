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
    def __init__(self, spec_parser=None, model=None, embedding_model=None, threshold=0.6, cache_dir=None, skip_create_graph: bool = False):
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
        self.skip_create_graph  = skip_create_graph
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
            if not self.skip_create_graph:

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
    def get_param_entity(self, param_name: str, endpoint_path: str) -> str:
        """
        Get the entity name for a path parameter.
        
        /projects/{id}/commits/{sha}
        -> id: "project"
        -> sha: "commit"
        """
        segments = endpoint_path.split('/')
        for i, segment in enumerate(segments):
            if segment == f"{{{param_name}}}" and i > 0:
                preceding = segments[i - 1]
                # Remove trailing 's' for singular
                if preceding.endswith('s'):
                    return preceding[:-1]
                return preceding
        return ""
    def get_best_matching_schema(self, operation: OperationProperties, schemas: Dict[str, ItemProperties], top_k: int =3):
        endpoint = operation.endpoint_path

        endpoint = endpoint.replace(self.path_tree, "") # only get relative path
        endpoint = endpoint.lower()
        endpoint = re.sub(r'\{.*?\}', '', endpoint)
        endpoint = re.sub(r"[_]", " ", endpoint)
        endpoint = re.sub(r"[^\w\s]", "", endpoint) 
        endpoint = re.sub(r"\s+", " ", endpoint).strip()
        similarity_scores = [0] * len(schemas)
        for params in operation.parameters.values():
            entity = self.get_param_entity(params.name, operation.endpoint_path)
            if entity:
                base_str = f"{params.name}_{entity}".lower()
            else:
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
        
        # Collect all subschemas first, then update results after iteration
        subschemas_to_add = {}
        for schema_name in list(results.keys()):
            schema = schemas.get(schema_name)
            if schema is not None:
                subschemas = self.get_subschemas_of_schema(schema)
                subschemas_to_add.update(subschemas)
        
        results.update(subschemas_to_add)

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
    
    def gpt_similarities(self, operations: List[OperationProperties], schemas: Dict[str, ItemProperties]):
        
        edges = []
        summary_results = []
        
        # Create debug folder BEFORE the loop
        debug_folder = os.path.join(os.path.dirname(self.cache_file), "op_schema_deps_debug")
        os.makedirs(debug_folder, exist_ok=True)

        for idx, operation in enumerate(operations.values()): 
            # Skip operations with no parameters
            if len(operation.parameters) == 0 and len(operation.request_body) == 0:
                print(f"SKIP NODE {operation.http_method.upper()} {operation.endpoint_path} DUE TO NO PARAMETERS AND REQUEST BODY")
                summary_results.append({
                    "index": idx,
                    "operation": f"{operation.http_method.upper()} {operation.endpoint_path}",
                    "success": False,
                    "skipped": True,
                    "reason": "No parameters or request body"
                })
                continue

            params = {
                "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
                "summary": ((operation.summary or "") + " " + (operation.description or "")).strip(),
                "specific_endpoint_params": "\n".join([
                    f"- {k} : {v.to_human_readable()}" 
                    for k, v in operation.parameters.items() 
                    if v.schema.type not in ("boolean",)
                ]),
            }
            relevant_schemas = self.get_best_matching_schema(operation, schemas, top_k=10)

            data_schemas = []
            for schema_name, schema in relevant_schemas.items():
                if schema is not None:
                    newSchema = copy.deepcopy(schema)
                    newSchema.xrefs = None
                    cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n", "")
                    cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                    cleaned_string = re.sub(r'\\+', "", cleaned_string)
                    data_schemas.append(f"- {schema_name}: {cleaned_string}")
            params["data_schemas"] = "\n".join(data_schemas)
            
            # Build full prompt
            full_prompt = self.op_schema_deps.PROMPT.format(**params)
            
            # Create safe filename for individual debug file
            safe_name = re.sub(r'[^\w\-]', '_', f"{operation.http_method}_{operation.endpoint_path}")
            safe_name = re.sub(r'_+', '_', safe_name)[:100]
            debug_file = os.path.join(debug_folder, f"{idx:03d}_{safe_name}.json")
            
            # Build debug entry
            debug_entry = {
                "index": idx,
                "operation": params["endpoint"],
                "operation_uuid": operation.uuid,
                "input": {
                    "endpoint": params["endpoint"],
                    "summary": params["summary"],
                    "specific_endpoint_params": params["specific_endpoint_params"],
                    "data_schemas": params["data_schemas"],
                },
                "full_prompt": full_prompt,
                "relevant_schemas": list(relevant_schemas.keys()),
            }
            
            try:
                print(f"\n[{idx}] Calling LLM for: {operation.http_method.upper()} {operation.endpoint_path}")
                
                # Single LLM call - get raw response
                raw_response, _ = self.model.generate(
                    system_prompt=self.op_schema_deps.SYSTEM_PROMPT,
                    prompt=full_prompt,
                    schema=None
                )
                debug_entry["raw_response"] = raw_response
                print(f"RAW RESPONSE:\n{raw_response}")
                
                # Parse the raw response locally (NO second LLM call)
                from api_testing.prompts.op_schema_deps.schema import Verdict
                try:
                    # Extract JSON from response
                    json_content = raw_response.strip()
                    if json_content.startswith("```"):
                        first_newline = json_content.find("\n")
                        if first_newline != -1:
                            json_content = json_content[first_newline + 1:]
                        if json_content.endswith("```"):
                            json_content = json_content[:-3]
                        json_content = json_content.strip()
                    
                    # Fix arrays - convert single strings to arrays
                    data = json.loads(json_content)
                    if "schemas" in data and isinstance(data["schemas"], dict):
                        for schema_name, schema_params in data["schemas"].items():
                            if isinstance(schema_params, dict):
                                for param_key, param_value in list(schema_params.items()):
                                    if isinstance(param_value, str):
                                        if "," in param_value:
                                            data["schemas"][schema_name][param_key] = [v.strip() for v in param_value.split(",")]
                                        else:
                                            data["schemas"][schema_name][param_key] = [param_value]
                                    elif param_value is None:
                                        del data["schemas"][schema_name][param_key]
                    
                    fixed_content = json.dumps(data)
                    parsed_response = Verdict.model_validate_json(fixed_content)
                    
                    print(f"PARSED RESPONSE:\n{parsed_response}")
                    
                    # Convert results to dict
                    if hasattr(parsed_response, 'model_dump'):
                        result_dict = parsed_response.model_dump()
                    elif hasattr(parsed_response, '__dict__'):
                        result_dict = parsed_response.__dict__
                    else:
                        result_dict = {"raw": str(parsed_response)}
                    
                    debug_entry["parsed_response"] = result_dict
                    debug_entry["success"] = True
                    
                    summary_results.append({
                        "index": idx,
                        "operation": params["endpoint"],
                        "success": True,
                        "schemas_found": list(result_dict.get("schemas", {}).keys()) if result_dict else [],
                    })
                    
                except Exception as parse_error:
                    print(f"PARSING ERROR: {parse_error}")
                    debug_entry["parsed_response"] = None
                    debug_entry["parse_error"] = str(parse_error)
                    debug_entry["success"] = False
                    summary_results.append({
                        "index": idx,
                        "operation": params["endpoint"],
                        "success": False,
                        "error": f"Parse error: {parse_error}"
                    })
                    
            except Exception as e:
                print(f"LLM ERROR: {e}")
                import traceback
                traceback.print_exc()
                
                debug_entry["raw_response"] = None
                debug_entry["error"] = str(e)
                debug_entry["success"] = False
                summary_results.append({
                    "index": idx,
                    "operation": params["endpoint"],
                    "success": False,
                    "error": str(e)
                })
            
            # Save individual debug file
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(debug_entry, f, indent=2, ensure_ascii=False, default=str)
            print(f"Saved debug to: {debug_file}")
        
        # Save summary file
        summary_file = os.path.join(debug_folder, "_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump({
                "total_operations": len(summary_results),
                "successful": sum(1 for r in summary_results if r.get("success", False)),
                "failed": sum(1 for r in summary_results if not r.get("success", False)),
                "results": summary_results
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*60}")
        print(f"Debug files saved to: {debug_folder}")
        print(f"Total: {len(summary_results)} | Success: {sum(1 for r in summary_results if r.get('success', False))} | Failed: {sum(1 for r in summary_results if not r.get('success', False))}")
        print(f"Summary: {summary_file}")
        
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
    def test_single_endpoint(self, operation_uuid: str, operations: Dict[str, OperationProperties] = None, schemas: Dict[str, ItemProperties] = None):
            """
            Test the LLM prompt for a single endpoint to debug schema dependency detection.
            
            :param operation_uuid: The UUID of the operation (e.g., "get-/projects/{id}/repository/commits/{sha}")
            :param operations: Optional dict of operations, uses spec_parser if not provided
            :param schemas: Optional dict of schemas, uses spec_parser if not provided
            :return: Tuple of (prompt_params, raw_response, parsed_response)
            """
            if operations is None:
                operations = self.spec_parser.operations
            if schemas is None:
                schemas = {k: v for opt in operations.values() for k, v in opt.schemas.items()}
            
            # Find the operation
            operation = operations.get(operation_uuid)
            if operation is None:
                available = list(operations.keys())
                raise ValueError(f"Operation '{operation_uuid}' not found. Available: {available[:5]}...")
            
            # Build the same params as gpt_similarities
            paths = [opt.endpoint_path for opt in operations.values()]
            self.path_tree = os.path.commonprefix(paths)
            
            params = {
                "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
                "summary": ((operation.summary or "") + " " + (operation.description or "")).strip(),
                "specific_endpoint_params": "\n".join([
                    f"- {k} : {v.to_human_readable()}" 
                    for k, v in operation.parameters.items() 
                    if v.schema.type not in ("boolean")
                ]),
            }
            
            relevant_schemas = self.get_best_matching_schema(operation, schemas, top_k=10)
            
            data_schemas = []
            for schema_name, schema in relevant_schemas.items():
                if schema is not None:
                    newSchema = copy.deepcopy(schema)
                    newSchema.xrefs = None
                    cleaned_string = newSchema.to_human_readable().replace('\\n', '').replace("\n", "")
                    cleaned_string = re.sub(r'\s+', ' ', cleaned_string).strip()
                    cleaned_string = re.sub(r'\\+', "", cleaned_string)
                    data_schemas.append(f"- {schema_name}: {cleaned_string}")
            
            params["data_schemas"] = "\n".join(data_schemas)
            
            # Print the full prompt for debugging
            print("=" * 80)
            print("SYSTEM PROMPT:")
            print("=" * 80)
            print(self.op_schema_deps.SYSTEM_PROMPT)
            print("\n" + "=" * 80)
            print("USER PROMPT:")
            print("=" * 80)
            full_prompt = self.op_schema_deps.PROMPT.format(**params)
            print(full_prompt)
            print("\n" + "=" * 80)
            
            # Get raw response (without schema validation)
            print("CALLING LLM (raw, no schema)...")
            raw_response, _ = self.model.generate(
                system_prompt=self.op_schema_deps.SYSTEM_PROMPT,
                prompt=full_prompt,
                schema=None  # No schema to see raw output
            )
            print("RAW RESPONSE:")
            print(raw_response)
            print("\n" + "=" * 80)
            
            # Get parsed response (with schema validation)
            print("CALLING LLM (with schema validation)...")
            try:
                from api_testing.prompts.op_schema_deps.schema import Verdict
                parsed_response, _ = self.model.generate(
                    system_prompt=self.op_schema_deps.SYSTEM_PROMPT,
                    prompt=full_prompt,
                    schema=Verdict
                )
                print("PARSED RESPONSE:")
                print(parsed_response)
            except Exception as e:
                print(f"PARSING ERROR: {e}")
                parsed_response = None
            
            print("=" * 80)
            
            return {
                "params": params,
                "raw_response": raw_response,
                "parsed_response": parsed_response,
                "relevant_schemas": list(relevant_schemas.keys())
            }