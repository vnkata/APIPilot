"""
Structured Output Extraction Utilities

Generic utilities for extracting and validating Pydantic models from raw LLM text outputs.
Handles common formats: JSON in markdown code blocks, plain JSON, embedded JSON.

Features:
- Multiple extraction strategies with fallbacks
- Robust regex patterns for nested JSON
- Text cleanup (trailing commas, comments)
- Detailed error messages
"""

import json
import re
from typing import Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from common.llm.exceptions import LLMValidationError
from common.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class ExtractionError(LLMValidationError):
    """Error raised when extraction or validation fails."""

    pass


class StructuredOutputExtractor(Generic[T]):
    """Generic extractor for Pydantic models from raw LLM text.

    Supports multiple JSON formats with robust fallback strategies:
    - Markdown code blocks: ```json {...} ```
    - Plain JSON: {...}
    - Embedded JSON in text
    - Handles nested structures
    - Cleans up common LLM output issues

    Features:
    - Multiple extraction patterns (greedy + non-greedy)
    - Text preprocessing (remove comments, trailing commas)
    - Type-safe with generics
    - Clear error messages with context
    - Logging for debugging

    Example:
        >>> from pydantic import BaseModel
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: int
        >>>
        >>> raw_text = '```json\\n{"name": "John", "age": 30}\\n```'
        >>> result = StructuredOutputExtractor.extract(raw_text, Person)
        >>> print(result.name, result.age)
        John 30
    """

    # Multiple regex patterns for different scenarios
    # Pattern 1: Markdown code block with greedy matching (best for nested JSON)
    MARKDOWN_GREEDY_PATTERN = re.compile(
        r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", re.DOTALL
    )

    # Pattern 2: Markdown code block with non-greedy (fallback)
    MARKDOWN_NON_GREEDY_PATTERN = re.compile(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL
    )

    # Pattern 3: Plain JSON with greedy matching
    PLAIN_GREEDY_PATTERN = re.compile(r"(\{[^`]*\}|\[[^`]*\])", re.DOTALL)

    # Pattern 4: Plain JSON non-greedy (last resort)
    PLAIN_NON_GREEDY_PATTERN = re.compile(r"(\{.*?\}|\[.*?\])", re.DOTALL)

    @staticmethod
    def _clean_json_text(text: str) -> str:
        """Clean up common JSON formatting issues from LLM output.

        Args:
            text: Raw JSON text

        Returns:
            Cleaned JSON text
        """
        # Remove C-style comments (// ...)
        text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)

        # Remove trailing commas before } or ]
        text = re.sub(r",\s*([}\]])", r"\1", text)

        # Normalize whitespace around braces
        text = text.strip()

        return text

    @staticmethod
    def _find_json_in_text(text: str) -> List[str]:
        """Find JSON string(s) in text using multiple extraction strategies.

        Tries patterns in order of specificity:
        1. Markdown code block (greedy) - best for nested JSON
        2. Markdown code block (non-greedy) - fallback
        3. Plain JSON (greedy) - for non-markdown responses
        4. Plain JSON (non-greedy) - last resort

        Args:
            text: Raw text that may contain JSON

        Returns:
            List of extracted JSON strings (empty if none found)
        """
        candidates: List[str] = []

        # Strategy 1: Markdown code block with greedy matching (best for nested)
        match = StructuredOutputExtractor.MARKDOWN_GREEDY_PATTERN.search(text)
        if match:
            json_str = match.group(1)
            candidates.append(json_str)
            logger.debug(
                f"Found JSON in markdown (greedy): length={len(json_str)}, "
                f"preview={json_str[:100]}"
            )

        # Strategy 2: Markdown non-greedy (may be different from greedy)
        match = StructuredOutputExtractor.MARKDOWN_NON_GREEDY_PATTERN.search(text)
        if match:
            json_str = match.group(1)
            if json_str not in candidates:  # Avoid duplicates
                candidates.append(json_str)
                logger.debug(
                    f"Found JSON in markdown (non-greedy): length={len(json_str)}"
                )

        # Strategy 3: Plain JSON greedy (no markdown)
        if not candidates:  # Only try if markdown didn't work
            match = StructuredOutputExtractor.PLAIN_GREEDY_PATTERN.search(text)
            if match:
                json_str = match.group(1)
                candidates.append(json_str)
                logger.debug(
                    f"Found plain JSON (greedy): length={len(json_str)}, "
                    f"preview={json_str[:100]}"
                )

        # Strategy 4: Plain JSON non-greedy (last resort)
        if not candidates:
            match = StructuredOutputExtractor.PLAIN_NON_GREEDY_PATTERN.search(text)
            if match:
                json_str = match.group(1)
                candidates.append(json_str)
                logger.debug(f"Found plain JSON (non-greedy): length={len(json_str)}")

        if not candidates:
            logger.debug("No JSON found in text")

        return candidates

    @staticmethod
    def _parse_json(json_str: str, attempt: int = 1) -> Optional[Dict]:
        """Parse JSON string with error handling and cleanup attempts.

        Args:
            json_str: JSON string to parse
            attempt: Attempt number (for logging)

        Returns:
            Parsed dictionary or None if parsing fails

        Raises:
            ExtractionError: If JSON parsing fails after all cleanup attempts
        """
        try:
            # Clean before parsing
            cleaned = StructuredOutputExtractor._clean_json_text(json_str)
            parsed = json.loads(cleaned)

            if attempt > 1:
                logger.info(f"JSON parsing succeeded after cleanup (attempt {attempt})")

            return parsed

        except json.JSONDecodeError as e:
            # Provide helpful error message with context
            lines = json_str.split("\n")
            error_line = (
                lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else "N/A"
            )

            # Show context: 2 lines before and after error
            start_line = max(0, e.lineno - 3) if e.lineno else 0
            end_line = min(len(lines), e.lineno + 2) if e.lineno else len(lines)
            context_lines = lines[start_line:end_line]
            context = "\n".join(
                f"  {i+start_line+1}: {line}" for i, line in enumerate(context_lines)
            )

            logger.error(
                f"JSON parsing failed (attempt {attempt}) at line {e.lineno}, "
                f"column {e.colno}: {e.msg}",
                extra={
                    "error_line": error_line,
                    "json_preview": json_str[:300],
                    "context": context,
                },
            )

            # Raise with detailed context
            raise ExtractionError(
                f"Failed to parse JSON at line {e.lineno}, col {e.colno}: {e.msg}\n"
                f"Error line: {error_line}\n"
                f"Context:\n{context}",
                provider="extractor",
                model="json_parser",
            ) from e

    @staticmethod
    def extract(raw_text: str, model_class: Type[T], strict: bool = True) -> T:
        """Extract and validate Pydantic model from raw text.

        Uses multiple extraction strategies and tries all candidates:
        1. Find JSON using multiple regex patterns
        2. Try parsing each candidate with cleanup
        3. Validate with Pydantic model
        4. Return first successful extraction

        Args:
            raw_text: Raw LLM output text
            model_class: Target Pydantic model class
            strict: If True, raise on validation errors; if False, log and return None

        Returns:
            Validated Pydantic model instance

        Raises:
            ExtractionError: If parsing or validation fails (when strict=True)

        Example:
            >>> class Config(BaseModel):
            ...     enabled: bool
            ...     timeout: int
            >>>
            >>> text = "Here's the config: ```json\\n{\"enabled\": true, \"timeout\": 30}\\n```"
            >>> config = StructuredOutputExtractor.extract(text, Config)
            >>> assert config.enabled is True
        """
        # Step 1: Find JSON candidates in text
        candidates = StructuredOutputExtractor._find_json_in_text(raw_text)

        if not candidates:
            error_msg = (
                f"No JSON found in text. Model: {model_class.__name__}. "
                f"Text preview: {raw_text[:300]}"
            )
            logger.error(error_msg)
            if strict:
                raise ExtractionError(
                    error_msg, provider="extractor", model="json_finder"
                )
            return None  # type: ignore

        logger.debug(
            f"Found {len(candidates)} JSON candidate(s) for {model_class.__name__}"
        )

        # Step 2 & 3: Try parsing and validating each candidate
        errors: List[str] = []

        for attempt, json_str in enumerate(candidates, start=1):
            try:
                # Parse JSON
                data = StructuredOutputExtractor._parse_json(json_str, attempt=attempt)
                if data is None:
                    continue

                # Validate with Pydantic
                try:
                    model_instance = model_class(**data)
                    logger.info(
                        f"Successfully extracted {model_class.__name__} "
                        f"(attempt {attempt}/{len(candidates)})",
                        extra={
                            "model": model_class.__name__,
                            "data_keys": list(data.keys()),
                            "attempt": attempt,
                        },
                    )
                    return model_instance

                except ValidationError as e:
                    error_msg = f"Attempt {attempt}: Validation failed - {e.error_count()} error(s)"
                    errors.append(error_msg)
                    logger.warning(
                        error_msg,
                        extra={
                            "model": model_class.__name__,
                            "errors": e.errors(),
                            "data": data,
                            "attempt": attempt,
                        },
                    )
                    continue  # Try next candidate

            except ExtractionError as e:
                error_msg = f"Attempt {attempt}: Parsing failed - {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue  # Try next candidate

            except Exception as e:
                error_msg = f"Attempt {attempt}: Unexpected error - {str(e)}"
                errors.append(error_msg)
                logger.warning(
                    error_msg,
                    extra={
                        "model": model_class.__name__,
                        "error": str(e),
                        "attempt": attempt,
                    },
                )
                continue  # Try next candidate

        # All attempts failed
        all_errors = "; ".join(errors)
        final_error_msg = (
            f"All {len(candidates)} extraction attempt(s) failed for {model_class.__name__}. "
            f"Errors: {all_errors}"
        )
        logger.error(
            final_error_msg,
            extra={
                "model": model_class.__name__,
                "candidates_count": len(candidates),
                "errors": errors,
            },
        )

        if strict:
            raise ExtractionError(
                final_error_msg, provider="extractor", model=model_class.__name__
            )
        return None  # type: ignore


__all__ = ["StructuredOutputExtractor", "ExtractionError"]
