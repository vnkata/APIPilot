from collections import defaultdict, deque
import json
import logging
from api_testing.configuration.configuration_parser import ConfigurationParser
from api_testing.constraint.static_constraint_miner import StaticConstraintMiner
from api_testing.models.configuration_model import FieldConfiguration
from api_testing.prompts.request_response_constraint import RequestResponseConstraint
from api_testing.utils import to_dict_helper

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
        self.critic_model = critic_model  # judge model
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
    def build_conf(self):
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()
        parser.export_debug_log()
    
    def process(self):
        self.init_graph()
        with open(os.path.join(self.project_dir,"semantic_property_dependency_graph.json"), "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        endpoint_groups = build_endpoint_groups(graph_data)
        with open(os.path.join(self.project_dir,"producer_pool.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(endpoint_groups, indent=4, ensure_ascii=False))
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()
        for endpoint in parser.configurations:
            for param in endpoint.params.keys():
                for k,v in endpoint_groups.items():
                    print(f'{endpoint.method.lower()}-{endpoint.endpoint}_params_{param}')
                    print(v)
                    if f'{endpoint.method}-{endpoint.endpoint}_params_{param}' in v:
                        endpoint.params[param] = FieldConfiguration(name=param, type="ProducerGenerator",genParameters={"pool": k} )
        parser.export_debug_log()
        
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

        
    def train_experience(self, population=200):
        pass
        # print("Trainning")
        # # 
        # nodes = self.operation_graph.nodes.values()
        # nodes_sorted_by_degree = sorted(nodes, key=lambda x : x.degree)
        
        # for node in nodes_sorted_by_degree:
        #     print(node.uuid)
    
    def run_tests(self):
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()
        # endpoint_groups = build_endpoint_groups(os.path.join(self.cache_dir,"semantic_property_dependency_graph.json"))
        # for endpoint_conf in parser.configurations:
        parser.export_debug_log()
        