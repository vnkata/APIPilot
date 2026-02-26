from collections import defaultdict
import copy
import json

def extract_context(data, xref_map, prefix=""):
    """
    Duyệt đệ quy JSON và nhóm context theo xrefs.
    - Gộp field cùng prefix (holidays.provinces.*)
    - Nếu prefix con (holidays.provinces.nextProvince.*) → tách entity riêng
    - Ưu tiên cấp sâu hơn (inner-most first)
    - Hash record để loại trùng
    """
    grouped = defaultdict(list)
    seen = defaultdict(set)  # {xref: {record_hash}}
    if isinstance(data, list):
        for item in data:
            sub_group = extract_context(item, xref_map, prefix)
            for xref, vals in sub_group.items():
                for rec in vals:
                    h = json.dumps(rec, sort_keys=True)
                    if h not in seen[xref]:
                        grouped[xref].append(rec)
                        seen[xref].add(h)
        return grouped
    if not isinstance(data, dict):
        return grouped
    # --- B1: duyệt sâu trước ---
    for key, val in data.items():
        new_prefix = f"{prefix + '.' + key if prefix else key}"
        sub_group = extract_context(val, xref_map, new_prefix)
        for xref, vals in sub_group.items():
            for rec in vals:
                h = json.dumps(rec, sort_keys=True)
                if h not in seen[xref]:
                    grouped[xref].append(rec)
                    seen[xref].add(h)
    # --- B2: gom field cùng cấp prefix hiện tại (bỏ prefix con) ---
    fields_by_xref = defaultdict(dict)
    for path, xref in xref_map.items():
        parent = ".".join(path.split(".")[:-1])
        if parent == prefix:
            field = path.split(".")[-1]
            if field in data:
                fields_by_xref[xref][field] = data[field]
    # --- B3: thêm record nếu chưa có ---
    for xref, record in fields_by_xref.items():
        if record:
            h = json.dumps(record, sort_keys=True)
            if h not in seen[xref]:
                grouped[xref].append(record)
                seen[xref].add(h)
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
    
    def __init__(self):
        self.contexts = {}  # { entity_name: [ {prop: value, ...}, ... ] }
        self.cache = {}

    def set_cache(self, cache):
        self.cache =  cache
    
    def clear_cache(self):
        self.cache =  {}
    def update_with_responses(self, responses, producer_properties):
        for response in responses:
            try : 
                response = json.loads(response)
                context = extract_context(response, producer_properties)
                for entity, record in context.items():
                    self.produce(entity, record)
            except:
                return
            
    def produce(self, entity_name, items):
        """
        Add contextual data to the memory.

        Args:
            entity_name (str): The entity name (e.g., "user").
            items (dict | list[dict]): One or multiple records to store.
        """
        if not isinstance(items, list):
            items = [items]

        self.contexts.setdefault(entity_name, [])
        existing = {str(x) for x in self.contexts[entity_name]}

        for item in items:
            if str(item) not in existing:
                self.contexts[entity_name].append(item)
                existing.add(str(item))

    def consume(self, entity_name, **filters):
        """
        Retrieve contextual data for an entity with optional filters.

        Example:
            memory.consume("user", group="A")

        Args:
            entity_name (str): The entity name.
            **filters: Key-value conditions to filter items.

        Returns:
            list[dict]: Filtered matching items.
        """
        items = self.contexts.get(entity_name, [])
        if not filters:
            return items
        return [i for i in items if all(i.get(k) == v for k, v in filters.items())]

    def values(self, entity_name, key):
        """
        Get a list of specific attribute values within a context.

        Example:
            memory.values("user", "id")

        Args:
            entity_name (str): The entity name.
            key (str): The property name.

        Returns:
            list: All values for the specified key.
        """
        return [i[key] for i in self.contexts.get(entity_name, []) if key in i]

    def copy(self):
        """
        Create a deep copy of the contextual memory.

        Returns:
            ContextualMemory: A fully independent copy.
        """
        new_memory = ContextualMemory()
        new_memory.contexts = copy.deepcopy(self.contexts)
        return new_memory

    def __repr__(self):
        return f"ContextualMemory({list(self.contexts.keys())})"