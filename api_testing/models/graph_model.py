
"""
Graph Models for API Testing

This module defines graph structures for modeling API operation dependencies
and relationships in API testing scenarios.
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from api_testing.models.specification_model import (
    ItemProperties,
    OperationProperties,
    ParameterProperties,
    ResponseProperties
)
from api_testing.utils import to_dict_helper


@dataclass
class OperationNode(OperationProperties):
    """
    Node representing an API operation in the operation graph.

    Extends OperationProperties with graph-specific attributes like
    in-degree and out-degree for graph analysis.
    """
    in_degree: int = 0
    out_degree: int = 0

    def __post_init__(self):
        """Validate node after initialization."""
        if self.in_degree < 0:
            raise ValueError("in_degree cannot be negative")
        if self.out_degree < 0:
            raise ValueError("out_degree cannot be negative")

    def increment_in_degree(self) -> None:
        """Increment the in-degree counter."""
        self.in_degree += 1

    def increment_out_degree(self) -> None:
        """Increment the out-degree counter."""
        self.out_degree += 1

    def decrement_in_degree(self) -> None:
        """Decrement the in-degree counter."""
        if self.in_degree > 0:
            self.in_degree -= 1

    def decrement_out_degree(self) -> None:
        """Decrement the out-degree counter."""
        if self.out_degree > 0:
            self.out_degree -= 1

    def degree(self) -> int:
        """
        Get the total degree of the node.

        Returns:
            Sum of in-degree and out-degree
        """
        return self.in_degree + self.out_degree

    def is_isolated(self) -> bool:
        """
        Check if the node is isolated (no connections).

        Returns:
            True if both in-degree and out-degree are 0
        """
        return self.in_degree == 0 and self.out_degree == 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the node to a dictionary.

        Returns:
            Dictionary representation of the node
        """
        result = super().to_dict() if hasattr(super(), 'to_dict') else asdict(self)
        return result

    def __repr__(self) -> str:
        """Detailed string representation of the operation node."""
        return (f"OperationNode(uuid='{self.uuid}', method='{self.http_method}', "
                f"endpoint='{self.endpoint_path}', in_degree={self.in_degree}, "
                f"out_degree={self.out_degree})")

    def __str__(self) -> str:
        """Simple string representation."""
        return f"OperationNode({self.uuid})"


@dataclass
class SimilarityValue:
    """
    Represents similarity between two parameter values.

    Used to track relationships between parameters across different operations
    in the API testing graph.
    """
    value1: str = ""
    value2: str = ""
    in_value: str = ""

    def __post_init__(self):
        """Validate similarity value after initialization."""
        if not isinstance(self.value1, str):
            raise ValueError("value1 must be a string")
        if not isinstance(self.value2, str):
            raise ValueError("value2 must be a string")
        if not isinstance(self.in_value, str):
            raise ValueError("in_value must be a string")

    def is_valid(self) -> bool:
        """
        Check if the similarity value is valid.

        Returns:
            True if all values are non-empty strings
        """
        return bool(self.value1 and self.value2 and self.in_value)

    def matches(self, other: "SimilarityValue") -> bool:
        """
        Check if this similarity value matches another.

        Args:
            other: Another SimilarityValue to compare with

        Returns:
            True if all corresponding values match
        """
        return (self.value1 == other.value1 and
                self.value2 == other.value2 and
                self.in_value == other.in_value)

    def to_dict(self) -> Dict[str, str]:
        """
        Convert the similarity value to a dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "SimilarityValue":
        """
        Create a SimilarityValue from a dictionary.

        Args:
            data: Dictionary containing similarity data

        Returns:
            SimilarityValue instance

        Raises:
            ValueError: If data is invalid
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        try:
            return cls(
                value1=data.get("value1", ""),
                value2=data.get("value2", ""),
                in_value=data.get("in_value", "")
            )
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid similarity data: {e}") from e

    def __str__(self) -> str:
        """String representation of the similarity value."""
        return f"SimilarityValue({self.value1} -> {self.value2} via {self.in_value})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"SimilarityValue(value1='{self.value1}', value2='{self.value2}', "
                f"in_value='{self.in_value}')")


