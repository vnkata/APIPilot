"""
Value selectors for constraint validation.

Supports:
- JSONPath selectors for response body
- Request reference selectors
- Response reference selectors
"""

from typing import Any, List, Optional, Dict
from dataclasses import dataclass
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from api_testing.constraint.ir.core import SelectorModel
from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SelectorMatch:
    """Result of selector evaluation."""

    value: Any
    path: str


class SelectorEngine:
    """Engine for evaluating selectors against request/response data."""

    def __init__(self):
        """Initialize selector engine."""
        self._jsonpath_cache: Dict[str, Any] = {}

    def select(
        self,
        selector: SelectorModel,
        response_body: Optional[Any] = None,
        request_ctx: Optional[Dict] = None,
        response_ctx: Optional[Dict] = None,
    ) -> List[SelectorMatch]:
        """Evaluate selector and return matches.

        Args:
            selector: SelectorModel to evaluate
            response_body: Response body data
            request_ctx: Request context (path, query, header, body)
            response_ctx: Response context (status, header, body)

        Returns:
            List of SelectorMatch objects
        """
        if selector.kind == "jsonpath":
            return self._select_jsonpath(
                selector,
                response_body or response_ctx.get("body") if response_ctx else {},
            )
        elif selector.kind == "request_ref":
            return self._select_request_ref(selector, request_ctx or {})
        elif selector.kind == "response_ref":
            return self._select_response_ref(selector, response_ctx or {})
        else:
            logger.warning(f"Unknown selector kind: {selector.kind}")
            return []

    def _select_jsonpath(
        self,
        selector: SelectorModel,
        data: Any,
    ) -> List[SelectorMatch]:
        """Select values using JSONPath.

        Args:
            selector: Selector with JSONPath expression
            data: JSON data to query

        Returns:
            List of matches
        """
        try:
            # Cache compiled JSONPath expressions
            expr = selector.expr
            if expr not in self._jsonpath_cache:
                self._jsonpath_cache[expr] = jsonpath_parse(expr)

            jsonpath_expr = self._jsonpath_cache[expr]

            # Execute JSONPath query
            matches = jsonpath_expr.find(data)

            results = []
            for match in matches:
                results.append(
                    SelectorMatch(
                        value=match.value,
                        path=str(match.full_path),
                    )
                )

            # Apply mode filter
            if selector.mode == "first" and results:
                return [results[0]]
            elif selector.mode == "any" and results:
                # For "any" mode, we still return all matches but engine will treat differently
                pass

            return results

        except JsonPathParserError as e:
            logger.error(f"Invalid JSONPath expression: {selector.expr}", error=str(e))
            return []
        except Exception as e:
            logger.error(
                "Error executing JSONPath",
                expr=selector.expr,
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    def _select_request_ref(
        self,
        selector: SelectorModel,
        request_ctx: Dict,
    ) -> List[SelectorMatch]:
        """Select value from request context.

        Supports references like:
        - req.path.paramName
        - req.query.paramName
        - req.header.headerName
        - req.body#/path/to/field

        Args:
            selector: Selector with request reference
            request_ctx: Request context dictionary

        Returns:
            List of matches
        """
        try:
            ref = selector.expr

            if ref.startswith("req.path."):
                param_name = ref[len("req.path.") :]
                value = request_ctx.get("path", {}).get(param_name)
            elif ref.startswith("req.query."):
                param_name = ref[len("req.query.") :]
                value = request_ctx.get("query", {}).get(param_name)
            elif ref.startswith("req.header."):
                header_name = ref[len("req.header.") :]
                value = request_ctx.get("header", {}).get(header_name)
            elif ref.startswith("req.body#/"):
                # Use JSONPath for body references
                json_path = "$." + ref[len("req.body#/") :].replace("/", ".")
                body = request_ctx.get("body", {})
                return self._select_jsonpath(
                    SelectorModel(kind="jsonpath", expr=json_path, mode=selector.mode),
                    body,
                )
            else:
                logger.warning(f"Invalid request reference: {ref}")
                return []

            if value is not None:
                return [SelectorMatch(value=value, path=ref)]
            return []

        except Exception as e:
            logger.error(
                "Error selecting request reference",
                ref=selector.expr,
                error=str(e),
            )
            return []

    def _select_response_ref(
        self,
        selector: SelectorModel,
        response_ctx: Dict,
    ) -> List[SelectorMatch]:
        """Select value from response context.

        Supports references like:
        - resp.status
        - resp.header.headerName
        - resp.body#/path/to/field

        Args:
            selector: Selector with response reference
            response_ctx: Response context dictionary

        Returns:
            List of matches
        """
        try:
            ref = selector.expr

            if ref == "resp.status":
                value = response_ctx.get("status")
            elif ref.startswith("resp.header."):
                header_name = ref[len("resp.header.") :]
                value = response_ctx.get("header", {}).get(header_name)
            elif ref.startswith("resp.body#/"):
                # Use JSONPath for body references
                json_path = "$." + ref[len("resp.body#/") :].replace("/", ".")
                body = response_ctx.get("body", {})
                return self._select_jsonpath(
                    SelectorModel(kind="jsonpath", expr=json_path, mode=selector.mode),
                    body,
                )
            else:
                logger.warning(f"Invalid response reference: {ref}")
                return []

            if value is not None:
                return [SelectorMatch(value=value, path=ref)]
            return []

        except Exception as e:
            logger.error(
                "Error selecting response reference",
                ref=selector.expr,
                error=str(e),
            )
            return []


__all__ = ["SelectorEngine", "SelectorMatch"]
