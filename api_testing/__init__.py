from collections import defaultdict, deque
import copy
import json
import logging
from time import sleep
from api_testing.configuration.configuration_parser import ConfigurationParser
from api_testing.constraint.static_constraint_miner import StaticConstraintMiner
from api_testing.feedback import FeedbackAnalyzer
from api_testing.generators.executor import Executor, Strategy
from api_testing.generators.requestor import Requestor
from api_testing.generators.smart_value_generator import SmartValueGenerator
from api_testing.graph.graph_analyzer import GraphAnalyzer
from api_testing.memory.contextual_memory import ContextualMemory
from api_testing.models.configuration_model import FieldConfiguration
from api_testing.prompts.request_response_constraint import RequestResponseConstraint
from api_testing.utils import flatten_json_schema, to_dict_helper
from api_testing.utils.common import remove_nulls
from api_testing.utils.http import isSuccessful
from collections import defaultdict

from .memory import (
    APITestingVectorDB
)

from .models import (
    APITestingBaseLLMModel,
    APITestingBaseEmbeddingModel,
    GeminiModel,
    OllamaModel,
    HuggingfaceEmbeddingModel,
    OllamaEmbeddingModel
)

from .graph import (
    OperationGraph,
    OperationNode,
    OperationEdge
)
from typing import Dict, Optional, Set, Union, List
from api_testing.dataset import SpecificationParser
from api_testing.graph import OperationGraph
from api_testing.models import APITestingBaseEmbeddingModel, APITestingBaseLLMModel
import shutil
import os
from api_testing.utils.log import configure_logging
from typing import List, Dict, Set, Any
import argparse



