"""Domain exceptions raised by artifact backend use cases."""

from __future__ import annotations


class ArtifactBackendError(Exception):
    """Base class for backend artifact errors."""


class ArtifactNotFound(ArtifactBackendError):
    """Raised when a run, artifact, operation, or HAR session does not exist."""


class InvalidArtifactRequest(ArtifactBackendError):
    """Raised when a request is unsafe or cannot be fulfilled."""


class ArtifactConflict(ArtifactBackendError):
    """Raised when a write request conflicts with existing idempotent state."""
