from collections import defaultdict
import copy
import json
import os
import random
import threading

def build_entity_prefix_map(xref_map):
    entity_prefix = {}

    for path, entity in xref_map.items():
        parent = ".".join(path.split(".")[:-1])

        if entity not in entity_prefix or len(parent) < len(entity_prefix[entity]):
            entity_prefix[entity] = parent

    return entity_prefix


def extract_context(data, xref_map, prefix="", base_dict=None, entity_prefix=None):

    if base_dict is None:
        base_dict = {}

    if entity_prefix is None:
        entity_prefix = build_entity_prefix_map(xref_map)

    grouped = defaultdict(list)

    # -------------------------
    # LIST
    # -------------------------
    if isinstance(data, list):
        for item in data:
            sub = extract_context(item, xref_map, prefix, base_dict, entity_prefix)
            if sub:
                for ent, vals in sub.items():
                    grouped[ent].extend(vals)
        return grouped

    if not isinstance(data, dict):
        return grouped

    # -------------------------
    # DFS children
    # -------------------------
    child_entities = []
    for key, val in data.items():

        child_prefix = f"{prefix}.{key}" if prefix else key

        sub_results = extract_context(
            val, xref_map, child_prefix, base_dict, entity_prefix
        )

        for ent, vals in sub_results.items():
            grouped[ent].extend(vals)

            if vals:
                child_entities.append({
                    "json_key": key,
                    "prefix": child_prefix,
                    "entity": ent,
                    "records": vals
                })

    # -------------------------
    # Collect entity fields
    # -------------------------
    fields_by_entity = defaultdict(dict)

    for path, entity in xref_map.items():

        parent = ".".join(path.split(".")[:-1])
        field = path.split(".")[-1]

        if parent == prefix and field in data:
            fields_by_entity[entity][field] = data[field]

    # -------------------------
    # Build records
    # -------------------------
    for entity, record in fields_by_entity.items():

        base_record = {**base_dict, **record}
        expanded = [base_record]

        for child in child_entities:

            child_entity = child["entity"]
            child_prefix = child["prefix"]

            if entity_prefix.get(child_entity) != child_prefix:
                continue

            child_attr = f"{child['json_key']}:{child_entity}"
            child_records = child["records"]

            # 🔑 kiểm tra JSON gốc
            is_array = isinstance(data.get(child["json_key"]), list)

            new_expanded = []

            for parent_rec in expanded:

                new_rec = copy.deepcopy(parent_rec)

                if is_array:
                    # luôn giữ list
                    new_rec[child_attr] = child_records

                else:
                    new_rec[child_attr] = child_records[0] if child_records else None

                new_expanded.append(new_rec)

            expanded = new_expanded

        grouped[entity].extend(expanded)

    return grouped

