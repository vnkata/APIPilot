"""
LLM Observability Module

OpenTelemetry tracing + Langfuse integration for LLM operations.
"""

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Dict, Optional

# OpenTelemetry imports (optional)
try:
    from opentelemetry import trace
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Status, StatusCode

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None  # type: ignore
    Status = None  # type: ignore
    StatusCode = None  # type: ignore
    HTTPXClientInstrumentor = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore

# Langfuse imports (optional)
try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None  # type: ignore

import json
from pathlib import Path

from common.logger.utils.helpers import get_logger

logger = get_logger(__name__)

# Debug logging configuration
_DEBUG_LOG_PATH = Path(r"d:\Projects\Desktop\restapi-testing-tool\.cursor\debug.log")

# Global flag to track if we've already logged Langfuse unavailability warning
_langfuse_unavailable_logged = False


def _debug_log(
    session_id: str,
    run_id: str,
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict,
):
    """Write debug log entry."""
    try:
        log_entry = {
            "sessionId": session_id,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass  # Fail silently to avoid breaking production code


class LLMTracer:
    """
    Unified tracer for LLM operations.

    Supports:
    - OpenTelemetry distributed tracing
    - Langfuse LLM-specific observability
    - Fallback to logging when neither is available

    Langfuse Setup:
        Langfuse captures full LLM call details: prompts, responses, token usage, and metadata.

        1. Install: pip install langfuse

        2. Get credentials (choose one):
           - Self-hosted: Start Langfuse (e.g., docker-compose) and get keys from UI
           - Cloud: Sign up at https://cloud.langfuse.com and get keys from dashboard

        3. Configure (choose one method):
           a) Environment variables (recommended):
              export LANGFUSE_PUBLIC_KEY="your-public-key"
              export LANGFUSE_SECRET_KEY="your-secret-key"
              export LANGFUSE_HOST="http://localhost:3000"  # Optional, defaults to localhost:3000

           b) Pass directly to LLMTracer:
              tracer = LLMTracer(
                  enable_langfuse=True,
                  langfuse_public_key="your-public-key",
                  langfuse_secret_key="your-secret-key",
                  langfuse_host="http://localhost:3000",  # Optional
              )

           c) Via LLMConfig (see LLMConfig docstring)

        4. Access Langfuse UI:
           - Self-hosted: http://localhost:3000 (default)
           - Cloud: https://cloud.langfuse.com

        The tracer automatically captures:
        - Input messages (prompts)
        - Output responses
        - Token usage (prompt_tokens, completion_tokens, total_tokens)
        - Model name
        - Metadata (provider, request_id, temperature, etc.)
    """

    def __init__(
        self,
        *,
        enable_otel: bool = True,
        enable_langfuse: bool = False,
        enable_httpx_instrumentation: bool = False,
        langfuse_public_key: str | None = None,
        langfuse_secret_key: str | None = None,
        langfuse_host: str | None = None,
        langfuse_connection_timeout: float = 2.0,
        langfuse_enable_health_check: bool = True,
        service_name: str = "llm-client",
    ):
        self.enable_otel = enable_otel and OTEL_AVAILABLE
        self.enable_langfuse = enable_langfuse and LANGFUSE_AVAILABLE
        self.enable_httpx_instrumentation = enable_httpx_instrumentation
        self.service_name = service_name
        self._tracer = None
        self._langfuse = None
        self._httpx_instrumented = False
        self._langfuse_available = False  # Track if Langfuse is actually reachable
        self._langfuse_connection_timeout = langfuse_connection_timeout
        self._langfuse_enable_health_check = langfuse_enable_health_check
        self._otel_exporter_initialized = False  # Track if we initialized OTEL exporter

        # Cleanup any existing httpx instrumentation if we don't want it
        # This prevents issues from previous runs that may have left instrumentation active
        if OTEL_AVAILABLE and not enable_httpx_instrumentation:
            try:
                HTTPXClientInstrumentor().uninstrument()
                logger.debug("Cleaned up any existing HTTPX instrumentation")
            except Exception:
                pass  # Ignore errors if already uninstrumented

        # Initialize Langfuse FIRST to check availability before OpenTelemetry
        # Support env vars as fallback: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
        # Priority: parameter > env var > None
        import os

        resolved_public_key = langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        resolved_secret_key = langfuse_secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        resolved_host = langfuse_host or os.getenv("LANGFUSE_HOST")

        if self.enable_langfuse and resolved_public_key and resolved_secret_key:
            self._init_langfuse(
                resolved_public_key,
                resolved_secret_key,
                resolved_host,
            )
        elif self.enable_langfuse:
            logger.warning(
                "Langfuse enabled but credentials not provided. "
                "Set langfuse_public_key and langfuse_secret_key in config "
                "or LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY env vars. "
                "Tracing will be disabled."
            )
            self._langfuse_available = False

        # Initialize OpenTelemetry AFTER Langfuse
        # Only enable OpenTelemetry if Langfuse is available (OpenTelemetry exports to Langfuse)
        if self.enable_otel:
            self._init_otel()

    def _check_otel_initialized(self) -> bool:
        """
        Check if OpenTelemetry SDK has been initialized via environment variables.

        Returns:
            True if OpenTelemetry SDK is already initialized, False otherwise.
        """
        if not OTEL_AVAILABLE:
            return False

        try:
            import os

            # Check if OTEL environment variables are set that would auto-initialize SDK
            otel_vars = [
                "OTEL_EXPORTER_OTLP_ENDPOINT",
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
                "OTEL_SERVICE_NAME",
            ]
            return any(os.getenv(var) for var in otel_vars)
        except Exception:
            return False

    def _init_otel(self) -> None:
        """
        Initialize OpenTelemetry tracing.

        Note: OpenTelemetry is only enabled if Langfuse is available and reachable,
        as OpenTelemetry traces are exported to Langfuse's OTLP endpoint.
        If Langfuse is not available, OpenTelemetry is disabled to avoid
        connection errors and noisy exception logs.

        If OpenTelemetry SDK was already initialized via env vars, we check
        Langfuse availability and suppress export errors if unavailable.
        """
        global _langfuse_unavailable_logged

        if not OTEL_AVAILABLE:
            self.enable_otel = False
            return

        try:
            # Only enable OpenTelemetry if Langfuse is available and reachable
            # OpenTelemetry exports traces to Langfuse's OTLP endpoint
            if self.enable_langfuse and (
                not self._langfuse or not self._langfuse_available
            ):
                # Langfuse is not available - disable OpenTelemetry
                # Only log once to avoid spam
                if not _langfuse_unavailable_logged:
                    logger.warning(
                        "OpenTelemetry disabled: Langfuse not available or unreachable. "
                        "OpenTelemetry tracing requires Langfuse to be running and reachable. "
                        "LLM operations will continue without OpenTelemetry tracing."
                    )
                    _langfuse_unavailable_logged = True
                self.enable_otel = False
                return

            # Check if OpenTelemetry SDK was already initialized via env vars
            otel_already_initialized = self._check_otel_initialized()

            if otel_already_initialized:
                # OpenTelemetry SDK was initialized via env vars
                # If Langfuse is not available, we can't easily disable the exporter
                # but we can at least suppress errors by not creating spans
                if not self._langfuse_available:
                    logger.warning(
                        "OpenTelemetry SDK was initialized via environment variables, "
                        "but Langfuse is unavailable. OpenTelemetry spans will not be created "
                        "to avoid export errors. Consider unsetting OTEL_EXPORTER_OTLP_ENDPOINT "
                        "if Langfuse is unavailable."
                    )
                    self.enable_otel = False
                    return

            # Get tracer - this will use existing TracerProvider if SDK was initialized via env vars
            # or create a new one if not
            self._tracer = trace.get_tracer(self.service_name)

            # Only initialize exporter if we haven't already and Langfuse is available
            # If SDK was initialized via env vars, exporter is already configured
            if not otel_already_initialized and self._langfuse_available:
                # We would normally set up OTLP exporter here, but since we're using
                # Langfuse's OTLP endpoint, and Langfuse SDK handles this, we don't need
                # to configure it separately. The tracer will work with Langfuse's integration.
                self._otel_exporter_initialized = True

            # Instrument HTTPX for automatic tracing of HTTP calls (disabled by default)
            # WARNING: This instruments ALL httpx clients globally in the process
            # Only enable if you want to trace all HTTP requests, not just LLM calls
            if self.enable_httpx_instrumentation and not self._httpx_instrumented:
                try:
                    HTTPXClientInstrumentor().instrument()
                    self._httpx_instrumented = True
                    logger.debug("HTTPX instrumented for OpenTelemetry (global)")
                    logger.warning(
                        "HTTPX global instrumentation enabled - this affects ALL httpx clients in the process"
                    )
                except Exception as e:
                    logger.warning(f"Failed to instrument HTTPX: {e}")

            if self._langfuse_available:
                logger.info("OpenTelemetry tracing initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry: {e}")
            self.enable_otel = False

    def _init_langfuse(
        self,
        public_key: str,
        secret_key: str,
        host: str | None,
    ) -> None:
        """
        Initialize Langfuse observability.

        Also checks if Langfuse is reachable to determine if OpenTelemetry
        should be enabled (OpenTelemetry exports to Langfuse's OTLP endpoint).

        Uses health check endpoint first, then falls back to OTLP endpoint test.
        """
        global _langfuse_unavailable_logged

        try:
            # If host not provided, default to localhost:3000 for self-hosted
            resolved_host = host or "http://localhost:3000"

            self._langfuse = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=resolved_host,
            )

            # Test connection to Langfuse by checking if the host is reachable
            # This helps determine if OpenTelemetry should be enabled
            # We test health endpoint first, then OTLP endpoint
            import urllib.error
            import urllib.request
            from urllib.parse import urljoin

            available = False
            timeout = self._langfuse_connection_timeout

            if self._langfuse_enable_health_check:
                # Try health check endpoint first (if available)
                try:
                    health_endpoint = urljoin(
                        resolved_host.rstrip("/") + "/", "/api/public/health"
                    )
                    req = urllib.request.Request(health_endpoint, method="GET")
                    urllib.request.urlopen(req, timeout=timeout)
                    available = True
                except (urllib.error.URLError, OSError, Exception):
                    # Health endpoint not available or failed, try OTLP endpoint
                    pass

            # If health check didn't succeed, try OTLP endpoint
            if not available:
                try:
                    otlp_endpoint = urljoin(
                        resolved_host.rstrip("/") + "/", "/api/public/otel/v1/traces"
                    )
                    req = urllib.request.Request(otlp_endpoint, method="HEAD")
                    urllib.request.urlopen(req, timeout=timeout)
                    available = True
                except (urllib.error.URLError, OSError, Exception) as conn_error:
                    # Connection failed - Langfuse is not reachable
                    available = False
                    # Only log warning once globally to avoid spam
                    if not _langfuse_unavailable_logged:
                        logger.warning(
                            f"Langfuse host is unreachable: {resolved_host}. "
                            f"Error: {type(conn_error).__name__}. "
                            "OpenTelemetry will be disabled to avoid export errors. "
                            "LLM operations will continue, but tracing will be disabled."
                        )
                        _langfuse_unavailable_logged = True

            self._langfuse_available = available

            if available:
                logger.info(
                    f"Langfuse observability initialized (host: {resolved_host})"
                )
            else:
                # Disable Langfuse if not available
                self.enable_langfuse = False

        except Exception as e:
            # Only log warning once globally
            if not _langfuse_unavailable_logged:
                logger.warning(
                    f"Failed to initialize Langfuse: {e}. "
                    "Tracing will be disabled. LLM operations will continue normally."
                )
                _langfuse_unavailable_logged = True
            self.enable_langfuse = False
            self._langfuse_available = False

    def cleanup(self) -> None:
        """Cleanup tracer resources and uninstrument httpx if needed."""
        if self._httpx_instrumented:
            try:
                HTTPXClientInstrumentor().uninstrument()
                self._httpx_instrumented = False
                logger.debug("HTTPX uninstrumented")
            except Exception as e:
                logger.warning(f"Failed to uninstrument HTTPX: {e}")

    @contextmanager
    def span(
        self,
        name: str,
        *,
        attributes: dict[str, Any] | None = None,
        input: Any | None = None,
        model: str | None = None,
    ) -> Generator[Optional["SpanContext"], None, None]:
        """
        Create a traced span for an operation.

        Args:
            name: Span name (e.g., "llm.chat", "llm.stream")
            attributes: Optional metadata dictionary for the span
            input: Optional input data to set on Langfuse generation at creation time.
                   For LLM calls, this should be the messages list:
                   [{"role": "user", "content": "..."}, ...]
            model: Optional model name/identifier. Should be set at creation time
                   for Langfuse cost calculation. If not provided, can be set later
                   via span.set_llm_model().

        Returns:
            SpanContext that can be used to set additional attributes, LLM data, etc.

        Usage:
            # Basic usage
            with tracer.span("llm.chat", attributes={"model": "gpt-4o-mini"}) as span:
                result = await client.chat(...)
                if span:
                    span.set_attribute("tokens", result.usage.total_tokens)

            # With Langfuse input and model set at start (recommended for cost calculation)
            messages = [{"role": "user", "content": "Hello!"}]
            with tracer.span("llm.chat", model="gpt-4o-mini", input=messages) as span:
                result = await client.chat(messages)
                if span:
                    span.set_llm_output(result.content)
                    span.set_llm_usage({
                        "prompt_tokens": result.usage.prompt_tokens,
                        "completion_tokens": result.usage.completion_tokens,
                        "total_tokens": result.usage.total_tokens,
                    })
                    span.finalize_llm_data()
        """
        context = SpanContext(name=name, tracer=self)
        start_time = time.time()

        # Start OTEL span
        # Only create spans if OpenTelemetry is enabled AND Langfuse is available
        # This prevents export errors when Langfuse is unavailable
        otel_span = None
        if self.enable_otel and self._tracer and self._langfuse_available:
            try:
                otel_span = self._tracer.start_span(name)
                if attributes:
                    for key, value in attributes.items():
                        otel_span.set_attribute(key, _sanitize_attribute(value))
                context._otel_span = otel_span
            except Exception as e:
                # Suppress errors when creating spans if Langfuse is unavailable
                logger.debug(f"Failed to create OpenTelemetry span: {e}")
                otel_span = None

        # Start Langfuse generation (for LLM calls)
        langfuse_generation = None
        if self.enable_langfuse and self._langfuse:
            try:
                generation_kwargs = {
                    "name": name,
                }
                if attributes:
                    generation_kwargs["metadata"] = attributes
                if input is not None:
                    generation_kwargs["input"] = input
                # Set model at creation time for cost calculation
                if model is not None:
                    generation_kwargs["model"] = model

                # Use start_observation with as_type='generation' (correct Langfuse API)
                langfuse_generation = self._langfuse.start_observation(
                    as_type="generation", **generation_kwargs
                )
                context._langfuse_generation = langfuse_generation
                # Store model in context for potential use in finalize_llm_data()
                if model is not None:
                    context._llm_model = model

            except Exception as e:
                logger.warning(f"Failed to create Langfuse generation: {e}")

        try:
            yield context

            # Success
            if otel_span:
                otel_span.set_status(Status(StatusCode.OK))
        except Exception as e:
            # Error
            if otel_span:
                otel_span.set_status(Status(StatusCode.ERROR, str(e)))
                otel_span.record_exception(e)
            if langfuse_generation:
                try:
                    langfuse_generation.update(
                        status_message=str(e),
                        level="ERROR",
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to update Langfuse generation on error: {e}"
                    )
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000

            # Finalize Langfuse LLM data before ending
            if langfuse_generation and context:
                try:
                    # Batch all LLM updates into single update() call
                    context.finalize_llm_data()

                    # Flush to ensure data is sent to Langfuse server
                    if self._langfuse:
                        self._langfuse.flush()

                except Exception as e:
                    logger.warning(f"Failed to finalize/flush Langfuse data: {e}")

            # End OTEL span
            # Suppress errors when ending spans to avoid export error spam
            if otel_span:
                try:
                    otel_span.set_attribute("duration_ms", duration_ms)
                    otel_span.end()
                except Exception as e:
                    # Suppress export errors - they're expected when Langfuse is unavailable
                    # Only log at debug level to avoid noise
                    logger.debug(f"Failed to end OpenTelemetry span: {e}")

            # End Langfuse generation
            if langfuse_generation:
                try:
                    langfuse_generation.end()
                except Exception as e:
                    logger.warning(f"Failed to end Langfuse generation: {e}")

    def log_llm_call(
        self,
        *,
        model: str,
        messages: list,
        response: str | None = None,
        usage: dict[str, int] | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Log an LLM call with full details for Langfuse.

        Call this after completing an LLM operation to record
        the full prompt/response for analysis.
        """
        if not self.enable_langfuse or not self._langfuse:
            return

        try:
            # Use start_observation with as_type='generation' (correct Langfuse API)
            generation = self._langfuse.start_observation(
                as_type="generation",
                name="llm-call",
                model=model,
                input=messages,
                output=response,
                usage_details=usage,  # Note: use usage_details, not usage
                metadata=metadata,
                level="ERROR" if error else "DEFAULT",
                status_message=error,
            )
            generation.end()  # End immediately since all data is provided at creation
        except Exception as e:
            logger.warning(f"Failed to log LLM call to Langfuse: {e}")

    def flush(self) -> None:
        """Flush any pending traces."""
        if self.enable_langfuse and self._langfuse:
            try:
                self._langfuse.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")

    def shutdown(self) -> None:
        """Shutdown tracer and flush pending data."""
        self.flush()
        if self._langfuse:
            try:
                self._langfuse.shutdown()
            except Exception as e:
                logger.warning(f"Failed to shutdown Langfuse: {e}")


class SpanContext:
    """Context for an active span, allowing attribute updates."""

    def __init__(self, name: str, tracer: LLMTracer):
        self.name = name
        self._tracer = tracer
        self._otel_span: Any | None = None
        self._langfuse_generation: Any | None = None
        self._attributes: dict[str, Any] = {}
        # Internal state for batching LLM data updates
        self._llm_output: str | None = None
        self._llm_usage: dict[str, int] | None = None
        self._llm_model: str | None = None
        self._llm_data_finalized: bool = False

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span."""
        self._attributes[key] = value

        if self._otel_span:
            try:
                self._otel_span.set_attribute(key, _sanitize_attribute(value))
            except Exception:
                pass

        if self._langfuse_generation:
            try:
                self._langfuse_generation.update(metadata={key: value})
            except Exception as e:
                logger.warning(f"Failed to update Langfuse generation metadata: {e}")

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        """Set multiple attributes."""
        for key, value in attributes.items():
            self.set_attribute(key, value)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        if self._otel_span:
            try:
                self._otel_span.add_event(
                    name,
                    attributes={
                        k: _sanitize_attribute(v) for k, v in (attributes or {}).items()
                    },
                )
            except Exception:
                pass

    def record_exception(self, exception: Exception) -> None:
        """Record an exception on the span."""
        if self._otel_span:
            try:
                self._otel_span.record_exception(exception)
            except Exception:
                pass

    def set_llm_input(self, messages: list) -> None:
        """
        Set input messages for Langfuse generation.

        Args:
            messages: List of message dicts in OpenAI format:
                     [{"role": "user", "content": "..."}, ...]

        Note: Input should typically be set at span creation time, but this method
        allows updating it if needed.
        """
        if self._langfuse_generation:
            try:
                self._langfuse_generation.update(input=messages)
            except Exception as e:
                logger.warning(f"Failed to set Langfuse input: {e}")

    def set_llm_output(self, response: str) -> None:
        """
        Set output response for Langfuse generation.

        Args:
            response: The complete response content from the LLM.

        Note: Data is stored internally and will be sent when finalize_llm_data() is called.
        """
        self._llm_output = response

    def set_llm_usage(self, usage: dict[str, int]) -> None:
        """
        Set token usage for Langfuse generation.

        Args:
            usage: Dict with keys:
                   - "prompt_tokens": int
                   - "completion_tokens": int
                   - "total_tokens": int

        Note: Data is stored internally and will be sent when finalize_llm_data() is called.
        """
        self._llm_usage = usage

    def set_llm_model(self, model: str) -> None:
        """
        Set model name for Langfuse generation.

        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "claude-3-opus").

        Note: Model should ideally be set at span creation time for cost calculation.
        If set here, data is stored internally and will be sent when finalize_llm_data() is called.
        """
        self._llm_model = model

    def finalize_llm_data(self) -> None:
        """
        Finalize and send all batched LLM data to Langfuse in a single update call.

        This method batches all LLM-related updates (output, usage, model) into
        a single update() call, which is more efficient and ensures data consistency.

        Should be called after all LLM data has been collected (e.g., after
        receiving the LLM response).
        """

        if self._llm_data_finalized or not self._langfuse_generation:
            return

        try:
            update_kwargs: dict[str, Any] = {}

            if self._llm_output is not None:
                update_kwargs["output"] = self._llm_output

            if self._llm_usage is not None:
                # Langfuse expects usage_details, not usage
                # Convert keys to match Langfuse format if needed
                usage_details = self._llm_usage.copy()
                update_kwargs["usage_details"] = usage_details

            if self._llm_model is not None:
                update_kwargs["model"] = self._llm_model

            if update_kwargs:
                try:
                    self._langfuse_generation.update(**update_kwargs)
                    self._llm_data_finalized = True
                except Exception as e:
                    logger.warning(
                        f"Failed to update Langfuse generation with LLM data: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to finalize Langfuse LLM data: {e}")


def _sanitize_attribute(value: Any) -> Any:
    """Sanitize attribute value for OTEL (must be primitive type)."""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_sanitize_attribute(v) for v in value]
    if isinstance(value, dict):
        return str(value)  # OTEL doesn't support nested dicts
    return str(value)


