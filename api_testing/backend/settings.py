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
    metadata_db_path: Path | None = None
    spec_storage_root: Path | None = None
    allowed_target_base_urls: tuple[str, ...] = ()
    max_active_executions: int = 2
    default_execution_timeout_seconds: int = 60
    default_request_budget: int = 20
    default_async_max_concurrent: int = 20
    subprocess_cancel_grace_seconds: int = 5

    def __post_init__(self) -> None:
        cache_root = Path(self.cache_root)
        object.__setattr__(self, "cache_root", cache_root)
        object.__setattr__(
            self,
            "metadata_db_path",
            Path(self.metadata_db_path)
            if self.metadata_db_path is not None
            else cache_root / "_backend" / "apipilot.db",
        )
        object.__setattr__(
            self,
            "spec_storage_root",
            Path(self.spec_storage_root)
            if self.spec_storage_root is not None
            else cache_root / "_backend" / "specs",
        )

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
        allowed_targets_value = os.getenv("APIPILOT_BACKEND_ALLOWED_TARGET_BASE_URLS", "")
        allowed_targets = tuple(
            target.strip()
            for target in allowed_targets_value.split(",")
            if target.strip()
        )
        return cls(
            cache_root=cache_root,
            allowed_origins=allowed_origins,
            metadata_db_path=_optional_path("APIPILOT_BACKEND_METADATA_DB_PATH"),
            spec_storage_root=_optional_path("APIPILOT_BACKEND_SPEC_STORAGE_ROOT"),
            allowed_target_base_urls=allowed_targets,
            max_active_executions=_int_env("APIPILOT_BACKEND_MAX_ACTIVE_EXECUTIONS", 2),
            default_execution_timeout_seconds=_int_env(
                "APIPILOT_BACKEND_DEFAULT_EXECUTION_TIMEOUT_SECONDS",
                60,
            ),
            default_request_budget=_int_env(
                "APIPILOT_BACKEND_DEFAULT_REQUEST_BUDGET",
                20,
            ),
            default_async_max_concurrent=_int_env(
                "APIPILOT_BACKEND_DEFAULT_ASYNC_MAX_CONCURRENT",
                20,
            ),
            subprocess_cancel_grace_seconds=_int_env(
                "APIPILOT_BACKEND_SUBPROCESS_CANCEL_GRACE_SECONDS",
                5,
            ),
        )


def _optional_path(name: str) -> Path | None:
    value = os.getenv(name)
    return Path(value) if value else None


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)
