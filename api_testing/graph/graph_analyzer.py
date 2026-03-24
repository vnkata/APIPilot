
import collections
import json
import os
from heapq import nlargest
import heapq
from functools import lru_cache
import json

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
                        current_params.setdefault(target_p, []).append(src)

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
                        child_params.setdefault(target_p, []).append(src)


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
            
    def remove_matching_params(self, target_endpoint, target_param, source_endpoint, source_param):
        """
        Remove incorrect dependency mapping from operation_sequences.

        (source_endpoint.source_param) -> (target_endpoint.target_param)
        """

        if target_endpoint not in self.operation_sequences:
            return

        new_candidates = []

        for candidate in self.operation_sequences[target_endpoint]:

            params = candidate.get("params", {})
            if target_param not in params:
                new_candidates.append(candidate)
                continue

            # filter source mapping
            filtered_sources = [
                s for s in params[target_param]
                if not (
                    s.get("source_param") == source_param
                    and s.get("source_endpoint") == source_endpoint
                )
            ]

            # nếu vẫn còn source hợp lệ → giữ lại
            if filtered_sources:
                params[target_param] = filtered_sources
                new_candidates.append(candidate)

            else:
                # remove param hoàn toàn
                params.pop(target_param, None)

                # nếu candidate vẫn còn params thì giữ
                if params:
                    candidate["params"] = params
                    new_candidates.append(candidate)

        self.operation_sequences[target_endpoint] = new_candidates
        self.save_to_cache()


    def __operation_sequences(self, target, adjacency_map, visited=None, param_mapping=None, top_k=2, max_depth=6,depth=0):
        visited = visited or set()
        base_param_mapping = param_mapping or {}
        target_uuid = target.uuid
        if depth >= max_depth:
            return [{
                "type": "max-depth",
                "combined_sequences": [[target_uuid]],
                "params": base_param_mapping,
                "score": 999
            }]

        # -------------------------------
        # Caching key builder
        # -------------------------------
        # param_mapping có thể chứa các object không hashable, nên serialize nhẹ
        def make_cache_key(node_uuid, params, visited_nodes):
            try:
                serialized_params = json.dumps(params, sort_keys=True)
            except Exception:
                # fallback nếu params chứa object không serialize được
                serialized_params = str(params)
            return (node_uuid, serialized_params, tuple(sorted(visited_nodes)))

        # Tạo cache nếu chưa có (chỉ tạo 1 lần trong vòng đời object)
        if not hasattr(self, "_op_seq_cache"):
            self._op_seq_cache = {}

        cache_key = make_cache_key(target_uuid, base_param_mapping, visited)
        if cache_key in self._op_seq_cache:
            return self._op_seq_cache[cache_key]

        # -------------------------------
        # Ngăn đệ quy vô hạn
        # -------------------------------
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
            mapping = {}
            for e in self_edges:
                for sp in e.similar_parameters:
                    tgt_param = str(sp.value2)
                    src_param = str(sp.value1)
                    mapping.setdefault(tgt_param, []).append({
                        "source_param": src_param,
                        "source_endpoint": target_uuid
                    })

            all_results.append({
                "type": "self-contained",
                "combined_sequences": [[target_uuid]],
                "params": {**base_param_mapping, **mapping},
                "score": 0
            })

        # === PHASE 2: CANDIDATE RANKING ===
        candidates = []
        target_method = getattr(target, "method", "").lower() # Giả sử target có attribute method
        target_path = getattr(target, "path", "")            # Giả sử target có attribute path
        for edge in edges:
            from_node = edge.from_node
            if from_node.uuid == target_uuid:
                continue
            from_method = getattr(from_node, "method", "").lower()
            from_path = getattr(from_node, "path", "")
            provided_params = {sp.value2 for sp in edge.similar_parameters}
            # === LOGIC ĐẶC BIỆT: PUT TÌM POST TRÊN CÙNG ENDPOINT ===
            method_priority = 0
            # Nếu cùng đường dẫn và target là PUT/PATCH, ưu tiên cực cao cho POST
            if from_path == target_path:
                if target_method in ["put", "patch"] and from_method == "post":
                    method_priority = 10  # Trọng số ưu tiên cao nhất
                elif target_method == "delete" and from_method in ["post", "get"]:
                    method_priority = 5   # Ưu tiên tìm để xóa

            if current_target_path_params.intersection(provided_params) or not current_target_path_params:
                is_evolving = 1 if len(provided_params) >= len(current_target_path_params) else 0
                richness = len(provided_params)

                candidates.append({
                    "edge": edge,
                    "from_node": from_node,
                    "priority": (method_priority, is_evolving, richness)
                })


        candidates.sort(key=lambda x: x["priority"], reverse=True)
        MAX_CANDIDATES = max(top_k * 2, 20)
        candidates = candidates[:MAX_CANDIDATES]
        # === PHASE 3: SEQUENCE BUILDING ===
        for candidate in candidates:
            edge = candidate["edge"]
            from_node = candidate["from_node"]
            mapped_on_edge = {}

            for sp in edge.similar_parameters:
                mapped_on_edge.setdefault(sp.value2, []).append(sp.value1)

            if current_target_path_params.issubset(set(mapped_on_edge.keys())):
                from_name = getattr(from_node, "name", from_node.uuid)
                edge_mapping = {}
                for t_p, s_p in mapped_on_edge.items():
                    if t_p in current_target_path_params:
                        for s in s_p:
                            edge_mapping.setdefault(t_p, []).append({
                                "source_param": s,
                                "source_endpoint": from_name
                            })
                combined_mapping = {**base_param_mapping, **edge_mapping}
                from_req_params = getattr(from_node, "required_parameters", [])

                if len(from_req_params) > 0:
                    upstream_results = self.__operation_sequences(
                        from_node, adjacency_map, current_visited, combined_mapping , 
                        top_k,
                        max_depth,
                        depth + 1   # 👈 tăng depth
                    )

                    for upstream in upstream_results:
                        if upstream["type"] == "unresolved":
                            continue
                        for seq in upstream["combined_sequences"]:
                            all_results.append({
                                "type": "recursive-path",
                                "combined_sequences": [seq + [target_uuid]],
                                "params": upstream["params"],
                                "score": len(seq) + 1
                            })
                else:
                    if len(from_req_params) == 0 and combined_mapping:
                        all_results.append({
                            "type": "direct-path",
                            "combined_sequences": [[from_node.uuid, target_uuid]],
                            "params": combined_mapping,
                            "score": 2
                        })

        # === PHASE 4: FINAL OPTIMIZATION ===
        if all_results:
            valid_paths = [r for r in all_results if r["type"] != "unresolved"]
            if valid_paths:
                valid_paths.sort(key=lambda x: x["score"])
                result = valid_paths[:top_k]
                self._op_seq_cache[cache_key] = result
                return result

        result = [{"type": "unresolved", "combined_sequences": [[target_uuid]], "params": base_param_mapping, "score": 999}]
        self._op_seq_cache[cache_key] = result
        return result
    
    def build_sequences(self, top_k=4):
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
        
        # --- 2️⃣ Thêm các node unresolved ---
        for uuid, candidates in self.operation_sequences.items():
            if any(c.get("type") == "unresolved" for c in candidates):
                root_uuids.append(uuid)
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
            # ⚠️ Nếu là unresolved root → đảm bảo có ít nhất self-node
            if not root_node.children:
                root_node.add_child_with_params(
                    [r_uuid], self.operation_sequences
                )


            forest[r_uuid] = root_node
        

        return forest
         