class OperationEdge:
    """
    Edge representing a relationship between two operation nodes.

    Connects operations that have parameter dependencies or relationships,
    with associated similarity information.
    """

    def __init__(
        self,
        from_node: OperationNode,
        to_node: OperationNode,
        similar_parameters: Optional[List[SimilarityValue]] = None
    ):
        """
        Initialize an operation edge.

        Args:
            from_node: Source operation node
            to_node: Target operation node
            similar_parameters: List of parameter similarities between operations

        Raises:
            ValueError: If nodes are invalid
        """
        # if not isinstance(from_node, OperationNode):
        #     raise ValueError("from_node must be an OperationNode")
        # if not isinstance(to_node, OperationNode):
        #     raise ValueError("to_node must be an OperationNode")

        self.from_node = from_node
        self.to_node = to_node
        self.similar_parameters = similar_parameters or []

        # Validate similar_parameters
        if not isinstance(self.similar_parameters, list):
            raise ValueError("similar_parameters must be a list")

        for param in self.similar_parameters:
            if not isinstance(param, SimilarityValue):
                raise ValueError("All similar_parameters must be SimilarityValue instances")

    def add_similarity(self, similarity: SimilarityValue) -> None:
        """
        Add a similarity parameter to the edge.

        Args:
            similarity: SimilarityValue to add

        Raises:
            ValueError: If similarity is invalid
        """
        if not isinstance(similarity, SimilarityValue):
            raise ValueError("similarity must be a SimilarityValue instance")
        self.similar_parameters.append(similarity)

    def remove_similarity(self, similarity: SimilarityValue) -> bool:
        """
        Remove a similarity parameter from the edge.

        Args:
            similarity: SimilarityValue to remove

        Returns:
            True if similarity was found and removed, False otherwise
        """
        try:
            self.similar_parameters.remove(similarity)
            return True
        except ValueError:
            return False

    def has_similarities(self) -> bool:
        """
        Check if the edge has any similarity parameters.

        Returns:
            True if there are similarity parameters, False otherwise
        """
        return len(self.similar_parameters) > 0

    def get_similarity_count(self) -> int:
        """
        Get the number of similarity parameters.

        Returns:
            Number of similarities
        """
        return len(self.similar_parameters)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the edge to a dictionary.

        Returns:
            Dictionary representation of the edge
        """
        return {
            "from_node": self.from_node.uuid,
            "to_node": self.to_node.uuid,
            "similar_parameters": [
                param.to_dict() for param in self.similar_parameters
            ]
        }

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        nodes: Dict[str, OperationNode]
    ) -> "OperationEdge":
        """
        Create an OperationEdge from a dictionary.

        Args:
            data: Dictionary containing edge data
            nodes: Dictionary mapping node UUIDs to OperationNode instances

        Returns:
            OperationEdge instance

        Raises:
            ValueError: If data is invalid or nodes are missing
        """
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary")

        try:
            from_uuid = data["from_node"]
            to_uuid = data["to_node"]

            from_node = nodes.get(from_uuid)
            to_node = nodes.get(to_uuid)

            if not from_node:
                raise ValueError(f"Source node {from_uuid} not found")
            if not to_node:
                raise ValueError(f"Target node {to_uuid} not found")

            similar_params_data = data.get("similar_parameters", [])
            similar_parameters = [
                SimilarityValue.from_dict(param_data)
                for param_data in similar_params_data
            ]

            return cls(from_node, to_node, similar_parameters)

        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid edge data: {e}") from e

    def __repr__(self) -> str:
        """Detailed string representation of the operation edge."""
        return (f"OperationEdge(from='{self.from_node.uuid}', to='{self.to_node.uuid}', "
                f"similarities={len(self.similar_parameters)})")

    def __str__(self) -> str:
        """Simple string representation."""
        return f"OperationEdge({self.from_node.uuid} -> {self.to_node.uuid})"

    def __eq__(self, other: object) -> bool:
        """Check equality with another edge."""
        if not isinstance(other, OperationEdge):
            return False
        return (self.from_node == other.from_node and
                self.to_node == other.to_node)

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash((self.from_node.uuid, self.to_node.uuid))
