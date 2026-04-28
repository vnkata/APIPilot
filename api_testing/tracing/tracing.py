"""
Tracing Module for API Testing

This module provides comprehensive tracing capabilities including:
- LLM usage and cost tracking
- Request/response logging
- Performance metrics
- Debug logging
"""

import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any
import litellm


@dataclass
class LLMUsage:
    """Data class for LLM token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add_usage(self, usage: Dict[str, int]):
        """Add usage from a response."""
        self.prompt_tokens += usage.get("prompt_tokens", 0)
        self.completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class LLMResponse:
    """Data class for LLM response logging."""
    messages: List[Dict[str, Any]]
    usage: Dict[str, int]
    response_time: float
    model: str
    timestamp: str

    @classmethod
    def from_callback(cls, kwargs: Dict, response_obj: Dict, start_time: float, end_time: float) -> "LLMResponse":
        """Create from callback parameters."""
        return cls(
            messages=kwargs.get("messages", []),
            usage=response_obj.get("usage", {}),
            response_time=end_time - start_time,
            model=kwargs.get("model", "unknown"),
            timestamp=datetime.now().isoformat()
        )


class TraceManager:
    """
    Comprehensive tracing manager for API testing operations.

    Singleton class that handles LLM cost tracking, logging, and performance monitoring.
    Only one instance exists throughout the application lifecycle.
    Ensures consistent tracing across the entire application.
    """

    # Singleton instance
    _instance = None

    # Pricing per 1K tokens (example rates - should be configurable)
    MODEL_PRICING = {
        "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }

    def __new__(cls, trace_path: str, llm_model: Optional[str] = None, log_level: int = logging.INFO):
        """Ensure only one instance of TraceManager exists."""
        if cls._instance is None:
            cls._instance = super(TraceManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, trace_path: str, llm_model: Optional[str] = None, log_level: int = logging.INFO):
        """
        Initialize the TraceManager.

        Note: Due to singleton pattern, initialization only happens once.
        Subsequent calls with different parameters will be ignored.

        Args:
            trace_path: Directory path for storing trace files
            llm_model: Default LLM model for pricing calculations
            log_level: Logging level
        """
        # Only initialize if not already done
        if hasattr(self, '_initialized'):
            return

        self.trace_path = trace_path
        self.llm_model = llm_model
        self.log_level = log_level

        # Ensure trace directory exists
        os.makedirs(self.trace_path, exist_ok=True)

        # Initialize usage tracking
        self.total_usage = LLMUsage()
        self.session_usage = LLMUsage()

        # Setup logging
        self.logger = self._setup_logger()

        # Register LLM callback
        self._register_llm_callback()

        # Load existing usage if available
        self._load_usage()

        # Mark as initialized
        self._initialized = True

        # Load existing usage if available
        self._load_usage()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with file and console handlers."""
        logger = logging.getLogger(f"TraceManager_{id(self)}")
        logger.setLevel(self.log_level)

        if logger.handlers:
            return logger  # Already configured

        # File handler
        log_file = os.path.join(self.trace_path, "trace.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(self.log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def _register_llm_callback(self):
        """Register the LLM success callback for tracking."""
        litellm.success_callback = [self._llm_callback]

    def _llm_callback(self, kwargs: Dict, response_obj: Dict, start_time: float, end_time: float):
        """Callback function for LLM requests."""
        try:
            # Update usage
            current_usage = response_obj.get("usage", {})
            self.total_usage.add_usage(current_usage)
            self.session_usage.add_usage(current_usage)

            # Calculate cost
            model = kwargs.get("model", self.llm_model or "unknown")
            cost = self._calculate_cost(model, current_usage)

            # Log response
            response_data = LLMResponse.from_callback(kwargs, response_obj, start_time, end_time)
            self._log_response(response_data, cost)

            # Save usage
            self._save_usage()

            self.logger.debug(f"LLM call completed - Model: {model}, Cost: ${cost:.6f}")

        except Exception as e:
            self.logger.error(f"Error in LLM callback: {e}")

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate cost for LLM usage."""
        pricing = self.MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})

        input_tokens = usage.get("prompt_tokens", 0) / 1000
        output_tokens = usage.get("completion_tokens", 0) / 1000

        cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
        return cost

    def _log_response(self, response: LLMResponse, cost: float):
        """Log LLM response to file."""
        log_file = os.path.join(self.trace_path, "llm_responses.jsonl")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                log_entry = {
                    **asdict(response),
                    "cost": cost
                }
                json.dump(log_entry, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Failed to log response: {e}")

    def _save_usage(self):
        """Save current usage statistics."""
        usage_file = os.path.join(self.trace_path, "llm_usage.json")
        try:
            usage_data = {
                "total": self.total_usage.to_dict(),
                "session": self.session_usage.to_dict(),
                "timestamp": datetime.now().isoformat()
            }
            with open(usage_file, "w", encoding="utf-8") as f:
                json.dump(usage_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save usage: {e}")

    def _load_usage(self):
        """Load existing usage statistics."""
        usage_file = os.path.join(self.trace_path, "llm_usage.json")
        if os.path.exists(usage_file):
            try:
                with open(usage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_usage = LLMUsage(**data.get("total", {}))
            except Exception as e:
                self.logger.warning(f"Failed to load usage: {e}")

    def log_event(self, event_type: str, message: str, **kwargs):
        """Log a custom event."""
        event_data = {
            "type": event_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }

        event_file = os.path.join(self.trace_path, "events.jsonl")
        try:
            with open(event_file, "a", encoding="utf-8") as f:
                json.dump(event_data, f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            self.logger.error(f"Failed to log event: {e}")

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary."""
        return {
            "total": self.total_usage.to_dict(),
            "session": self.session_usage.to_dict(),
            "total_cost": self._calculate_cost(self.llm_model or "unknown", self.total_usage.to_dict()) if self.llm_model else 0.0
        }

    def reset_session_usage(self):
        """Reset session usage counter."""
        self.session_usage = LLMUsage()
        self._save_usage()
        self.logger.debug("Session usage reset")

    @classmethod
    def get_instance(cls) -> Optional["TraceManager"]:
        """Get the singleton instance if it exists."""
        return cls._instance

    @classmethod
    def reset_singleton(cls):
        """Reset the singleton instance (useful for testing)."""
        if cls._instance:
            cls._instance.close()
        cls._instance = None

    def close(self):
        """Clean up and save final state."""
        self._save_usage()
        self.logger.debug("TraceManager closed")


# Convenience function for backward compatibility
def get_trace_manager(trace_path: str, llm_model: Optional[str] = None, log_level: int = logging.INFO) -> TraceManager:
    """
    Get the singleton TraceManager instance.

    Args:
        trace_path: Directory path for storing trace files
        llm_model: Default LLM model for pricing calculations
        log_level: Logging level

    Returns:
        The singleton TraceManager instance
    """
    return TraceManager(trace_path, llm_model, log_level)