"""
Constraint module for extracting and validating API constraints.

New architecture (v2):
- ir/: Enhanced IR models with Scope, Provenance, Conditions
- extractors/: Multi-phase extraction pipeline
- primitives/: Comprehensive validator registry
- engine/: Validation engine with selectors and CEL

Legacy:
- StaticConstraintMiner: Updated to use new IR builder
"""

from .static_constraint_miner import StaticConstraintMiner

# New v2 exports
from api_testing.constraint.ir import (
    ConstraintIRModel,
    ConstraintModel,
    ScopeModel,
    SelectorModel,
    PredicateModel,
    ProvenanceModel,
    ConditionModel,
    ConstraintIRBuilder,
    IRSchemaValidator,
)
from api_testing.constraint.extractors import (
    ResPropSingleStructuralExtractor,
    ResPropSingleDescriptionExtractor,
    ResPropSingleLLMExtractor,
    PredicatePromptBuilder,
    ResPropCrossFieldCoverageChecker,
)
from api_testing.constraint.primitives.registry_loader import ProposedPredicateManager
from api_testing.constraint.primitives import (
    PredicateRegistry,
    get_registry,
    get_predicate,
    VALIDATOR_REGISTRY,
    get_validator,
)
from api_testing.constraint.engine import (
    ValidationEngine,
    SelectorEngine,
    CELEvaluator,
)
from api_testing.constraint.reporting import CSVReporter
from api_testing.constraint.cache import SchemaConstraintCache

__all__ = [
    # Legacy
    "StaticConstraintMiner",
    # IR Models
    "ConstraintIRModel",
    "ConstraintModel",
    "ScopeModel",
    "SelectorModel",
    "PredicateModel",
    "ProvenanceModel",
    "ConditionModel",
    "ConstraintIRBuilder",
    "IRSchemaValidator",
    # Extractors
    "ResPropSingleStructuralExtractor",
    "ResPropSingleDescriptionExtractor",
    "ResPropLLMCoverageChecker",
    "ResPropSingleLLMExtractor",
    "PredicatePromptBuilder",
    "ResPropCrossFieldLLMExtractor",
    "ResPropCrossFieldCoverageChecker",
    "ProposedPredicateManager",
    # Primitives
    "PredicateRegistry",
    "get_registry",
    "get_predicate",
    "VALIDATOR_REGISTRY",
    "get_validator",
    # Engine
    "ValidationEngine",
    "SelectorEngine",
    "CELEvaluator",
    # Reporting
    "CSVReporter",
    # Cache
    "SchemaConstraintCache",
]
