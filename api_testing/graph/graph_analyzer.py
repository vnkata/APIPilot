
import json
import os
from heapq import nlargest

class TreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children: dict[str, "TreeNode"] = {}
        self.matched_params: dict[str, dict] = {}

    def add_child_with_params(
        self,
        path: list[str],
        endpoints_data: dict[str, list[dict]],
        inherited_params: dict | None = None,
        ancestors: list[str] | None = None,
    ):
        """
        Build tree where parameter mapping respects the actual path chain.
        Each tree path (Bills-chain vs Sittings-chain) maps its own sources independently.
        """
        if not path:
            return

        current_uuid, *tail = path
        if inherited_params is None:
            inherited_params = {}
        if ancestors is None:
            ancestors = []

        # --- 1️⃣ Params của current node (nguồn từ chính nó hoặc ancestor thật) ---
        current_params = {}
        for record in endpoints_data.get(current_uuid, []):
            for target_p, sources in record.get("params", {}).items():
                for src in sources:
                    src_ep = src.get("source_endpoint")
                    if src_ep == current_uuid or src_ep in ancestors:
                        current_params[target_p] = src

        combined_params = {**inherited_params, **current_params}
        self.matched_params.update(combined_params)

        # --- 2️⃣ Nếu đã hết path ---
        if not tail:
            return

        next_uuid = tail[0]
        child = self.children.setdefault(next_uuid, TreeNode(next_uuid))

        # --- 3️⃣ Lấy params cho child, chỉ giữ nguồn nằm trong path cụ thể ---
        child_params = {}
        for record in endpoints_data.get(next_uuid, []):
            for target_p, sources in record.get("params", {}).items():
                for src in sources:
                    src_ep = src.get("source_endpoint")
                    # chỉ giữ nếu nguồn thuộc ancestor chain hiện tại
                    if src_ep in ancestors + [current_uuid]:
                        child_params[target_p] = src

        # --- 4️⃣ Gọi đệ quy ---
        child.add_child_with_params(
            tail,
            endpoints_data,
            {**combined_params, **child_params},
            ancestors + [current_uuid],
        )

