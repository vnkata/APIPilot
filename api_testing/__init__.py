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
        nodes = [ node for node in self.operation_graph.nodes.values() if node.degree == 0] 
        from typing import List, Dict, Set, Any

        # def find_api_workflows_recursive(
        #     current_node: OperationNode,
        #     path: List[str],
        #     provided_pool: Set[str],
        #     adj_list: Dict[str, List[OperationEdge]],
        #     all_valid_paths: List[Dict]
        # ):
        #     """
        #     Hàm đệ quy duyệt các nhánh API dựa trên điều kiện tham số.
        #     """
        #     # 1. Thu hoạch dữ liệu từ node hiện tại
        #     # Lấy 'value1' từ các cạnh đi RA (giả định node này có thể cung cấp các field đó)
        #     new_data_harvested = set()
        #     for edge in adj_list.get(current_node.uuid, []):
        #         for param_mapping in edge.similar_parameters:
        #             new_data_harvested.add(param_mapping.value1)
        #     current_branch_pool = provided_pool
            
        #     # 2. Tìm các node lân cận có thể đi tiếp
        #     possible_edges = adj_list.get(current_node.uuid, [])
        #     has_valid_next = False

        #     for edge in possible_edges:
        #         neighbor = edge.to_node
                
        #         # ĐIỀU KIỆN 1: Chặn lặp node (Cycle Detection trên nhánh)
        #         if neighbor.uuid in path:
        #             continue
                    
        #         # ĐIỀU KIỆN 2: Kiểm tra tham số bắt buộc
        #         # Lấy danh sách params required của node đích
        #         required_params = [
        #             name for name, p in neighbor.parameters.items() 
        #             if getattr(p, 'required', False)
        #         ]
        #         new_data_harvested = {i for i in new_data_harvested if i in required_params}
        #         # Cập nhật pool dữ liệu cho riêng nhánh này
        #         current_branch_pool = provided_pool.union(new_data_harvested)
    
        #         # Kiểm tra những gì Edge này có thể cung cấp dựa trên Pool hiện tại
        #         mapping_available = {
        #             p.value2 for p in edge.similar_parameters 
        #             if p.value1 in current_branch_pool
        #         }
                
        #         # Kiểm tra xem có đủ required params không
        #         is_satisfied = all(rp in mapping_available for rp in required_params)

        #         if is_satisfied:
        #             has_valid_next = True
        #             # Đệ quy đi sâu vào nhánh này
        #             find_api_workflows_recursive(
        #                 neighbor,
        #                 path + [neighbor.uuid],
        #                 current_branch_pool,
        #                 adj_list,
        #                 all_valid_paths
        #             )
        #         else:
        #             # Debug: In ra lý do nhánh bị chặn
        #             missing = set(required_params) - mapping_available
        #             print(f"Blocked: {'->'.join(path)} -> {neighbor.uuid} thiếu {missing}")
        #             pass

        #     # 3. Nếu không còn nhánh nào đi tiếp được, lưu lại kết quả của nhánh này
        #     if not has_valid_next:
        #         all_valid_paths.append({
        #             "path": path,
        #             "final_pool": current_branch_pool
        #         })

        # # --- Cách sử dụng ---

        # def start_traversal(nodes, edges, start_uuid):
        #     node_map = {n.uuid: n for n in nodes}
            
        #     # Tiền xử lý: Nhóm edges theo from_node_uuid
        #     adj_list = {}
        #     for edge in edges:
        #         adj_list.setdefault(edge.from_node.uuid, []).append(edge)
                
        #     all_results = []
        #     if start_uuid in node_map:
        #         find_api_workflows_recursive(
        #             node_map[start_uuid], 
        #             [start_uuid], 
        #             set(), 
        #             adj_list, 
        #             all_results
        #         )
        #     return all_results
        def find_api_workflows_recursive(
            current_node: OperationNode,
            path: List[str],
            provided_pool: Set[str],
            adj_list: Dict[str, List[OperationEdge]],
            all_valid_paths: List[Dict]
        ):
            # 1. Thu hoạch dữ liệu thô từ node hiện tại
            raw_harvested = {
                p.value1 for edge in adj_list.get(current_node.uuid, []) 
                for p in edge.similar_parameters
            }

            possible_edges = adj_list.get(current_node.uuid, [])

            # --- LOGIC ƯU TIÊN ---
            # Tính toán xem mỗi cạnh mang lại bao nhiêu tham số "mới" chưa từng có trong pool
            def get_priority(edge):
                neighbor_required = {
                    name for name, p in edge.to_node.parameters.items() 
                    if getattr(p, 'required', False)
                }
                # Tham số mới = (Những gì node hiện tại cấp) GIAO (Những gì neighbor cần) TRỪ ĐI (Những gì đã có)
                new_params_count = len((raw_harvested & neighbor_required) - provided_pool)
                return new_params_count

            # Sắp xếp giảm dần theo số lượng tham số mới
            sorted_edges = sorted(possible_edges, key=get_priority, reverse=True)
            # ---------------------

            has_valid_next = False

            for edge in sorted_edges:
                neighbor = edge.to_node
                
                if neighbor.uuid in path:
                    continue
                    
                required_params = {
                    name for name, p in neighbor.parameters.items() 
                    if getattr(p, 'required', False)
                }
                
                useful_data = raw_harvested & required_params
                current_branch_pool = provided_pool | useful_data
                
                mapping_available = {
                    p.value2 for p in edge.similar_parameters 
                    if p.value1 in current_branch_pool
                }
                
                if required_params.issubset(mapping_available):
                    has_valid_next = True
                    find_api_workflows_recursive(
                        neighbor,
                        path + [neighbor.uuid],
                        current_branch_pool,
                        adj_list,
                        all_valid_paths
                    )

            if not has_valid_next:
                all_valid_paths.append({
                    "path": path,
                    "final_pool": provided_pool | raw_harvested
                })

        def start_traversal(nodes, edges, start_uuid):
            node_map = {n.uuid: n for n in nodes}
            
            # Tiền xử lý: Nhóm edges theo from_node_uuid
            adj_list = {}
            for edge in edges:
                adj_list.setdefault(edge.from_node.uuid, []).append(edge)
                
            all_results = []
            if start_uuid in node_map:
                find_api_workflows_recursive(
                    node_map[start_uuid], 
                    [start_uuid], 
                    set(), 
                    adj_list, 
                    all_results
                )
            return all_results
        results = []
        for node in nodes:
            results.extend(start_traversal( self.operation_graph.nodes.values(), self.operation_graph.edges, node.uuid))
        def remove_duplicate_paths(data):
            seen_paths = set()
            unique_data = []
            
            for entry in data:
                # Chuyển list thành tuple để có thể hash và so sánh
                path_tuple = tuple(entry["path"])
                if path_tuple not in seen_paths:
                    unique_data.append(entry)
                    seen_paths.add(path_tuple)
                    
            return unique_data

        results = remove_duplicate_paths(results)
        def is_subset(path_small, path_large):
            """Kiểm tra xem path_small có phải là tập con của path_large hay không"""
            # Cách 1: Kiểm tra đúng thứ tự (Sequence/Prefix)
            # return all(x == y for x, y in zip(path_small, path_large))
            
            # Cách 2: Kiểm tra tập hợp (không quan trọng thứ tự)
            return set(path_small).issubset(set(path_large))

        def filter_subsets(data):
            # Sắp xếp theo độ dài giảm dần để ưu tiên giữ lại các path dài trước
            data.sort(key=lambda x: len(x['path']), reverse=True)
            
            unique_data = []
            for i in range(len(data)):
                is_sub = False
                for j in range(len(unique_data)):
                    # So sánh object hiện tại với các object dài hơn đã được giữ lại
                    if is_subset(data[i]['path'], unique_data[j]['path']):
                        is_sub = True
                        break
                if not is_sub:
                    unique_data.append(data[i])
                    
            return unique_data
        results = filter_subsets(results)
        with open("demo.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, default=str)

    
    def run_tests(self):
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()
        # endpoint_groups = build_endpoint_groups(os.path.join(self.cache_dir,"semantic_property_dependency_graph.json"))
        # for endpoint_conf in parser.configurations:
        