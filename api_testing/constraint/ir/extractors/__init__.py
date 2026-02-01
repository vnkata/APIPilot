"""
Constraint extractors for mining constraints from API specifications.

This module provides extractors for different types of constraints:
- Response property constraints (single-field and multi-field)
- Request-response constraints (parameters matching response data)
- Common utilities for matching and analysis
"""

# Response property extractors
# Common utilities
from api_testing.constraint.ir.extractors.common import (
    CandidateConstraint,
    Evidence,
)

# Prompt builder
from api_testing.constraint.ir.extractors.prompt_builder import (
    PredicatePromptBuilder,
)

# Request-response extractors
from api_testing.constraint.ir.extractors.request_response import (
    RequestResponseAnalyzer,
)
from api_testing.constraint.ir.extractors.response_property import (
    CrossFieldResponseAnalyzer,
    ResPropCrossFieldCoverageChecker,
    ResPropSingleCoverageChecker,
    ResPropSingleDescriptionExtractor,
    ResPropSingleLLMExtractor,
    ResPropSingleStructuralExtractor,
    SingleFieldResponseAnalyzer,
)

__all__ = [
    # Response property
    "ResPropSingleStructuralExtractor",
    "ResPropSingleDescriptionExtractor",
    "ResPropSingleLLMExtractor",
    "ResPropSingleCoverageChecker",
    "SingleFieldResponseAnalyzer",
    "ResPropCrossFieldCoverageChecker",
    "CrossFieldResponseAnalyzer",
    # Request-response
    "RequestResponseAnalyzer",
    # Common
    "CandidateConstraint",
    "Evidence",
    # Prompt builder
    "PredicatePromptBuilder",
]
