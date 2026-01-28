"""
Request-response constraint extractors.

This module provides extractors for detecting constraints that span
request parameters and response data.
"""

from api_testing.constraint.ir.extractors.request_response.analyzer import (
    RequestResponseAnalyzer,
)

__all__ = ["RequestResponseAnalyzer"]
