"""
Multi-field response property extractors.

Extractors for cross-field constraints within response schemas.
"""

from api_testing.constraint.ir.extractors.response_property.multi.coverage_checker import (
    ResPropCrossFieldCoverageChecker,
)
from api_testing.constraint.ir.extractors.response_property.multi.analyzer import (
    CrossFieldResponseAnalyzer,
)

__all__ = [
    "ResPropCrossFieldCoverageChecker",
    "CrossFieldResponseAnalyzer",
]
