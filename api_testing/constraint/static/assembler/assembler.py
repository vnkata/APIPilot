"""Constraint assembler for building unified constraint structures.

Assembles unified constraint data by combining response property constraints
and request-response constraints into a structured format.
"""

from api_testing.constraint.static.assembler.classifier import BodyParamClassifier
from api_testing.constraint.static.assembler.models import (
    ResponsePropertyConstraint,
    UnifiedConstraints,
)
from api_testing.models.specification_model import (
    OperationProperties,
    ParameterProperties,
)
from common.logger import get_logger

logger = get_logger(__name__)


class ConstraintAssembler:
    """Assembles unified constraint structures from extracted constraint data.

    Combines response property constraints and request-response constraints
    into a unified format with body-level and detail-level organization.

    Attributes:
        classifier: BodyParamClassifier for categorizing parameters
    """

    def __init__(self, classifier: BodyParamClassifier | None = None) -> None:
        """Initialize ConstraintAssembler.

        Args:
            classifier: Optional custom classifier. If None, uses default.
        """
        self.classifier = classifier or BodyParamClassifier()

    def assemble_operation_constraints(
        self,
        operation: OperationProperties,
        response_properties_constraints: dict[str, str],
        request_response_constraints: dict[str, dict[str, str]],
    ) -> UnifiedConstraints:
        """Assemble unified constraints for a single operation.

        Args:
            operation: Full operation properties including parameters
            response_properties_constraints: Dict mapping response property path
                to constraint description (e.g., {"holidays.date": "..."})
            request_response_constraints: Dict mapping request param to dict of
                response properties it affects (e.g., {"year": {"holidays.date": "..."}})

        Returns:
            UnifiedConstraints with body and detail sections

        Example:
            >>> assembler = ConstraintAssembler()
            >>> constraints = assembler.assemble_operation_constraints(
            ...     operation=operation_props,
            ...     response_properties_constraints={"holidays.date": "ISO date..."},
            ...     request_response_constraints={"year": {"holidays.date": "Filters..."}}
            ... )
        """
        unified = UnifiedConstraints()
        operation_id = (
            operation.operation_id
            or f"{operation.http_method}-{operation.endpoint_path}"
        )
        parameters = operation.parameters

        # If no parameters, return structure with all response properties in detail
        if not parameters:
            unified.detail = self._build_detail_section(
                operation=operation,
                response_properties_constraints=response_properties_constraints,
                request_response_constraints={},
            )
            return unified

        # Classify parameters into body and detail
        body_params, detail_params = self.classifier.classify_parameters(parameters)

        logger.debug(
            f"Classified parameters for {operation_id}: "
            f"body={list(body_params.keys())}, detail={list(detail_params.keys())}"
        )

        # Build body section from body-level parameters
        unified.body = self._build_body_section(
            body_params=body_params,
            request_response_constraints=request_response_constraints,
        )

        # Build detail section from detail-level parameters
        unified.detail = self._build_detail_section(
            operation=operation,
            response_properties_constraints=response_properties_constraints,
            request_response_constraints=request_response_constraints,
            detail_param_names=set(detail_params.keys()),
        )

        return unified

    def _build_body_section(
        self,
        body_params: dict[str, ParameterProperties],
        request_response_constraints: dict[str, dict[str, str]],
    ) -> dict[str, str]:
        """Build body section with simple string descriptions.

        Args:
            body_params: Parameters classified as body-level
            request_response_constraints: Request-response constraint data

        Returns:
            Dict mapping param name to description string
        """
        body_section: dict[str, str] = {}

        for param_name, param_props in body_params.items():
            # Use parameter description if available
            description = param_props.description or ""

            # If param has request-response constraints, aggregate them
            if param_name in request_response_constraints:
                affected_fields = request_response_constraints[param_name]
                if affected_fields:
                    # Append info about affected fields
                    field_count = len(affected_fields)
                    if description:
                        description += f" (affects {field_count} response field(s))"
                    else:
                        description = f"Affects {field_count} response field(s)"

            # Fallback if still no description
            if not description:
                category = self.classifier.get_param_category_hint(param_name)
                if category:
                    description = f"Parameter for {category}"
                else:
                    description = f"Request parameter '{param_name}'"

            body_section[param_name] = description

        return body_section

    @staticmethod
    def _build_detail_section(
        operation: OperationProperties,
        response_properties_constraints: dict[str, str],
        request_response_constraints: dict[str, dict[str, str]],
        detail_param_names: set | None = None,
    ) -> dict[str, ResponsePropertyConstraint]:
        """Build detail section with response-centric view and enhanced descriptions.

        For each response property, includes all request parameters that
        affect it (filtered to detail-level params only if detail_param_names provided).
        Enhanced descriptions include parameter schema info from to_human_readable().

        Args:
            operation: Full operation with parameters
            response_properties_constraints: Response property descriptions
            request_response_constraints: Request-response mappings
            detail_param_names: Optional set of param names to include.
                If None, includes all params (for operations without params)

        Returns:
            Dict mapping response property path to ResponsePropertyConstraint
        """
        detail_section: dict[str, ResponsePropertyConstraint] = {}
        operation_id = (
            operation.operation_id
            or f"{operation.http_method}-{operation.endpoint_path}"
        )

        # Cache parameter descriptions to avoid redundant to_human_readable() calls
        param_descriptions_cache: dict[str, str] = {}

        def get_param_description(parameter_name: str) -> str:
            """Get cached parameter description or generate it."""
            if parameter_name in param_descriptions_cache:
                return param_descriptions_cache[parameter_name]

            # Get parameter properties
            if operation.parameters and parameter_name in operation.parameters:
                param = operation.parameters[parameter_name]
                param_info = param.to_human_readable()
            else:
                # Fallback if parameter not found (defensive)
                logger.debug(
                    f"Parameter '{parameter_name}' not found in operation {operation_id}, "
                    f"using name only"
                )
                param_info = parameter_name

            param_descriptions_cache[parameter_name] = param_info
            return param_info

        # Build reverse mapping: response_property -> dict of param constraints
        property_to_params: dict[str, dict[str, str]] = {}

        for param_name, affected_properties in request_response_constraints.items():
            # Filter to detail-level params only (if detail_param_names provided)
            if detail_param_names is not None and param_name not in detail_param_names:
                continue

            # Get parameter description (cached)
            param_desc = get_param_description(param_name)

            for prop_path, constraint_desc in affected_properties.items():
                if prop_path not in property_to_params:
                    property_to_params[prop_path] = {}

                # Build enhanced description: [{param}: {param_info}] {constraint}
                enhanced_description = f"[{param_name}: {param_desc}] {constraint_desc}"
                property_to_params[prop_path][param_name] = enhanced_description

        # Build detail section for ALL response properties
        for prop_path, prop_description in response_properties_constraints.items():
            request_dict = property_to_params.get(prop_path, {})

            detail_section[prop_path] = ResponsePropertyConstraint(
                request=request_dict, response_property=prop_description
            )

        return detail_section


__all__ = ["ConstraintAssembler"]
