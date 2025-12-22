# common/logger/standard_logger.py

import sys
import os
import inspect
from typing import Any, Optional, Dict
from pathlib import Path
from loguru import logger as loguru_logger

from common.logger.logger_interface import LoggerInterface, LogLevel
from common.logger.utils.serialize_utils import (
    serialize_for_console,
    serialize_for_file,
)



class StandardLogger(LoggerInterface):
    """Standard logger implementation using Loguru library"""

    # Loguru level mapping
    LEVEL_MAP = {
        LogLevel.DEBUG: "DEBUG",
        LogLevel.INFO: "INFO",
        LogLevel.WARNING: "WARNING",
        LogLevel.ERROR: "ERROR",
        LogLevel.CRITICAL: "CRITICAL",
    }

    # Class-level flag to track if default handler has been removed
    _default_handler_removed = False

    def __init__(
        self,
        name: str = "restful-api-testing",
        level: LogLevel = LogLevel.INFO,
        console_level: Optional[LogLevel] = None,
        file_level: Optional[LogLevel] = None,
        use_colors: bool = True,
        log_file: Optional[str] = None,
    ):
        self.name = name
        self.context: Dict[str, Any] = {}
        self.use_colors = use_colors
        self.log_file = log_file

        # Set default levels
        self._console_level = console_level or level
        self._file_level = file_level or level if log_file else None
        self._level = level

        # Remove default handler only once
        if not StandardLogger._default_handler_removed:
            loguru_logger.remove()
            StandardLogger._default_handler_removed = True

        # Add console handler with colors
        console_format = self._get_console_format(use_colors)
        loguru_logger.add(
            sys.stderr,
            format=console_format,
            level=self.LEVEL_MAP[self._console_level],
            colorize=use_colors,
            backtrace=True,
            diagnose=True,
            filter=lambda record: record["extra"].get("logger_name") == name,
        )

        # Add file handler if log file is specified
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_format = self._get_file_format()
            loguru_logger.add(
                log_file,
                format=file_format,
                level=(
                    self.LEVEL_MAP[self._file_level]
                    if self._file_level
                    else self.LEVEL_MAP[level]
                ),
                rotation="10 MB",  # Rotate when file reaches 10MB
                retention="30 days",  # Keep logs for 30 days
                compression="zip",  # Compress rotated logs
                backtrace=True,
                diagnose=True,
                enqueue=True,  # Thread-safe async logging
                filter=lambda record: record["extra"].get("logger_name") == name,
            )

        # Bind logger name to context
        self.logger = loguru_logger.bind(logger_name=name)

    def _get_console_format(self, use_colors: bool) -> str:
        """Get console log format with caller information"""
        if use_colors:
            return (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<dim>[PID:{process}] [TID:{thread}]</dim> | "
                "<cyan>{extra[caller_file]}</cyan>:<cyan>{extra[caller_function]}</cyan>:<cyan>{extra[caller_line]}</cyan> | "
                "<level>{message}</level>"
                "{extra[data_context]}"
            )
        else:
            return (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "[PID:{process}] [TID:{thread}] | "
                "{extra[caller_file]}:{extra[caller_function]}:{extra[caller_line]} | "
                "{message}"
                "{extra[data_context]}"
            )

    def _get_file_format(self) -> str:
        """Get file log format - JSON structured for production"""
        return (
            '{{"timestamp":"{time:YYYY-MM-DD HH:mm:ss.SSS}", '
            '"level":"{level}", '
            '"logger":"{extra[logger_name]}", '
            '"file":"{extra[caller_file]}", '
            '"function":"{extra[caller_function]}", '
            '"line":{extra[caller_line]}, '
            '"process":{process}, '
            '"thread":{thread}, '
            '"message":"{message}"'
            "{extra[data_json]}"
            "}}"
        )

    def _get_caller_info(self) -> Dict[str, Any]:
        """Get caller information from stack frame"""
        try:
            # Go up the stack to find the actual caller
            # Stack: _get_caller_info -> _log_with_context -> debug/info/etc -> actual_caller
            frame = inspect.currentframe()
            if frame is None:
                return {
                    "caller_file": "unknown",
                    "caller_function": "unknown",
                    "caller_line": 0,
                }

            # Skip: _get_caller_info (0) -> _log_with_context (1) -> debug/info/etc (2) -> actual caller (3)
            caller_frame = frame.f_back.f_back.f_back

            if caller_frame is None:
                return {
                    "caller_file": "unknown",
                    "caller_function": "unknown",
                    "caller_line": 0,
                }

            # Get file path and extract just the filename
            file_path = caller_frame.f_code.co_filename
            file_name = os.path.basename(file_path)

            return {
                "caller_file": file_name,
                "caller_function": caller_frame.f_code.co_name,
                "caller_line": caller_frame.f_lineno,
            }
        except Exception as e:
            # Fallback if stack inspection fails
            return {
                "caller_file": "error",
                "caller_function": "error",
                "caller_line": 0,
            }

    def _log_with_context(self, level: str, message: str, *args, **kwargs) -> None:
        """Log with context and caller information"""
        try:
            # Get caller information
            caller_info = self._get_caller_info()

            # Extract data from kwargs (everything except 'extra')
            extra_data = kwargs.pop("extra", {})

            # All remaining kwargs are data to be logged
            data_kwargs = kwargs

            # Merge instance context with call context and caller info
            full_context = {**self.context, **caller_info, **extra_data}

            # Prepare data serialization for console (pretty) and file (compact)
            data_context_str = ""
            data_json_str = ""

            if data_kwargs:
                # Serialize for console (pretty-print with newlines + colorization)
                console_parts = []
                for key, value in data_kwargs.items():
                    serialized = serialize_for_console(value)

                    # Apply Rich colorization if available and colors enabled
                    # if self.use_colors and is_colorization_available():
                    #     serialized = colorize_for_console(serialized)

                    # Check if it's multiline
                    if "\n" in serialized:
                        console_parts.append(
                            f"\n  {key}=\n    {serialized.replace(chr(10), chr(10) + '    ')}"
                        )
                    else:
                        console_parts.append(f"\n  {key}={serialized}")
                data_context_str = "".join(console_parts)

                # Serialize for file (compact JSON - no colors)
                file_parts = []
                for key, value in data_kwargs.items():
                    serialized = serialize_for_file(value)
                    file_parts.append(f'"{key}":{serialized}')
                data_json_str = ", " + ", ".join(file_parts)

            # Add data context to full_context
            full_context["data_context"] = data_context_str
            full_context["data_json"] = data_json_str

            # Bind context and log
            bound_logger = self.logger.bind(**full_context)

            # Format message if args provided (backward compatibility)
            if args:
                message = message.format(*args)

            # Log at the specified level
            bound_logger.opt(depth=1).log(level, message)
        except Exception as e:
            # Fallback logging if something goes wrong
            print(f"Logger error: {e}", file=sys.stderr)
            print(f"Original message: {message}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log debug message"""
        self._log_with_context("DEBUG", message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log info message"""
        self._log_with_context("INFO", message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log warning message"""
        self._log_with_context("WARNING", message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log error message"""
        self._log_with_context("ERROR", message, *args, **kwargs)

    def critical(self, message: str, *args, **kwargs) -> None:
        """Log critical message"""
        self._log_with_context("CRITICAL", message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """Log exception with traceback"""
        try:
            # Get caller information
            caller_info = self._get_caller_info()

            # Extract data from kwargs
            extra_data = kwargs.pop("extra", {})
            data_kwargs = kwargs

            # Merge contexts
            full_context = {**self.context, **caller_info, **extra_data}

            # Prepare data serialization
            data_context_str = ""
            data_json_str = ""

            if data_kwargs:
                console_parts = []
                for key, value in data_kwargs.items():
                    serialized = serialize_for_console(value)

                    # Apply Rich colorization if available and colors enabled
                    # if self.use_colors and is_colorization_available():
                    #     serialized = colorize_for_console(serialized)

                    if "\n" in serialized:
                        console_parts.append(
                            f"\n  {key}=\n    {serialized.replace(chr(10), chr(10) + '    ')}"
                        )
                    else:
                        console_parts.append(f"\n  {key}={serialized}")
                data_context_str = "".join(console_parts)

                file_parts = []
                for key, value in data_kwargs.items():
                    serialized = serialize_for_file(value)
                    file_parts.append(f'"{key}":{serialized}')
                data_json_str = ", " + ", ".join(file_parts)

            full_context["data_context"] = data_context_str
            full_context["data_json"] = data_json_str

            bound_logger = self.logger.bind(**full_context)

            if args:
                message = message.format(*args)

            bound_logger.opt(depth=1).exception(message)
        except Exception as e:
            print(f"Logger error: {e}", file=sys.stderr)
            print(f"Original message: {message}", file=sys.stderr)
            import traceback

            traceback.print_exc()

    def log(self, level: LogLevel, message: str, *args, **kwargs) -> None:
        """Log message with specified level"""
        loguru_level = self.LEVEL_MAP[level]
        self._log_with_context(loguru_level, message, *args, **kwargs)

    def set_level(self, level: LogLevel) -> None:
        """Set log level"""
        self._level = level
        # Note: Loguru handlers are configured at creation time
        # To change level dynamically, you would need to remove and re-add handlers

    def set_console_level(self, level: LogLevel) -> None:
        """Set minimum log level for console output"""
        self._console_level = level
        # Note: Would need to remove and re-add handlers to change dynamically

    def set_file_level(self, level: LogLevel) -> None:
        """Set minimum log level for file output"""
        self._file_level = level
        # Note: Would need to remove and re-add handlers to change dynamically

    def get_console_level(self) -> LogLevel:
        """Get current console log level"""
        return self._console_level

    def get_file_level(self) -> Optional[LogLevel]:
        """Get current file log level (None if no file logging)"""
        return self._file_level

    def add_context(self, **kwargs) -> None:
        """Add context to all subsequent log messages"""
        self.context.update(kwargs)

    def remove_context(self, *keys) -> None:
        """Remove context keys"""
        for key in keys:
            self.context.pop(key, None)

    def clear_context(self) -> None:
        """Clear all context"""
        self.context.clear()

    def get_context(self) -> Dict[str, Any]:
        """Get current context"""
        return self.context.copy()

    def child(self, name: str, **kwargs) -> "StandardLogger":
        """Create a child logger with additional context"""
        child_name = f"{self.name}.{name}"
        child = StandardLogger(
            name=child_name,
            level=self._level,
            console_level=self._console_level,
            file_level=self._file_level,
            use_colors=self.use_colors,
            log_file=self.log_file,
        )
        child.context = {**self.context, **kwargs}
        return child
