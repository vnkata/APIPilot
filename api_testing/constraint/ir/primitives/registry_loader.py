"""
Predicate registry loader and manager.

Loads predicate metadata from registry_data.json and provides
access to predicate information for validation and IR building.
"""

import json
from pathlib import Path
from typing import Optional

from api_testing.constraint.ir.primitives.registry_models import (
    PredicateMetadata,
    PredicateRegistry,
)
from common.logger import get_logger

logger = get_logger(__name__)


class PredicateRegistryLoader:
    """Loader for predicate registry data."""

    _instance: Optional["PredicateRegistryLoader"] = None
    _registry: PredicateRegistry | None = None

    def __new__(cls):
        """Singleton pattern for registry loader."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize registry loader."""
        if self._registry is None:
            self._load_registry()

    def _load_registry(self) -> None:
        """Load registry from merged category-specific JSON files."""
        try:
            # Check for old monolithic registry file and warn if found
            old_registry_file = Path(__file__).parent / "registry_data.json"
            if old_registry_file.exists():
                logger.warning(
                    "DEPRECATION WARNING: registry_data.json is deprecated. "
                    "The registry now uses category-specific files in registry/primitives/ and registry/relations/. "
                    "Please update any tools that reference registry_data.json directly.",
                    old_file=str(old_registry_file),
                    new_location="registry/primitives/ and registry/relations/",
                )

            from api_testing.constraint.ir.primitives.registry import (
                load_merged_registry,
            )

            data = load_merged_registry()
            self._registry = PredicateRegistry(**data)

            logger.info(
                "Predicate registry loaded from merged sources",
                total=len(self._registry.predicates),
                implemented=len(self._registry.list_implemented()),
            )
        except Exception as e:
            logger.error(
                "Failed to load predicate registry",
                error=str(e),
                error_type=type(e).__name__,
            )
            self._registry = PredicateRegistry(predicates=[])

    @property
    def registry(self) -> PredicateRegistry:
        """Get the loaded registry."""
        if self._registry is None:
            self._load_registry()
        return self._registry  # type: ignore

    def get(self, kind: str, version: str = "v1") -> PredicateMetadata | None:
        """Get predicate metadata.

        Args:
            kind: Predicate kind
            version: Predicate version

        Returns:
            PredicateMetadata or None if not found
        """
        return self.registry.get(kind, version)

    def list_all(self) -> list[PredicateMetadata]:
        """List all predicates."""
        return self.registry.predicates

    def list_implemented(self) -> list[PredicateMetadata]:
        """List only implemented predicates."""
        return self.registry.list_implemented()

    def list_by_category(self, category: str) -> list[PredicateMetadata]:
        """List predicates by category."""
        return self.registry.list_by_category(category)

    def is_implemented(self, kind: str, version: str = "v1") -> bool:
        """Check if predicate is implemented."""
        meta = self.get(kind, version)
        return meta.implemented if meta else False

    def validate_args(self, kind: str, version: str, args: dict) -> bool:
        """Validate predicate arguments against schema.

        Args:
            kind: Predicate kind
            version: Predicate version
            args: Arguments to validate

        Returns:
            True if valid, False otherwise
        """
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import ValidationError

        meta = self.get(kind, version)
        if not meta:
            logger.warning(f"Unknown predicate: {kind}@{version}")
            return False

        try:
            schema = meta.args_schema.model_dump(exclude_none=True)
            validator = Draft202012Validator(schema)
            validator.validate(args)
            return True
        except ValidationError as e:
            logger.error(
                "Predicate args validation failed",
                predicate=f"{kind}@{version}",
                error=e.message,
            )
            return False

    def validate_and_categorize(
        self, predicate_kind: str, version: str, args: dict
    ) -> tuple[bool, str | None, str | None]:
        """Validate predicate and return (is_valid, error_msg, category).

        Categorizes predicate validation result into three states:
        - valid: Predicate exists in registry and args are valid
        - invalid: Predicate exists but args don't match schema
        - proposed: Predicate doesn't exist in registry

        Args:
            predicate_kind: Predicate kind (e.g., 'int.range')
            version: Predicate version (e.g., 'v1')
            args: Arguments to validate

        Returns:
            Tuple of (is_valid, error_msg, category) where:
            - (True, None, "valid"): Predicate exists and args are valid
            - (False, error_msg, "invalid"): Predicate exists but args invalid
            - (False, None, "proposed"): Predicate doesn't exist in registry

        Example:
            >>> loader = PredicateRegistryLoader()
            >>> is_valid, error, cat = loader.validate_and_categorize("int.range", "v1", {"min": 1, "max": 10})
            >>> assert is_valid and cat == "valid"
            >>> is_valid, error, cat = loader.validate_and_categorize("int.range", "v1", {"invalid": "arg"})
            >>> assert not is_valid and cat == "invalid"
            >>> is_valid, error, cat = loader.validate_and_categorize("string.unknown", "v1", {})
            >>> assert not is_valid and cat == "proposed"
        """
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import ValidationError

        # Check if predicate exists
        meta = self.get(predicate_kind, version)

        if not meta:
            # Predicate doesn't exist - it's a proposal
            return (False, None, "proposed")

        # Predicate exists - validate args
        try:
            schema = meta.args_schema.model_dump(exclude_none=True)
            validator = Draft202012Validator(schema)
            validator.validate(args)
            return (True, None, "valid")
        except ValidationError as e:
            # Args don't match schema
            error_msg = f"Invalid args for {predicate_kind}@{version}: {e.message}"
            return (False, error_msg, "invalid")


# Global registry instance
_loader = PredicateRegistryLoader()


def get_registry() -> PredicateRegistry:
    """Get the global predicate registry."""
    return _loader.registry