class GraphAnalyzer:
    def __init__(self, graph=None, cache_dir=None):
        self.graph = graph
        self.cache_file = os.path.join(
            cache_dir, "dependency_sequences.json")
        self.__load_or_initialize()

    def __load_or_initialize(self):
        if  os.path.exists(self.cache_file):
            print(f"Loading analyzer from cache: {self.cache_file}")
            with open(self.cache_file, "r") as file:
                data = json.load(file)
                self.operation_sequences = data
        else:
            print(f"build analyzer ...")
            self.build_sequences()
            self.save_to_cache()
    
    def __operation_sequences(self, target, adjacency_map, visited=None, param_mapping=None, top_k=2):
        visited = visited or set()
        base_param_mapping = param_mapping or {}
        target_uuid = target.uuid

        if target_uuid in visited:
            return []
        
        current_visited = visited | {target_uuid}
        edges = adjacency_map.get(target_uuid, [])
        
        current_target_path_params = {
            str(p.name) for n, p in target.parameters.items() 
            if getattr(p, 'in_value', '') == "path"
        }
        
        all_results = []

        # === PHASE 1: SELF-CONTAINED CHECK ===
        self_edges = [e for e in edges if getattr(e.from_node, "uuid", None) == target_uuid]
        self_produced = {sp.value2 for e in self_edges for sp in e.similar_parameters}
        all_produced = {sp.value2 for edge in edges for sp in edge.similar_parameters}

        if not current_target_path_params and all_produced.issubset(self_produced):
            mapping = {p: [{"source_param": p, "source_endpoint": target_uuid}] 
                    for p in target.parameters.keys() if p in self_produced}
            all_results.append({
                "type": "self-contained",
                "combined_sequences": [[target_uuid]],
                "params": {**base_param_mapping, **mapping},
                "score": 0 # Độ dài chuỗi
            })

        # === PHASE 2: CANDIDATE RANKING ===
        candidates = []
        for edge in edges:
            from_node = edge.from_node
            if from_node.uuid == target_uuid:
                continue
            
            # Lấy tập tham số thực tế mà cạnh này cung cấp
            provided_params = {sp.value2 for sp in edge.similar_parameters}
            
            # Chỉ xét nếu cạnh này đóng góp ít nhất một tham số cần thiết
            if current_target_path_params.intersection(provided_params) or not current_target_path_params:
                # Ranking criteria nâng cao:
                # - is_evolving: 1 nếu rút gọn được cấu trúc tham số
                # - efficiency: số lượng tham số cung cấp / số lượng tham số node nguồn yêu cầu
                is_evolving = 1 if len(provided_params) >= len(current_target_path_params) else 0
                richness = len(provided_params)
                
                candidates.append({
                    "edge": edge,
                    "from_node": from_node,
                    "priority": (is_evolving, richness)
                })

        # Sắp xếp ứng viên
        candidates.sort(key=lambda x: x["priority"], reverse=True)

        # === PHASE 3: SEQUENCE BUILDING ===
        for candidate in candidates:
            edge = candidate["edge"]
            from_node = candidate["from_node"]
            mapped_on_edge = {sp.value2: sp.value1 for sp in edge.similar_parameters}
            
            # Chỉ xử lý nếu cạnh này thỏa mãn các path params của target
            if current_target_path_params.issubset(set(mapped_on_edge.keys())):
                from_name = getattr(from_node, "name", from_node.uuid)
                edge_mapping = {
                    t_p: [{"source_param": s_p, "source_endpoint": from_name}]
                    for t_p, s_p in mapped_on_edge.items() if t_p in current_target_path_params
                }
                combined_mapping = {**base_param_mapping, **edge_mapping}
                from_req_params = getattr(from_node, "required_parameters", [])

                if len(from_req_params) > 0:
                    upstream_results = self.__operation_sequences(
                        from_node, adjacency_map, current_visited, combined_mapping
                    )
                    
                    for upstream in upstream_results:
                        if upstream["type"] == "unresolved": continue
                        for seq in upstream["combined_sequences"]:
                            all_results.append({
                                "type": "recursive-path",
                                "combined_sequences": [seq + [target_uuid]],
                                "params": upstream["params"],
                                "score": len(seq) + 1
                            })
                else:
                    all_results.append({
                        "type": "direct-path",
                        "combined_sequences": [[from_node.uuid, target_uuid]],
                        "params": combined_mapping,
                        "score": 2
                    })

        # === PHASE 4: FINAL OPTIMIZATION (Lọc bỏ chuỗi rác) ===
        if all_results:
            # Lọc bỏ các unresolved nếu đã có đường đi tốt
            valid_paths = [r for r in all_results if r["type"] != "unresolved"]
            if valid_paths:
                # Sắp xếp tất cả kết quả theo độ dài chuỗi (score) tăng dần
                valid_paths.sort(key=lambda x: x["score"])
                
                # Trả về kết quả ngắn nhất (Slice lấy 1 phần tử đầu tiên để tối ưu nhất)
                return valid_paths[:top_k]

        return [{"type": "unresolved", "combined_sequences": [[target_uuid]], "params": base_param_mapping, "score": 999}]
    

    # def __operation_sequences(
    #     self,
    #     target,
    #     adjacency_map,
    #     visited=None,
    #     param_mapping=None,
    #     top_k=2,
    #     _cache=None,
    #     _edge_data=None
    # ):
    #     """
    #     Optimized recursive search for operation sequences.
    #     Uses caching, precomputed edge data, and efficient merges to reduce time complexity.
    #     """

    #     # === PHASE 0: INITIAL SETUP & CACHE ===
    #     if visited is None:
    #         visited = set()
    #     if param_mapping is None:
    #         param_mapping = {}
    #     if _cache is None:
    #         _cache = {}
    #     if _edge_data is None:
    #         # Precompute edge lookup table for performance
    #         _edge_data = {
    #             id(e): {
    #                 "from_uuid": getattr(e.from_node, "uuid", None),
    #                 "similar_map": {sp.value2: sp.value1 for sp in getattr(e, "similar_parameters", [])},
    #             }
    #             for edges in adjacency_map.values()
    #             for e in edges
    #         }

    #     target_uuid = target.uuid
    #     # ✅ Safe cache key using JSON serialization (handles lists/dicts)
    #     cache_key = (target_uuid, json.dumps(param_mapping, sort_keys=True))
    #     if cache_key in _cache:
    #         return _cache[cache_key]

    #     # Prevent infinite recursion
    #     if target_uuid in visited:
    #         return []

    #     visited.add(target_uuid)
    #     edges = adjacency_map.get(target_uuid, [])
    #     current_target_path_params = {
    #         str(p.name)
    #         for _, p in getattr(target, "parameters", {}).items()
    #         if getattr(p, "in_value", "") == "path"
    #     }

    #     all_results = []

    #     # === PHASE 1: SELF-CONTAINED CHECK ===
    #     self_edges = [e for e in edges if getattr(e.from_node, "uuid", None) == target_uuid]
    #     self_produced = {sp.value2 for e in self_edges for sp in getattr(e, "similar_parameters", [])}
    #     all_produced = {sp.value2 for e in edges for sp in getattr(e, "similar_parameters", [])}

    #     if not current_target_path_params and all_produced.issubset(self_produced):
    #         mapping = {
    #             p: [{"source_param": p, "source_endpoint": target_uuid}]
    #             for p in getattr(target, "parameters", {}).keys()
    #             if p in self_produced
    #         }
    #         all_results.append({
    #             "type": "self-contained",
    #             "combined_sequences": [[target_uuid]],
    #             "params": {**param_mapping, **mapping},
    #             "score": 0
    #         })

    #     # === PHASE 2: CANDIDATE RANKING ===
    #     candidates = []
    #     for edge in edges:
    #         edge_info = _edge_data[id(edge)]
    #         from_node = getattr(edge, "from_node", None)
    #         from_uuid = edge_info["from_uuid"]
    #         if from_uuid == target_uuid or from_node is None:
    #             continue

    #         provided_params = set(edge_info["similar_map"].keys())
    #         if current_target_path_params.intersection(provided_params) or not current_target_path_params:
    #             is_evolving = int(len(provided_params) >= len(current_target_path_params))
    #             richness = len(provided_params)
    #             candidates.append({
    #                 "edge": edge,
    #                 "from_node": from_node,
    #                 "priority": (is_evolving, richness)
    #             })

    #     # Use heapq.nlargest instead of full sorting
    #     candidates = nlargest(top_k, candidates, key=lambda x: x["priority"])

    #     # === PHASE 3: SEQUENCE BUILDING ===
    #     for candidate in candidates:
    #         edge = candidate["edge"]
    #         from_node = candidate["from_node"]
    #         edge_info = _edge_data[id(edge)]
    #         mapped_on_edge = edge_info["similar_map"]

    #         # Only consider if this edge provides required path parameters
    #         if current_target_path_params.issubset(mapped_on_edge.keys()):
    #             from_name = getattr(from_node, "name", from_node.uuid)
    #             edge_mapping = {
    #                 t_p: [{"source_param": s_p, "source_endpoint": from_name}]
    #                 for t_p, s_p in mapped_on_edge.items()
    #                 if t_p in current_target_path_params
    #             }

    #             combined_mapping = param_mapping.copy()
    #             combined_mapping.update(edge_mapping)
    #             from_req_params = getattr(from_node, "required_parameters", [])

    #             if from_req_params:
    #                 upstream_results = self.__operation_sequences(
    #                     from_node,
    #                     adjacency_map,
    #                     visited,
    #                     combined_mapping,
    #                     top_k=top_k,
    #                     _cache=_cache,
    #                     _edge_data=_edge_data
    #                 )

    #                 for upstream in upstream_results:
    #                     if upstream["type"] == "unresolved":
    #                         continue
    #                     for seq in upstream["combined_sequences"]:
    #                         all_results.append({
    #                             "type": "recursive-path",
    #                             "combined_sequences": [seq + [target_uuid]],
    #                             "params": upstream["params"],
    #                             "score": len(seq) + 1
    #                         })
    #             else:
    #                 all_results.append({
    #                     "type": "direct-path",
    #                     "combined_sequences": [[from_node.uuid, target_uuid]],
    #                     "params": combined_mapping,
    #                     "score": 2
    #                 })

    #     # Backtrack visited node
    #     visited.remove(target_uuid)

    #     # === PHASE 4: FINAL OPTIMIZATION (FILTERING) ===
    #     if all_results:
    #         valid_paths = [r for r in all_results if r["type"] != "unresolved"]
    #         if valid_paths:
    #             valid_paths.sort(key=lambda x: x["score"])
    #             _cache[cache_key] = valid_paths[:top_k]
    #             return valid_paths[:top_k]

    #     unresolved = [{
    #         "type": "unresolved",
    #         "combined_sequences": [[target_uuid]],
    #         "params": param_mapping,
    #         "score": 999
    #     }]
    #     _cache[cache_key] = unresolved
    #     return unresolved

    def build_sequences(self, top_k=2):
        # 2️⃣ Nhóm cạnh theo to_node.uuid (để truy ngược về các node có thể dẫn đến nó)
        adjacency_map  = {}
        for edge in self.graph.edges:
            adjacency_map.setdefault(edge.to_node.uuid, []).append(edge)
        operation_seq = {}
        for node in self.graph.nodes.values():
            sequences = self.__operation_sequences(node, adjacency_map,top_k=top_k)
            operation_seq[node.uuid] = sequences
        
        self.operation_sequences = operation_seq

    def save_to_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.operation_sequences, f, indent=4, ensure_ascii=False)

    def export_to_forest(self):
        """
        Build a forest (dict of root_uuid -> TreeNode) from operation_sequences.

        A root endpoint is defined as one that does NOT contain any path parameters (no `{}` in its name).
        Each root node's tree includes all combined_sequences that begin with that endpoint.
        """

        forest = {}

        # 1️⃣ Identify root endpoints: those without path parameters
        root_uuids = [
            uuid for uuid in self.operation_sequences.keys()
            if "{" not in uuid and "}" not in uuid
        ]

        # 2️⃣ For each root, build its tree
        for r_uuid in root_uuids:
            root_node = TreeNode(r_uuid)

            # Iterate through all endpoints and sequences
            for target_uuid, candidates in self.operation_sequences.items():
                for candidate in candidates:
                    for path in candidate.get("combined_sequences", []):
                        # Only process sequences that start from this root
                        if path and path[0] == r_uuid:
                            root_node.add_child_with_params(path, self.operation_sequences)

            forest[r_uuid] = root_node

        return forest
         