class ContextualMemory:
    """
    A contextual memory that stores entities and their related data.
    Structure:
        {
            "user": [ {"id": 1, "group": "A"}, {"id": 2, "group": "B"} ],
            "holiday": [ {"id": "NY", "date": "2026-01-01"} ]
        }
    """
    
    def __init__(self, cache_dir):
        self.contexts = {}  # { entity_name: [ {prop: value, ...}, ... ] }
        self.cache = {}
        self.current_uuid = None
        self.priority_resources = []
        self._lock = threading.Lock()
        self.cache_file = os.path.join(
            cache_dir, "contextual_memory.json")
        self.load_or_initialize_cache()
        
    def load_or_initialize_cache(self):
        # Check if the cache file exists
        if  os.path.exists(self.cache_file):
            with open(self.cache_file, "r") as file:
                data = json.load(file)
                self.contexts = data

    def set_current(self, current_uuid):
        self.current_uuid =  current_uuid

    def clear_current(self): 
        self.current_uuid =  None

    def set_cache(self, entity, cache):
        if cache:
            self.cache[entity] =  cache
    
    def clear_cache(self):
        self.cache =  {}

    def set_priority_resources(self, resources):
        self.priority_resources = resources
    
    def clear_priority_resources(self):
        self.priority_resources =  []

    def has(self, entry):
        return entry in self.contexts
    def update_with_responses(self, responses, producer_properties):
        for entry in responses:
            try:
                # lấy response text
                results = (
                    entry.get("response", {})
                    .get("content", {})
                    .get("text")
                )
                if not results:
                    continue
                response_json = json.loads(results)
                # path params của request
                base_dict = entry.get("request", {}).get("path_params", {})
                base_dict = {f"{key}:path": value for key, value in base_dict.items()}

                # extract entities từ response
                context = extract_context(response_json, producer_properties, base_dict=base_dict)
                if not context:
                    continue
                for entity, record in context.items():
                    for x in entity.split(","):
                        self.produce(x, record)
            except Exception as e:
                print("update_with_responses error:", e)
                continue
            
    def produce(self, entity_name, items):
        
        if not isinstance(items, list):
            items = [items]

        self.contexts.setdefault(entity_name, [])
        existing = {str(x) for x in self.contexts[entity_name]}

        for item in items:
            if str(item) not in existing:
                self.contexts[entity_name].append(item)
                existing.add(str(item))
        self.export_to_file()
        
    # def consume(self, entity_name, **filters):
    #     """
    #     Retrieve contextual data for an entity with optional filters.

    #     Example:
    #         memory.consume("user", group="A")

    #     Args:
    #         entity_name (str): The entity name.
    #         **filters: Key-value conditions to filter items.

    #     Returns:
    #         list[dict]: Filtered matching items.
    #     """
    #     items = self.contexts.get(entity_name, [])

    #     if self.current_uuid is not None:
    #         blacklist_ctx = self.contexts.get(self.current_uuid, {})
    #         blacklist_items = blacklist_ctx.get(entity_name, [])
    #     else:
    #         blacklist_items = []  
    #     def is_blacklisted(item):
    #         for b in blacklist_items:
    #             if all(item.get(k) == v for k, v in b.items()):
    #                 return True
    #         return False
        
    #     whitelist = [i for i in items if not is_blacklisted(i)]
    #     # print("Consume ", entity_name, "=> ", len(items), len(blacklist_items), len(whitelist) )
    #     if not filters:
    #         return whitelist
    #     return [i for i in whitelist if all(i.get(k) == v for k, v in filters.items())] 
    def consume_priority_resource(self, entity_name: str,priority_resource,  **filters, ):
        # --------------------------
        # 1. Filter helper
        # --------------------------
        def match(item: dict) -> bool:
            return not filters or all(item.get(k) == v for k, v in filters.items())

        # --------------------------
        # 2. Collect candidates
        # --------------------------
        results = []

        # cache
        cached = self.cache.get(entity_name)
        if cached:
            values = self.cache.get(entity_name, {})
            if values and isinstance(values, dict):
                return [values]
        # context
        for item in self.contexts.get(entity_name, []):
            if isinstance(item, dict) and match(item):
                results.append(item)

        # nested
        suffix = f":{entity_name}"

        def scan(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():

                    if k.endswith(suffix):
                        if isinstance(v, dict) and match(v):
                            results.append(v)

                        elif isinstance(v, list):
                            for e in v:
                                if isinstance(e, dict) and match(e):
                                    results.append(e)

                    if isinstance(v, (dict, list)):
                        scan(v)

            elif isinstance(obj, list):
                for x in obj:
                    scan(x)

        for parent_items in self.cache.values():
            if isinstance(parent_items, list):
                for parent in parent_items:
                    scan(parent)

        if not results:
            return []

        # --------------------------
        # 3. Scoring
        # --------------------------
        def score_item(item: dict) -> float:
            score = 0

            # 🔥 3.0 Entity-level priority
            if entity_name in priority_resource:
                score += (len(priority_resource) - priority_resource.index(entity_name)) * 10

            # 🔥 3.1 Nested resource priority
            def scan_resource(obj):
                nonlocal score

                if isinstance(obj, dict):
                    for k, v in obj.items():
                        for i, res in enumerate(priority_resource):
                            if k.endswith(f":{res}"):
                                score += (len(priority_resource) - i) * 10

                        if isinstance(v, (dict, list)):
                            scan_resource(v)

                elif isinstance(obj, list):
                    for x in obj:
                        scan_resource(x)

            scan_resource(item)

            # 🔹 3.2 Filter bonus
            score += len(filters) * 5

            # 🔹 3.3 Completeness
            score += len(item.keys()) * 0.5

            # 🔹 3.4 Depth penalty
            def calc_depth(obj, depth=0):
                if isinstance(obj, dict):
                    return max([calc_depth(v, depth + 1) for v in obj.values()] + [depth])
                if isinstance(obj, list):
                    return max([calc_depth(v, depth + 1) for v in obj] + [depth])
                return depth

            score -= calc_depth(item) * 0.3

            return score

        scored = [(item, score_item(item)) for item in results]

        # --------------------------
        # 4. Select max-score set
        # --------------------------
        max_score = max(s for _, s in scored)
        best_items = [item for item, s in scored if s ==  max_score]
        no_best_items = [item for item, s in scored if s !=  max_score]
        # --------------------------
        # 5. Stable ordering
        # --------------------------
        best_items = sorted(best_items, key=lambda x: str(x))
        no_best_items = random.sample(no_best_items, min(len(best_items), len(no_best_items)))
        return best_items + no_best_items

    def consume(self, entity_name, **filters):
        if len(self.priority_resources) > 0:
            return self.consume_priority_resource(entity_name, priority_resource=self.priority_resources, **filters)
        results = []

        if len(self.cache.keys()) > 0:
            values = self.cache.get(entity_name, {})
            if values != {}:
                if isinstance(values, dict):
                    return [values]
                return values
        # --------------------------
        # 1. direct lookup
        # --------------------------
        items = self.contexts.get(entity_name, [])

        for item in items:
            if not filters or all(item.get(k) == v for k, v in filters.items()):
                results.append(item)

        # --------------------------
        # 2. lookup nested in cache
        # --------------------------
        suffix = f":{entity_name}"
        def _scan_nested(obj, suffix, filters, results):

            if isinstance(obj, dict):

                for key, val in obj.items():

                    if key.endswith(suffix):

                        if isinstance(val, dict):
                            if not filters or all(val.get(k) == v for k, v in filters.items()):
                                results.append(val)

                        elif isinstance(val, list):
                            for elem in val:
                                if isinstance(elem, dict):
                                    if not filters or all(elem.get(k) == v for k, v in filters.items()):
                                        results.append(elem)

                    # continue scanning deeper
                    if isinstance(val, (dict, list)):
                        _scan_nested(val, suffix, filters, results)

            elif isinstance(obj, list):

                for item in obj:
                    _scan_nested(item, suffix, filters, results)
                    
        for parent_items in self.cache.values():
            for parent in parent_items:
                _scan_nested(parent, suffix, filters, results)
        
        return results
    
    def remove(self, resources):
        endpoint_ctx = self.contexts.setdefault(self.current_uuid, {})
        if not isinstance(endpoint_ctx, dict):
            endpoint_ctx = {}
            self.contexts[self.current_uuid] = endpoint_ctx
        blacklist = endpoint_ctx.setdefault("blacklist", [])
        key = json.dumps(resources, sort_keys=True)
        existing = {json.dumps(x, sort_keys=True) for x in blacklist}
        if key not in existing:
            blacklist.append(resources)
    
    def is_blacklisted(self, resources):
        endpoint_ctx = self.contexts.setdefault(self.current_uuid, {})
        if not isinstance(endpoint_ctx, dict):
            return False
        blacklist = endpoint_ctx.setdefault("blacklist", [])
        key = json.dumps(resources, sort_keys=True)
        existing = {json.dumps(x, sort_keys=True) for x in blacklist}
        if key not in existing:
            return False
        return True
    
    def in_whitelist(self, resources):
        endpoint_ctx = self.contexts.setdefault(self.current_uuid, {})
        if not isinstance(endpoint_ctx, dict):
            return False
        whitelist = endpoint_ctx.setdefault("whitelist", [])
        key = json.dumps(resources, sort_keys=True)
        existing = {json.dumps(x, sort_keys=True) for x in whitelist}
        if key not in existing:
            return False
        return True

    def add(self, resources):
        endpoint_ctx = self.contexts.setdefault(self.current_uuid, {})
        if not isinstance(endpoint_ctx, dict):
            endpoint_ctx = {}
            self.contexts[self.current_uuid] = endpoint_ctx
        whitelist = endpoint_ctx.setdefault("whitelist", [])
        key = json.dumps(resources, sort_keys=True)
        existing = {json.dumps(x, sort_keys=True) for x in whitelist}
        if key not in existing:
            whitelist.append(resources)

    def values(self, entity_name, key):
        
        return [i[key] for i in self.contexts.get(entity_name, []) if key in i]

    def copy(self):

        new_memory = ContextualMemory(cache_dir=os.path.dirname(self.cache_file) or ".")
        new_memory.contexts = copy.deepcopy(self.contexts)
        return new_memory

    def merge(self, other: 'ContextualMemory'):
        """
        Merge another ContextualMemory into this one.
        Thread-safe: acquires lock before merging.
        Skips per-node whitelists (current_uuid keys).
        """
        with self._lock:
            for entity, items in other.contexts.items():
                if entity == other.current_uuid:
                    continue
                if entity not in self.contexts:
                    self.contexts[entity] = []
                existing = {str(x) for x in self.contexts[entity]}
                for item in items:
                    if str(item) not in existing:
                        self.contexts[entity].append(item)
                        existing.add(str(item))
            self.export_to_file()

    def __repr__(self):
        return f"ContextualMemory({list(self.contexts.keys())})"
    
    def export_to_file(self):
        with open(self.cache_file, "w") as file:
            json.dump(self.contexts, file, indent=2, ensure_ascii=False)
            file.flush()