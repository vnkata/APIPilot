from pydantic import BaseModel
from typing import Set, Dict, Any


class ParametersPool(BaseModel):
  groups: Dict[str, Dict[str, Set[Any]]] = {}
  alias_map: Dict[str, str] = {}
  
  def __init__(self, **data):
    super().__init__(**data)
    self.groups = {}
    self.alias_map = {}
    
  def add_group(self, canonical_key: str, aliases=None, values=None):
    aliases = set(aliases or [])
    values = set(values or [])
    self.groups[canonical_key] = {"aliases": aliases, "values": values}
    for k in aliases | {canonical_key}:
        self.alias_map[k] = canonical_key

  def add_value(self, key: str, value: Any):
    canonical = self.get_canonical_key(key)
    if canonical:
        self.groups[canonical]["values"].add(value)
    else:
        # Nếu chưa tồn tại nhóm, tạo mới
        self.add_group(key, aliases=set(), values={value})
  def get_canonical_key(self, key: str):
    return self.alias_map.get(key)
  def get_values(self, key: str):
    canonical = self.get_canonical_key(key)
    if canonical:
        return self.groups[canonical]["values"]
    return set()
  def merge_aliases(self, key1: str, key2: str):
    c1, c2 = self.get_canonical_key(key1), self.get_canonical_key(key2)
    if not c1 or not c2 or c1 == c2:
        return
    # Gộp alias & value
    self.groups[c1]["aliases"] |= self.groups[c2]["aliases"] | {c2}
    self.groups[c1]["values"] |= self.groups[c2]["values"]
    # Cập nhật alias_map
    for k in self.groups[c2]["aliases"] | {c2}:
        self.alias_map[k] = c1
    del self.groups[c2]

    def __repr__(self):
        return f"ParametersPool(groups={self.groups})"
