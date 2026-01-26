"""
Simplified logger API for quick usage
"""

import re
from typing import Optional
from pathlib import Path
from common.logger.logger_factory import LoggerFactory, LoggerType
from common.logger.logger_interface import LoggerInterface, LogLevel
from common.logger.models import LoggerConfig
from common.file.paths import get_project_log_dir, resolve_to_project_root


def _sanitize_logger_name_for_filename(name: str) -> str:
    """
    Sanitize logger name for use in filename.

    Replaces dots and other invalid characters with underscores.

    Args:
        name: Logger name (e.g., "common.logger.utils.helpers")

    Returns:
        Sanitized name (e.g., "common_logger_utils_helpers")
    """
    # Replace dots and other non-alphanumeric characters (except underscores and hyphens) with underscores
    sanitized = re.sub(r"[^\w\-_.]", "_", name)
    # Replace dots with underscores for cleaner filenames
    sanitized = sanitized.replace(".", "_")
    # Remove leading/trailing underscores and collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized or "app"


def get_logger(
    name: Optional[str] = None,
    level: LogLevel = LogLevel.INFO,
    log_file: Optional[str] = None,
    console_level: Optional[LogLevel] = None,
    file_level: Optional[LogLevel] = None,
    use_colors: bool = True,
    enable_per_level: bool = True,
    per_level_dir: Optional[str] = None,
) -> LoggerInterface:
    """
    Get a logger instance with simplified API.

    By default, creates logger with:
    - Console output (INFO level)
    - Main log file (DEBUG level)
    - Per-level log files (DEBUG.log, INFO.log, WARNING.log, ERROR.log, CRITICAL.log)

    Args:
        name: Logger name (auto-detected from caller if None)
        level: Default log level (used if console_level/file_level not specified)
        log_file: Optional file path for logging. If None, auto-generates from logger name.
                  Relative paths are resolved to project root, absolute paths are used as-is.
        console_level: Log level for console output (default: INFO if not specified)
        file_level: Log level for file output (default: DEBUG if not specified)
        use_colors: Whether to use colored output (default: True)
        enable_per_level: Enable per-level file logging (default: True)
        per_level_dir: Directory for per-level logs (default: logs/levels/)

    Returns:
        LoggerInterface instance

    Example:
        >>> from common.logger import get_logger, LogLevel
        >>> # Simple usage with all defaults (console + file + per-level)
        >>> logger = get_logger(__name__)
        >>> logger.info("Hello world!")
        >>> logger.error("Error goes to ERROR.log automatically!")

        >>> # With separate console/file levels
        >>> logger = get_logger(
        ...     __name__,
        ...     console_level=LogLevel.INFO,
        ...     file_level=LogLevel.DEBUG
        ... )

        >>> # Disable per-level logging if needed
        >>> logger = get_logger(__name__, enable_per_level=False)

        >>> # Custom per-level directory
        >>> logger = get_logger(__name__, per_level_dir="logs/custom_levels")
    """
    import inspect

    # Auto-detect caller module name if not provided
    if name is None:
        frame = inspect.currentframe()
        if frame and frame.f_back:
            caller_module = frame.f_back.f_globals.get("__name__", "unknown")
            name = caller_module
        else:
            name = "app"

    # Auto-generate log file path if not provided
    if log_file is None:
        sanitized_name = _sanitize_logger_name_for_filename(name)
        log_file = str(get_project_log_dir() / f"{sanitized_name}.log")
    else:
        # Resolve relative paths to project root, preserve absolute paths
        log_file = str(resolve_to_project_root(log_file))

    # Set default levels: console INFO, file DEBUG
    if console_level is None:
        console_level = LogLevel.INFO
    if file_level is None:
        file_level = LogLevel.DEBUG

    # If per-level logging is enabled, use config-based approach
    if enable_per_level:
        # Auto-generate per-level directory if not provided
        if per_level_dir is None:
            per_level_dir = str(get_project_log_dir() / "levels")
        else:
            per_level_dir = str(resolve_to_project_root(per_level_dir))

        # Create config with per-level logging
        config = LoggerConfig.with_per_level_logging(
            name=name,
            level=level,
            log_file=log_file,
            console_level=console_level,
            file_level=file_level,
            use_colors=use_colors,
            per_level_dir=per_level_dir,
        )

        return LoggerFactory.get_logger_with_config(config)
    else:
        # Use legacy approach without per-level logging
        return LoggerFactory.get_logger(
            name=name,
            logger_type=LoggerType.STANDARD,
            level=level,
            console_level=console_level,
            file_level=file_level,
            log_file=log_file,
            use_colors=use_colors,
        )


__all__ = ["get_logger"]
