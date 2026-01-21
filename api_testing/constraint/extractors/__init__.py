"""
Constraint extractors for mining constraints from API specifications.

This module provides extractors for different types of constraints:
- Response property constraints (single-field and multi-field)
- Request-response constraints (parameters matching response data)
- Common utilities for matching and analysis
"""

# Response property extractors
from api_testing.constraint.extractors.response_property import (
    ResPropSingleStructuralExtractor,
    ResPropSingleDescriptionExtractor,
    ResPropSingleLLMExtractor,
    ResPropSingleCoverageChecker,
    SingleFieldResponseAnalyzer,
    ResPropCrossFieldCoverageChecker,
    CrossFieldResponseAnalyzer,
)

# Request-response extractors
from api_testing.constraint.extractors.request_response import (
    RequestResponseAnalyzer,
)

# Common utilities
from api_testing.constraint.extractors.common import (
    CandidateConstraint,
    Evidence,
)

# Prompt builder
from api_testing.constraint.extractors.prompt_builder import (
    PredicatePromptBuilder,
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