# Global tracer instance (lazy initialization)
_global_tracer: LLMTracer | None = None


def get_tracer(
    *,
    enable_otel: bool = True,
    enable_langfuse: bool = False,
    enable_httpx_instrumentation: bool = False,
    langfuse_connection_timeout: float = 2.0,
    langfuse_enable_health_check: bool = True,
    **kwargs,
) -> LLMTracer:
    """
    Get or create the global LLM tracer.

    Args:
        enable_otel: Enable OpenTelemetry tracing
        enable_langfuse: Enable Langfuse observability
        enable_httpx_instrumentation: Enable global httpx instrumentation (default: False)
            WARNING: This instruments ALL httpx clients in the process, not just LLM calls
        langfuse_connection_timeout: Timeout in seconds for Langfuse connection health check
        langfuse_enable_health_check: Enable health check endpoint test before OTLP endpoint
        **kwargs: Additional tracer configuration (langfuse_public_key, langfuse_secret_key, etc.)

    Returns:
        Global LLMTracer instance
    """
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = LLMTracer(
            enable_otel=enable_otel,
            enable_langfuse=enable_langfuse,
            enable_httpx_instrumentation=enable_httpx_instrumentation,
            langfuse_connection_timeout=langfuse_connection_timeout,
            langfuse_enable_health_check=langfuse_enable_health_check,
            **kwargs,
        )
    return _global_tracer


def reset_tracer() -> None:
    """Reset the global tracer (mainly for testing)."""
    global _global_tracer
    if _global_tracer:
        _global_tracer.shutdown()
    _global_tracer = None


def uninstrument_httpx() -> None:
    """
    Uninstrument httpx globally.

    Call this if httpx was instrumented by a previous run and is causing issues.
    This is a workaround for when OpenTelemetry httpx instrumentation
    interferes with normal HTTP requests.
    """
    if OTEL_AVAILABLE:
        try:
            HTTPXClientInstrumentor().uninstrument()
            logger.info("HTTPX globally uninstrumented")
        except Exception as e:
            logger.debug(f"Attempted to uninstrument HTTPX: {e}")


__all__ = [
    "LLMTracer",
    "SpanContext",
    "get_tracer",
    "reset_tracer",
    "uninstrument_httpx",
    "OTEL_AVAILABLE",
    "LANGFUSE_AVAILABLE",
]
