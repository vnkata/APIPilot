
from dataclasses import dataclass, fields

from api_testing.models.specification_model import ItemProperties, OperationProperties, ParameterProperties, ResponseProperties
from api_testing.utils import to_dict_helper


@dataclass
class OperationNode(OperationProperties):
    in_degree: int = 0
    out_degree: int = 0
     
    def __repr__(self):
        return f"OperationNode({self.uuid})"
    

@dataclass
class OperationEdge:
    def __init__(self, from_node, to_node, similar_parameters):
        self.from_node = from_node
        self.to_node = to_node
        self.similar_parameters = similar_parameters

    def __repr__(self):
        return f"OperationEdge({self.from_node.uuid} -> {self.to_node.uuid})"

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