def parse_args():
    parser = argparse.ArgumentParser(
        description="APITesting - Automated REST API Testing with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  apitesting                    # Run with TUI and configuration wizard
  apitesting --quick            # Quick setup (essential settings only)
  apitesting --skip-wizard      # Skip wizard, use configurations.toml directly

For more information, visit: https://github.com/thanhtuit96/API-Testing
        """,
    )
    parser.add_argument(
        "--skip-wizard",
        action="store_true",
        help="Skip configuration wizard and use configurations.toml directly",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick setup wizard (essential settings only)",
    )
    parser.add_argument(
        "-s",
        "--spec",
        type=str,
        default=None,
        help="Override specification path (relative to project root)",
    )
    parser.add_argument(
        "-t",
        "--time",
        type=int,
        default=None,
        help="Override test duration in seconds",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=100,
        help="TUI display width (default: 100)",
    )
    return parser.parse_args()



def build_endpoint_groups(data: dict) -> Dict[str, List[str]]:
    """
    Gom nhóm tham số tương tự nhưng tôn trọng hướng truyền dữ liệu giữa các endpoint.
    - value1: từ response của from_node
    - value2: vào parameter của to_node
    Lan truyền bắc cầu theo hướng endpoint graph.
    """
    graph: Dict[str, Set[str]] = defaultdict(set)
    reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    # ==== B1. Xây dựng đồ thị có hướng ====
    for edge in data.get("edges", []):
        for sp in edge.get("similar_parameters", []):
            v1, v2 = sp.get("value1"), sp.get("value2")
            if not v1 or not v2:
                continue
            kv1 = edge.get("from_node") + "_attributes_" + v1
            kv2 = edge.get("to_node") + "_params_" + v2
            graph[kv1].add(kv2)
            reverse_graph[kv2].add(kv1)

    # ==== B2. Duyệt nhóm liên thông (bắc cầu hai chiều) ====
    def traverse_group(start: str, visited: Set[str]) -> Set[str]:
        group = set()
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            group.add(node)
            # Lan truyền xuôi
            for nxt in graph.get(node, []):
                if nxt not in visited:
                    queue.append(nxt)
            # Lan truyền ngược
            for prev in reverse_graph.get(node, []):
                if prev not in visited:
                    queue.append(prev)
        return group

    # ==== B3. Gom nhóm ====
    visited = set()
    groups: Dict[str, Set[str]] = {}
    all_nodes = list(graph.keys()) + list(reverse_graph.keys())

    for node in all_nodes:
        if node not in visited:
            group = traverse_group(node, visited)
            if group:
                canonical = min(group, key=len)
                groups[canonical] = group

    # ==== B4. Kết quả trả về dạng Dict[str, List[str]] ====
    return {k: sorted(list(v)) for k, v in groups.items()}

class APITesting:
    def __init__(self,
                 base_url: Optional[str] = None,
                 base_title: Optional[str] = None,
                 spec_path: str = None,
                 model: Optional[Union[str, APITestingBaseLLMModel]] = None,
                 critic_model: Optional[Union[str,
                                              APITestingBaseLLMModel]] = None,
                 embedder: Optional[Union[str,
                                          APITestingBaseEmbeddingModel]] = None,
                 vector_db: Optional[Union[str,
                                           APITestingVectorDB]] = None,
                 test_single_endpoint: Optional[str] = None,  # New parameter
                 # async_mode=False,
                 ):
        self.base_url = base_url
        self.base_title = base_title
        self.spec_path = spec_path
        self.embedder = embedder
        self.model = model
        self.critic_model = critic_model or model # judge model
        self.vector_db = vector_db
        self.project_dir = None
        self.test_single_endpoint = test_single_endpoint
        self.operation_graph = None
        self._load_()
        
        if self.test_single_endpoint:
            self.init_graph_for_single_endpoint(self.test_single_endpoint)
        else:
            self.init_graph()

    def _load_(self):
        #  get tile from spec_path
        self.spec_parser = SpecificationParser(spec_path=self.spec_path)
        if self.base_title is None:
            self.base_title = self.spec_parser.get_api_title()
        if self.base_url is None:
            self.base_url = self.spec_parser.get_api_url()
        # mkir project if not exist
        self.project_dir = os.path.join(os.getcwd(), ".cache", self.base_title)
        if not os.path.exists(self.project_dir):
            print(f"Cache dir not found, I'll create dir {self.project_dir}")
            os.makedirs(self.project_dir)
            # change pwd to project_dir
            _, file_extension = os.path.splitext(self.spec_path)
            shutil.copyfile(
                self.spec_path, os.path.join(self.project_dir, f"baseline_specification{file_extension}"))
        # logger
        configure_logging(
            log_dir=self.project_dir,
            llm_model=self.model.get_model_name(),
            level=logging.DEBUG
        )
        self.spec_parser.load_or_initialize(cache_dir=self.project_dir)
        # self._preprocess_()
    
    def build_odg(self):
        self.operation_graph = OperationGraph(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        self.operation_graph.create_graph()
        self.operation_graph.save_graph_to_cache()

    def build_config(self):
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()

    def process(self):
        
        self.build_odg()
        self.build_config()
        with open(os.path.join(self.project_dir,"semantic_property_dependency_graph.json"), "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        endpoint_groups = build_endpoint_groups(graph_data)
        with open(os.path.join(self.project_dir,"producer_pool.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(endpoint_groups, indent=4, ensure_ascii=False))

        for endpoint in self.parser.configurations:
            for param in endpoint.params.keys():
                for k,v in endpoint_groups.items():
                    if f'{endpoint.method}-{endpoint.endpoint}_params_{param}' in v:
                        endpoint.params[param] = FieldConfiguration(name=param, type="ProducerGenerator",genParameters={"pool": k} )
        self.parser.json_output()

        # process
    
    def _preprocess_(self):
        # extract contrains
        constraints = {}
        for operation, details in self.spec_parser.operations.items():
            print("EXTRACT CONSTRAINTS", operation)
            simple = details.simple_operation()
            # parameters
            parameters = '\n'.join([
                f'{k}:{v}' for k, v in simple["parameters"].items()
            ])
            response = simple["responses"]
            # Querys =
            query = details.http_method.upper() + " " + details.endpoint_path + \
                " : " + details.description

            results = self.vector_db.search(query=query)
            # query to string
            extras = "\n=========\n".join([res.content for res in results])
            #  read RAGS
            miner = RequestResponseConstraint(
                llm=self.model, endpoint=f"{details.http_method} {details.endpoint_path}", parameters=parameters, response=response, extras=extras)
            constraint = miner.validate()
            constraints[operation] = to_dict_helper(constraint)["constraint"]
            # Contraints
        file_name = os.path.join(
            self.project_dir, f"request_resonponse_constraint.json")
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(constraints, file, ensure_ascii=False, indent=4)

    def init_graph(self):
        # miner = StaticConstraintMiner(spec_parser=self.spec_parser,
        #     model=self.model,
        #     embedding_model=self.embedder,cache_dir=self.project_dir)
        # miner.response_properties_constraints()

        self.operation_graph = OperationGraph(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        self.operation_graph.plot_graph()
    
    def run_tests(self,num_generations=1, num_test_cases=20, mutation_ratio=0.0):
        self.operation_graph = OperationGraph(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.update_conf(self.operation_graph)
        configurations = { f"{conf.method}-{conf.endpoint}": conf for conf in parser.configurations}
        nodes = self.operation_graph.nodes

        total_testcase = 0
        total_success = 0

        # process producer
        # edges = []
        adjacency_map  = {}
        properties = defaultdict(list)

        for edge in self.operation_graph.edges:
            adjacency_map.setdefault(edge.from_node.uuid, []).append(edge)
            properties[edge.from_node.uuid].append(edge)
        producer_map = {}

        def extract_xrefs_for_keys(keys, flatten):
            """
            Trích ra xrefs tương ứng cho danh sách key từ flatten schema.
            Trả về dict { key: xrefs_value hoặc None }
            """
            return {
                key: flatten.get(key, {}).get("xrefs")
                for key in keys
            }
        for uuid, edge in adjacency_map.items():
            producer_map[uuid] = {sp.value1 for e in edge for sp in e.similar_parameters}
            flatten = flatten_json_schema(nodes.get(uuid).successful_responses.to_dict())
            producer_map[uuid] = remove_nulls(extract_xrefs_for_keys(producer_map[uuid], flatten))
            properties[uuid] =  extract_xrefs_for_keys(producer_map[uuid], flatten)   

            # pick
        graph_analyst = GraphAnalyzer(graph=self.operation_graph, cache_dir=self.project_dir)
        feedback_analyzer = FeedbackAnalyzer(model=self.model)

        forest = graph_analyst.export_to_forest()

        def traverse_dfs(node, depth=0, context_pool: ContextualMemory = None,parent=None):
            nonlocal total_testcase, total_success
            context_pool = context_pool or ContextualMemory()
            # 
            print("  " * depth + f"• {node.name} ")

            configuration = copy.copy(configurations.get(node.name))
            # test
            producer = { param: conf for param, conf in configuration.params.items() if conf.type == "ProducerGenerator"}
            if len(producer) > 0:
                for k, v in node.matched_params.items():
                    if k in producer:
                        producer[k].genParameters = {
                            "pool": producer_map.get(v.get("source_endpoint"), {}).get(v.get("source_param"), None),
                            "key": v.get("source_param").split(".")[-1]
                        }
            executor = Executor(
                api_url = self.base_url, 
                strategy= Strategy.NAIVE_VALUE,
                operation=nodes.get(node.name),
                cache_dir=self.project_dir,
                model=self.model,
                num_test_cases=num_test_cases,
                configuration=configurations.get(node.name),
                context_pool=context_pool
            ) 
            responses = executor.exec()
            # feedback = feedback_analyzer.evaluate(responses)
            # successfull responses 

            success_responses = [ 
                entry.get("response",{}).get("content",{}).get("text") 
                for entry in responses if isSuccessful(entry.get("response",{}).get("status",0)) 
            ]
            context_pool.update_with_responses(success_responses, properties.get(node.name))
            print("success", len(success_responses) , "with context_pool", context_pool)
            total_success +=  len(success_responses)
            total_testcase +=  num_test_cases
            # save pool
            for child in node.children.values():
                traverse_dfs(child, depth + 1, context_pool.copy(), node)

        def traverse_forest_dfs(forest):
            """Duyệt toàn bộ rừng"""
            for root_name, root_node in forest.items():
                print(f"\n🌳 Root: {root_name}")
                traverse_dfs(root_node, depth=1)

        for _ in range(num_generations):
            traverse_forest_dfs(forest)
        print("Success rate", total_success/total_testcase)

    
