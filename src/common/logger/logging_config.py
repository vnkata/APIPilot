"""
Logging Configuration Module for RBCTest Constraint Mining

This module provides centralized configuration for comprehensive logging across
the constraint mining pipeline with support for:
- Hybrid logging (pretty console + JSON file)
- Per-component log files
- Detailed GPT call logging
- Context tracking for nested operations
- Async logging with minimal performance impact
- Environment-based configuration (DEV vs PROD)

Configuration aligns with user requirements:
- Level: DETAILED (DEBUG level for comprehensive inspection)
- Format: HYBRID (pretty console, JSON files)
- Encoding: UTF-8 everywhere
- Organization: Component-specific logs + main log
- GPT: Separate detailed log for prompts/responses
- Performance: Async logging with level control
- Context: Chain tracking for nested calls
"""

import os
from datetime import datetime
from typing import Optional
from pathlib import Path

from common.logger.logger_factory import LoggerFactory, LoggerType, LogLevel
from common.logger.models import LoggerConfig, FileHandlerConfig, PerLevelConfig


class Environment:
    """Environment detection and configuration"""

    @staticmethod
    def get_environment() -> str:
        """
        Detect current environment from ENV variable

        Returns:
            'dev', 'prod', or 'test'
        """
        env = os.getenv("ENV", "dev").lower()
        if env in ("production", "prod"):
            return "prod"
        elif env in ("test", "testing"):
            return "test"
        return "dev"

    @staticmethod
    def is_dev() -> bool:
        """Check if running in development environment"""
        return Environment.get_environment() == "dev"

    @staticmethod
    def is_prod() -> bool:
        """Check if running in production environment"""
        return Environment.get_environment() == "prod"


class LoggingConfig:
    """Central configuration for RBCTest logging system"""

    # Base log directory
    BASE_LOG_DIR = "logs"

    # Environment-aware log levels
    @classmethod
    def get_console_level(cls) -> LogLevel:
        """Get console log level based on environment"""
        if Environment.is_dev():
            return LogLevel.DEBUG  # Verbose in dev
        elif Environment.is_prod():
            return LogLevel.INFO  # Quiet in prod
        return LogLevel.INFO  # Default

    @classmethod
    def get_file_level(cls) -> LogLevel:
        """Get file log level based on environment"""
        # Always detailed logging to files for forensics
        return LogLevel.DEBUG

    # Legacy properties for backward compatibility
    CONSOLE_LEVEL = LogLevel.INFO
    FILE_LEVEL = LogLevel.DEBUG

    # Component-specific settings
    COMPONENTS = {
        "main": "constraints_mining",
        "constraint_inference": "constraint_inference",
        "parameter_mapping": "parameter_mapping",
        "gpt_calls": "gpt_calls",
        "gpt_detailed": "gpt_detailed",
    }

    @classmethod
    def get_log_dir(cls, service_name: Optional[str] = None) -> str:
        """
        Get the log directory for a specific service.

        Args:
            service_name: Name of the service (e.g., "Canada Holidays")
                         If None, returns base log dir.

        Returns:
            str: Full path to log directory
        """
        if service_name:
            # Create service-specific subdirectory
            log_dir = os.path.join(cls.BASE_LOG_DIR, service_name)
        else:
            log_dir = cls.BASE_LOG_DIR

        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    @classmethod
    def get_log_file(
        cls, component: str, service_name: Optional[str] = None, timestamp: bool = True
    ) -> str:
        """
        Get the log file path for a component.

        Args:
            component: Component name (key from COMPONENTS dict)
            service_name: Service name for per-service logging
            timestamp: Whether to include timestamp in filename

        Returns:
            str: Full path to log file
        """
        log_dir = cls.get_log_dir(service_name)
        component_name = cls.COMPONENTS.get(component, component)

        if timestamp:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{component_name}_{timestamp_str}.log"
        else:
            filename = f"{component_name}.log"

        return os.path.join(log_dir, filename)

    @classmethod
    def create_logger(
        cls,
        name: str,
        component: str,
        service_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        **context,
    ):
        """
        Create a configured logger for a component.

        Args:
            name: Logger name (typically __name__ from calling module)
            component: Component type (from COMPONENTS)
            service_name: Service name for context and log file naming
            level: Override default log level
            **context: Additional context to add to logger

        Returns:
            Logger instance configured with hybrid format and context
        """
        log_file = cls.get_log_file(component, service_name, timestamp=False)

        # Use environment-aware levels
        file_level = level if level is not None else cls.get_file_level()
        console_level = cls.get_console_level()

        logger = LoggerFactory.get_logger(
            name=name,
            logger_type=LoggerType.STANDARD,
            level=file_level,
            console_level=console_level,
            file_level=file_level,
            log_file=log_file,
        )

        # Add base context
        base_context = {
            "component": component,
            "environment": Environment.get_environment(),
        }
        if service_name:
            base_context["service"] = service_name

        # Merge with additional context
        base_context.update(context)
        logger.add_context(**base_context)

        return logger

    @classmethod
    def create_gpt_logger(cls, service_name: Optional[str] = None):
        """
        Create specialized logger for GPT calls with dual output:
        - Main GPT log: Metadata only (model, tokens, timing)
        - Detailed GPT log: Full prompts and responses

        Args:
            service_name: Service name for log organization

        Returns:
            tuple: (metadata_logger, detailed_logger)
        """
        # Metadata logger (structured, concise)
        metadata_logger = cls.create_logger(
            name="gpt_metadata",
            component="gpt_calls",
            service_name=service_name,
            level=LogLevel.INFO,
        )

        # Detailed logger (full prompts/responses)
        detailed_log_file = cls.get_log_file(
            "gpt_detailed", service_name, timestamp=False
        )
        detailed_logger = LoggerFactory.get_logger(
            name="gpt_detailed",
            logger_type=LoggerType.STANDARD,
            level=cls.get_file_level(),
            console_level=cls.get_console_level(),
            file_level=cls.get_file_level(),
            log_file=detailed_log_file,
        )

        if service_name:
            detailed_logger.add_context(
                service=service_name,
                component="gpt_detailed",
                environment=Environment.get_environment(),
            )

        return metadata_logger, detailed_logger

    @classmethod
    def create_logger_with_per_level(
        cls,
        name: str,
        component: str,
        service_name: Optional[str] = None,
        level: Optional[LogLevel] = None,
        per_level_dir: Optional[str] = None,
        levels: Optional[list[LogLevel]] = None,
        **context,
    ):
        """
        Create logger with per-level file logging enabled

        Args:
            name: Logger name
            component: Component type
            service_name: Service name for context
            level: Override default log level
            per_level_dir: Directory for per-level logs (defaults to logs/levels/{service})
            levels: Levels to create files for (defaults to all)
            **context: Additional context

        Returns:
            Logger instance with per-level logging
        """
        # Determine main log file
        main_log_file = cls.get_log_file(component, service_name, timestamp=False)

        # Determine per-level directory
        if per_level_dir is None:
            if service_name:
                per_level_dir = os.path.join(cls.BASE_LOG_DIR, service_name, "levels")
            else:
                per_level_dir = os.path.join(cls.BASE_LOG_DIR, "levels")

        # Use environment-aware levels
        file_level = level if level is not None else cls.get_file_level()
        console_level = cls.get_console_level()

        # Create config with per-level logging
        config = LoggerConfig.with_per_level_logging(
            name=name,
            level=file_level,
            log_file=main_log_file,
            per_level_dir=per_level_dir,
            console_level=console_level,
            file_level=file_level,
            use_colors=True,
            levels=levels,
        )

        # Add context
        base_context = {
            "component": component,
            "environment": Environment.get_environment(),
        }
        if service_name:
            base_context["service"] = service_name
        base_context.update(context)
        config.initial_context = base_context

        # Create logger using factory
        logger = LoggerFactory.get_logger_with_config(config, cache=True)
        return logger


