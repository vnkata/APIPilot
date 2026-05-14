from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


@dataclass(frozen=True, slots=True)
class BackendSettings:
    cache_root: Path = Path(".cache")
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS

    @classmethod
    def from_env(cls) -> "BackendSettings":
        cache_root = Path(os.getenv("APIPILOT_BACKEND_CACHE_ROOT", ".cache"))
        origins_value = os.getenv("APIPILOT_BACKEND_ALLOWED_ORIGINS")
        if origins_value is None:
            allowed_origins = DEFAULT_ALLOWED_ORIGINS
        else:
            allowed_origins = tuple(
                origin.strip() for origin in origins_value.split(",") if origin.strip()
            )
        return cls(cache_root=cache_root, allowed_origins=allowed_origins)
