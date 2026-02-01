"""
Data models for logger configuration using Pydantic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from common.logger.logger_interface import LogLevel


class FileHandlerConfig(BaseModel):
    """Configuration for file handler."""

    path: Path = Field(..., description="Log file path")
    level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level")
    format_type: str = Field(
        default="json", description="Format type: 'json' or 'text'"
    )
    rotation: str = Field(default="500 MB", description="Log rotation size/time")
    retention: str = Field(default="10 days", description="Log retention period")
    compression: str = Field(default="zip", description="Compression format")


class PerLevelConfig(BaseModel):
    """Configuration for per-level file handlers."""

    enabled: bool = Field(default=False, description="Enable per-level logging")
    base_dir: Path = Field(
        default=Path("logs/levels"), description="Base directory for level files"
    )
    levels: List[LogLevel] = Field(
        default_factory=lambda: [
            LogLevel.DEBUG,
            LogLevel.INFO,
            LogLevel.WARNING,
            LogLevel.ERROR,
            LogLevel.CRITICAL,
        ],
        description="Levels to create separate files for",
    )
    format_type: str = Field(
        default="json", description="Format type: 'json' or 'text'"
    )
    rotation: str = Field(default="100 MB", description="Log rotation size/time")
    retention: str = Field(default="7 days", description="Log retention period")
    compression: str = Field(default="zip", description="Compression format")

    def get_file_path(self, level: LogLevel) -> Path:
        """Get file path for specific log level."""
        return self.base_dir / f"{level.value.lower()}.log"


class LoggerConfig(BaseModel):
    """Complete logger configuration."""

    name: str = Field(default="app", description="Logger name")
    level: LogLevel = Field(default=LogLevel.INFO, description="Base log level")

    # Console settings
    console_enabled: bool = Field(default=True, description="Enable console logging")
    console_level: Optional[LogLevel] = Field(
        default=None, description="Console log level (defaults to base level)"
    )
    use_colors: bool = Field(default=True, description="Use colored output")

    # File settings
    file_enabled: bool = Field(default=False, description="Enable file logging")
    file_config: Optional[FileHandlerConfig] = Field(
        default=None, description="Main file handler config"
    )
    file_level: Optional[LogLevel] = Field(
        default=None, description="File log level (defaults to base level)"
    )

    # Per-level file settings
    per_level_config: Optional[PerLevelConfig] = Field(
        default=None, description="Per-level file handler config"
    )

    # Context
    initial_context: Dict[str, Any] = Field(
        default_factory=dict, description="Initial context for all logs"
    )

    @property
    def effective_console_level(self) -> LogLevel:
        """Get effective console level."""
        return self.console_level or self.level

    @property
    def effective_file_level(self) -> LogLevel:
        """Get effective file level."""
        return self.file_level or self.level

    @classmethod
    def create_simple(
        cls,
        name: str = "app",
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        console_level: Optional[LogLevel] = None,
        file_level: Optional[LogLevel] = None,
        use_colors: bool = True,
    ) -> LoggerConfig:
        """
        Create a simple logger configuration.

        Args:
            name: Logger name
            level: Base log level
            log_file: Path to log file (enables file logging if provided)
            console_level: Console log level (defaults to base level)
            file_level: File log level (defaults to base level)
            use_colors: Use colored console output

        Returns:
            LoggerConfig instance
        """
        file_config = None
        if log_file:
            file_config = FileHandlerConfig(
                path=Path(log_file),
                level=file_level or level,
            )

        return cls(
            name=name,
            level=level,
            console_enabled=True,
            console_level=console_level,
            use_colors=use_colors,
            file_enabled=log_file is not None,
            file_config=file_config,
            file_level=file_level,
        )

    @classmethod
    def create_development(
        cls,
        name: str = "dev",
        log_dir: str = "logs",
    ) -> LoggerConfig:
        """
        Create development configuration with per-level logging.

        Args:
            name: Logger name
            log_dir: Base log directory

        Returns:
            LoggerConfig instance
        """
        log_path = Path(log_dir)
        return cls(
            name=name,
            level=LogLevel.DEBUG,
            console_enabled=True,
            console_level=LogLevel.DEBUG,
            use_colors=True,
            file_enabled=True,
            file_config=FileHandlerConfig(
                path=log_path / "app.log",
                level=LogLevel.DEBUG,
                format_type="text",
            ),
            per_level_config=PerLevelConfig(
                enabled=True,
                base_dir=log_path / "levels",
                format_type="text",
            ),
        )

    @classmethod
    def create_production(
        cls,
        name: str = "prod",
        log_dir: str = "/var/log/app",
    ) -> LoggerConfig:
        """
        Create production configuration with JSON logging.

        Args:
            name: Logger name
            log_dir: Base log directory

        Returns:
            LoggerConfig instance
        """
        log_path = Path(log_dir)
        return cls(
            name=name,
            level=LogLevel.INFO,
            console_enabled=True,
            console_level=LogLevel.WARNING,
            use_colors=False,
            file_enabled=True,
            file_config=FileHandlerConfig(
                path=log_path / "app.json",
                level=LogLevel.INFO,
                format_type="json",
                rotation="100 MB",
                retention="30 days",
            ),
            per_level_config=PerLevelConfig(
                enabled=True,
                base_dir=log_path / "levels",
                levels=[LogLevel.ERROR, LogLevel.CRITICAL],
                format_type="json",
                rotation="50 MB",
                retention="90 days",
            ),
        )

    @classmethod
    def with_per_level_logging(
        cls,
        name: str = "app",
        level: LogLevel = LogLevel.INFO,
        log_file: Optional[str] = None,
        per_level_dir: str = "logs/levels",
        console_level: Optional[LogLevel] = None,
        file_level: Optional[LogLevel] = None,
        use_colors: bool = True,
        levels: Optional[List[LogLevel]] = None,
    ) -> LoggerConfig:
        """
        Create config with per-level file logging enabled.

        Args:
            name: Logger name
            level: Base log level
            log_file: Main log file path
            per_level_dir: Directory for per-level logs
            console_level: Console output level
            file_level: File output level
            use_colors: Enable colored output
            levels: Levels to create files for (defaults to all)

        Returns:
            LoggerConfig instance with per-level logging
        """
        file_config = None
        if log_file:
            file_config = FileHandlerConfig(
                path=Path(log_file),
                level=file_level or level,
            )

        per_level_config = PerLevelConfig(
            enabled=True,
            base_dir=Path(per_level_dir),
            levels=levels
            or [
                LogLevel.DEBUG,
                LogLevel.INFO,
                LogLevel.WARNING,
                LogLevel.ERROR,
                LogLevel.CRITICAL,
            ],
        )

        return cls(
            name=name,
            level=level,
            console_level=console_level,
            use_colors=use_colors,
            file_enabled=log_file is not None,
            file_config=file_config,
            file_level=file_level,
            per_level_config=per_level_config,
        )