# Convenience functions for quick logger creation


def get_main_logger(service_name: str, **context):
    """Get main orchestration logger with service context"""
    return LoggingConfig.create_logger(
        name="main", component="main", service_name=service_name, **context
    )


def get_constraint_logger(service_name: str, **context):
    """Get constraint inference logger with service context"""
    return LoggingConfig.create_logger(
        name="constraint_inference",
        component="constraint_inference",
        service_name=service_name,
        **context,
    )


def get_parameter_logger(service_name: str, **context):
    """Get parameter mapping logger with service context"""
    return LoggingConfig.create_logger(
        name="parameter_mapping",
        component="parameter_mapping",
        service_name=service_name,
        **context,
    )


def get_gpt_loggers(service_name: str):
    """Get both GPT loggers (metadata + detailed)"""
    return LoggingConfig.create_gpt_logger(service_name)


def get_logger_with_per_level(
    name: str,
    service_name: Optional[str] = None,
    component: str = "main",
    per_level_dir: Optional[str] = None,
    **context,
):
    """
    Get logger with per-level file logging enabled

    Args:
        name: Logger name
        service_name: Service name
        component: Component type
        per_level_dir: Custom per-level directory
        **context: Additional context

    Returns:
        Logger with per-level logging
    """
    return LoggingConfig.create_logger_with_per_level(
        name=name,
        component=component,
        service_name=service_name,
        per_level_dir=per_level_dir,
        **context,
    )


# Helper for adding operation context
def add_operation_context(logger, operation: str, **extra):
    """
    Add operation-specific context to logger.

    Args:
        logger: Logger instance
        operation: Operation name (e.g., "GET /api/v1/holidays")
        **extra: Additional context fields
    """
    context = {"operation": operation}
    context.update(extra)
    logger.add_context(**context)
    return logger
