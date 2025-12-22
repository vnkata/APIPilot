"""
Configuration for OpenAPI client
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class OpenAPIConfig:
    """
    Configuration for OpenAPIClient behavior

    Attributes:
        cache_enabled: Enable caching of parsed specs (default: True)
        cache_ttl: Cache TTL in seconds (default: 3600 = 1 hour)
        validate_spec: Validate spec against OAS schema on load (default: True)
        strict_validation: Strict request/response validation (default: False)
        resolve_refs: Resolve all $ref references (default: True)
        lazy_load: Lazy-load Pydantic models on-demand (default: True)
        allow_invalid_specs: Allow loading invalid specs (default: False)
        default_timeout: Default HTTP timeout for dynamic client (default: 30s)
        max_retries: Max retries for HTTP requests (default: 3)
    """

    # Caching
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour

    # Parsing & Validation
    validate_spec: bool = True
    strict_validation: bool = False
    resolve_refs: bool = True
    lazy_load: bool = True
    allow_invalid_specs: bool = False

    # HTTP Client
    default_timeout: int = 30
    max_retries: int = 3

    # Paths
    cache_dir: Optional[Path] = field(default=None)

    def __post_init__(self) -> None:
        # Ensure cache_dir is Path if provided as string
        if self.cache_dir and not isinstance(self.cache_dir, Path):
            object.__setattr__(self, "cache_dir", Path(self.cache_dir))


# Default config instance
DEFAULT_CONFIG = OpenAPIConfig()


__all__ = ["OpenAPIConfig", "DEFAULT_CONFIG"]
