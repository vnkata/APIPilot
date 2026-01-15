from collections import defaultdict, deque
import json
import logging
from api_testing.configuration.configuration_parser import ConfigurationParser
from api_testing.constraint.static_constraint_miner import StaticConstraintMiner
from api_testing.generators.executor import Executor, Strategy
from api_testing.generators.requestor import Requestor
from api_testing.generators.smart_value_generator import SmartValueGenerator
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
from typing import List, Dict, Set, Any


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
        self.parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
    
    def process(self):
        
        self.init_graph()
        self.build_conf()
        
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
        
    
    def train_experience(self, population=200):
        print("Trainning")
        # 
        started_nodes = { node.uuid: node for node in self.operation_graph.nodes.values() if node.degree == 0} # get all nodes no dependency
        # Tiền xử lý: Nhóm edges theo from_node_uuid
        adj_list = {}
        for edge in self.operation_graph.edges:
            adj_list.setdefault(edge.from_node.uuid, []).append(edge)
        
        def traversal(
            current_node,
            path: List[str],
            provided_pool: Set[str],
            adj_list: Dict[str, List["OperationEdge"]],
            all_valid_paths: List[Dict],
        ):
            """
            DFS traversal từ node gốc đến node lá, chỉ lưu các đường đi hợp lệ.
            Một đường đi hợp lệ là khi mỗi node kế tiếp có đủ required parameters
            từ các node trước đó.
            """

            # 1️⃣ Thu hoạch dữ liệu mà node hiện tại có thể cung cấp
            current_uuid = current_node.uuid
            # process current node
            executor = Executor(api_url = self.base_url, 
                strategy= Strategy.SMART_VALUE,
                operation=current_node,
                cache_dir=self.project_dir,
                model=self.model
            ) 
            executor.exec()
            possible_edges = adj_list.get(current_uuid, [])
            raw_harvested = {
                p.value1
                for edge in possible_edges
                for p in edge.similar_parameters
            }
            print("current ", current_uuid, " pool ", raw_harvested)

            # Nếu node hiện tại là node lá (không có outgoing edge) → kết thúc DFS
            if not possible_edges:
                all_valid_paths.append({
                    "path": path,
                    "final_pool": provided_pool | raw_harvested
                })
                return

            # 2️⃣ Ưu tiên cạnh mang lại nhiều tham số mới hơn
            def get_priority(edge):
                neighbor_required = {
                    name
                    for name, p in edge.to_node.parameters.items()
                }
                new_raw_harvested = {p.value2 for p in edge.similar_parameters}
                # Các tham số mới mà current node có thể cung cấp cho neighbor
                new_params_count = len((new_raw_harvested & neighbor_required) - provided_pool)
                return new_params_count

            # Tính priority cho từng edge
            edge_priorities = [(edge, get_priority(edge)) for edge in possible_edges]

            # Chỉ giữ các cạnh có priority > 0
            valid_edges = [edge for edge, score in edge_priorities if score > 0]

            # Sắp xếp giảm dần theo priority
            sorted_edges = sorted(valid_edges, key=lambda e: get_priority(e), reverse=True)

            has_valid_next = False
            # 3️⃣ Duyệt từng cạnh hợp lệ
            for edge in sorted_edges:
                neighbor = edge.to_node

                # Tránh vòng lặp
                if neighbor.uuid in path:
                    continue
                
                # Lấy tập tham số required của node kế tiếp
                required_params = {
                    name
                    for name, p in neighbor.parameters.items()
                    if getattr(p, "required", False)
                }
                mapped_outputs = {
                        p.value2
                        for p in edge.similar_parameters
                        if p.value1 in raw_harvested
                    }

                # 3️⃣ Các dữ liệu hữu ích có thể cung cấp cho neighbor
                useful_data = mapped_outputs & required_params
                current_branch_pool = provided_pool | useful_data

                # Nếu đủ dữ liệu để đi sang node kế → đi tiếp
                if required_params.issubset(current_branch_pool):
                    has_valid_next = True
                    traversal(
                        neighbor,
                        path + [neighbor.uuid],
                        provided_pool | raw_harvested,
                        adj_list,
                        all_valid_paths,
                    )

            # 4️⃣ Nếu node hiện tại không có neighbor hợp lệ → đây là node lá hợp lệ
            if not has_valid_next:
                all_valid_paths.append({
                    "path": path,
                    "final_pool": provided_pool | raw_harvested
                })

        all_results = []
        for start_uuid, start_props in started_nodes.items():
            traversal(current_node=start_props, path=[start_uuid], provided_pool=set(), adj_list=adj_list, all_valid_paths=all_results)
        with open("demo.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=4, default=str)
    
    def run_tests(self):
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()
        