def get_predicate(kind: str, version: str = "v1") -> PredicateMetadata | None:
    """Get predicate metadata."""
    return _loader.get(kind, version)


def validate_predicate_args(kind: str, version: str, args: dict) -> bool:
    """Validate predicate arguments."""
    return _loader.validate_args(kind, version, args)


class ProposedPredicateManager:
    """Manager for LLM-proposed predicates.

    Handles saving and loading proposed predicates to/from proposed_predicates.json.
    """

    def __init__(self, registry_dir: Path | None = None):
        """Initialize manager.

        Args:
            registry_dir: Directory containing registry files (defaults to primitives dir)
        """
        if registry_dir is None:
            registry_dir = Path(__file__).parent

        self.proposed_file = registry_dir / "proposed_predicates.json"
        self.logger = logger
        self._registry: dict | None = None

    def load(self) -> dict:
        """Load proposed predicates from file.

        Returns:
            Dictionary with version and predicates list
        """
        if not self.proposed_file.exists():
            return {"version": "1.0", "predicates": []}

        try:
            with open(self.proposed_file, encoding="utf-8") as f:
                data = json.load(f)
            self._registry = data
            return data
        except Exception as e:
            self.logger.error(
                "Failed to load proposed predicates",
                file=str(self.proposed_file),
                error=str(e),
            )
            return {"version": "1.0", "predicates": []}

    def save(self, data: dict) -> bool:
        """Save proposed predicates to file.

        Args:
            data: Dictionary with version and predicates

        Returns:
            True if successful
        """
        try:
            with open(self.proposed_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._registry = data
            self.logger.info(
                "Proposed predicates saved",
                file=str(self.proposed_file),
                count=len(data.get("predicates", [])),
            )
            return True
        except Exception as e:
            self.logger.error(
                "Failed to save proposed predicates",
                file=str(self.proposed_file),
                error=str(e),
            )
            return False

    def add_proposal(
        self,
        kind: str,
        version: str,
        category: str,
        description: str,
        args_schema: dict,
        evidence: str,
        field_context: str | None = None,
        proposed_by: str = "llm",
    ) -> bool:
        """Add a new predicate proposal.

        Args:
            kind: Predicate kind
            version: Version
            category: Category
            description: Description
            args_schema: Arguments schema
            evidence: Evidence/reasoning
            field_context: Optional field path context
            proposed_by: Source of proposal

        Returns:
            True if added successfully
        """
        from datetime import datetime

        # Load current proposals
        data = self.load()

        # Check for duplicates
        for pred in data.get("predicates", []):
            if pred.get("kind") == kind and pred.get("version") == version:
                self.logger.warning(
                    "Predicate already proposed",
                    predicate=f"{kind}@{version}",
                )
                return False

        # Create proposal
        proposal = {
            "kind": kind,
            "version": version,
            "category": category,
            "description": description,
            "args_schema": args_schema,
            "proposed_by": proposed_by,
            "evidence": evidence,
            "status": "pending_review",
            "proposed_at": datetime.utcnow().isoformat() + "Z",
        }

        if field_context:
            proposal["field_context"] = field_context

        # Add and save
        data["predicates"].append(proposal)
        return self.save(data)

    def get_proposals(self, status: str | None = None) -> list[dict]:
        """Get all proposals, optionally filtered by status.

        Args:
            status: Optional status filter (pending_review, approved, rejected)

        Returns:
            List of proposal dictionaries
        """
        data = self.load()
        proposals = data.get("predicates", [])

        if status:
            proposals = [p for p in proposals if p.get("status") == status]

        return proposals

    def get_proposed(self) -> list[dict]:
        """Get all proposed predicates pending review.

        Returns:
            List of pending proposals
        """
        return self.get_proposals(status="pending_review")

    def save_proposed(
        self,
        predicate_kind: str,
        args_schema: dict,
        description: str,
        evidence: str,
        proposed_by: str = "llm",
        field_context: str | None = None,
    ) -> bool:
        """Save newly proposed predicate for review.

        Args:
            predicate_kind: Proposed predicate name (e.g., "string.is_canadian_province")
            args_schema: Expected arguments schema (JSON Schema format)
            description: Human description
            evidence: Evidence from API spec or reasoning
            proposed_by: Source (default: "llm")
            field_context: Optional field path context

        Returns:
            True if saved successfully
        """
        # Parse kind to extract category
        parts = predicate_kind.split(".")
        category = parts[0] if parts else "unknown"

        # Default version
        version = "v1"

        return self.add_proposal(
            kind=predicate_kind,
            version=version,
            category=category,
            description=description,
            args_schema=args_schema,
            evidence=evidence,
            field_context=field_context,
            proposed_by=proposed_by,
        )

    def mark_reviewed(self, predicate_kind: str, status: str) -> bool:
        """Mark predicate as reviewed (accepted/rejected).

        Args:
            predicate_kind: Predicate kind (e.g., "string.email")
            status: New status ("approved" or "rejected")

        Returns:
            True if updated successfully
        """
        if status not in ["approved", "rejected"]:
            self.logger.error(
                "Invalid status",
                status=status,
                valid_statuses=["approved", "rejected"],
            )
            return False

        # Load proposals
        data = self.load()

        # Find and update
        found = False
        for pred in data.get("predicates", []):
            if pred.get("kind") == predicate_kind:
                pred["status"] = status
                from datetime import datetime

                pred["reviewed_at"] = datetime.utcnow().isoformat() + "Z"
                found = True
                break

        if not found:
            self.logger.warning("Predicate not found", predicate_kind=predicate_kind)
            return False

        return self.save(data)


__all__ = [
    "PredicateRegistryLoader",
    "ProposedPredicateManager",
    "get_registry",
    "get_predicate",
    "validate_predicate_args",
]
