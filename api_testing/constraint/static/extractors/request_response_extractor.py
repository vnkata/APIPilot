"""Request-response constraint extractor.

Extracts relationships between request parameters and response properties
for API operations.
"""

import os
from typing import Dict, List, Optional, Tuple

from api_testing.dataset import SpecificationParser
from api_testing.models.specification_model import OperationProperties
from api_testing.prompts.request_response_constraint.miner import (
    RequestResponseConstraintMiner,
)
from api_testing.utils import flatten_json_schema
from common.logger import Logger

from api_testing.constraint.static.extractors.base_extractor import BaseStaticExtractor, handle_extraction_error
from api_testing.constraint.static.extractors.models import RequestResponseConstraints


class RequestResponseExtractor(
    BaseStaticExtractor[OperationProperties, RequestResponseConstraints]
):
    """Extracts request-response constraint relationships from API operations.

    Processes operations to identify which request parameters constrain
    which response properties using LLM validation.

    Example:
        >>> extractor = RequestResponseExtractor(
        ...     spec_parser=parser,
        ...     cache_dir="./cache",
        ...     batch_size=10
        ... )
        >>> result = await extractor.extract_all(operations_list)
        >>> for constraint in result.successful:
        ...     print(f"{constraint.operation_uuid}: {constraint.constraints}")
    """

    def __init__(
        self,
        spec_parser: SpecificationParser,
        cache_dir: str,
        batch_size: int = 10,
        logger: Optional[Logger] = None,
    ) -> None:
        """Initialize RequestResponseExtractor.

        Args:
            spec_parser: Parser containing parsed API specification
            cache_dir: Directory path for caching extracted constraints
            batch_size: Number of operations to process in parallel (default: 10)
            logger: Logger instance (shared from parent)

        Raises:
            ValueError: If spec_parser or cache_dir is None
        """
        if spec_parser is None:
            raise ValueError("spec_parser is required")

        super().__init__(cache_dir=cache_dir, batch_size=batch_size, logger=logger)

        self.spec_parser = spec_parser
        self.request_response_miner = RequestResponseConstraintMiner()

    @property
    def cache_file(self) -> str:
        """Path to request-response constraints cache file."""
        return os.path.join(self.cache_dir, "_temp_request_response_constraints.json")

    @handle_extraction_error(return_value=(None, None))
    async def _extract_single(
        self, operation: OperationProperties
    ) -> Tuple[str, Optional[RequestResponseConstraints]]:
        """Extract request-response constraints for a single operation.

        Args:
            operation: OperationProperties to extract constraints from

        Returns:
            Tuple of (operation_uuid, RequestResponseConstraints or None if failed)
        """
        operation_uuid = operation.uuid
        self.logger.debug(f"Processing operation: {operation_uuid}")

        # Extract request parameters
        request_params: List[str] = []
        if operation.parameters:
            for param_name, param_props in operation.parameters.items():
                if param_props.schema is None:
                    self.logger.warning(
                        f"Parameter '{param_name}' in operation '{operation_uuid}' "
                        f"has no schema. Skipping constraint extraction."
                    )
                    continue

                param_desc = param_props.to_human_readable()
                request_params.append(f"- {param_name}: {param_desc}")

        if not request_params:
            self.logger.debug(
                f"Operation '{operation_uuid}' has no request parameters, skipping"
            )
            return operation_uuid, None

        # Extract response properties
        response_props: List[str] = []
        if operation.successful_responses:
            flattened_responses = flatten_json_schema(
                operation.successful_responses.to_dict()
            )
            response_props = [
                f"- {prop_path}: {prop_info.get('description', 'No description')}"
                for prop_path, prop_info in flattened_responses.items()
            ]

        if not response_props:
            self.logger.debug(
                f"Operation '{operation_uuid}' has no response properties, skipping"
            )
            return operation_uuid, None

        # Extract constraints using LLM
        result = await self.request_response_miner.extract_constraints(
            operation_name=operation_uuid,
            method=operation.method,
            path=operation.path,
            request_params="\n".join(request_params),
            response_properties="\n".join(response_props),
        )

        constraints = RequestResponseConstraints(
            operation_uuid=operation_uuid,
            constraints=result.constraints,
        )

        # Count total constraint pairs
        total_pairs = sum(len(resp_props) for resp_props in constraints.constraints.values())

        self.logger.debug(
            f"Extracted request-response constraints: operation={operation_uuid}, "
            f"request_params={len(constraints.constraints)}, "
            f"constraint_pairs={total_pairs}"
        )

        return operation_uuid, constraints

    def _parse_cached_items(
        self, cached_data: List[Dict]
    ) -> List[RequestResponseConstraints]:
        """Parse cached request-response constraints.

        Args:
            cached_data: List of cached constraint dictionaries

        Returns:
            List of RequestResponseConstraints instances
        """
        return [RequestResponseConstraints(**item) for item in cached_data]


__all__ = ["RequestResponseExtractor"]
