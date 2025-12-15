
from dataclasses import dataclass

from api_testing.models.specification_model import OperationProperties
from api_testing.utils import to_dict_helper


@dataclass
class OperationNode(OperationProperties):
    in_degree: int = 0
    out_degree: int = 0

    def __repr__(self):
        return f"OperationNode({self.uuid})"

    def to_dict(self):
        result = {k: to_dict_helper(
            v) for k, v in self.__dict__.items() if v is not None}
        if 'parameters' in result and self.parameters:
            result['parameters'] = {k: v.to_dict()
                                    for k, v in self.parameters.items()}
        if 'request_body' in result and self.request_body:
            result['request_body'] = {
                k: v.to_dict() for k, v in self.request_body.items()}
        return result


@dataclass
class OperationEdge:
    def __init__(self, from_node, to_node, similar_parameters):
        self.from_node = from_node
        self.to_node = to_node
        self.similar_parameters = similar_parameters

    def __repr__(self):
        return f"OperationEdge({self.from_node} -> {self.to_node})"

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
