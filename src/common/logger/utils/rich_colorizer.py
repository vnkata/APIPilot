"""
Rich-based colorization for console output

Uses semantic ANSI color codes for VSCode Dark theme style
"""

import re
from typing import Optional

# Check Rich availability (not strictly required anymore, using direct ANSI)
try:
    from rich.console import Console

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class RichColorizer:
    """Colorize data structures using ANSI color codes"""

    # ANSI color codes (VSCode Dark theme semantic coloring)
    CYAN = "\033[36m"  # Keys (identifiers)
    GREEN = "\033[32m"  # String values
    YELLOW = "\033[33m"  # Numbers
    MAGENTA = "\033[35m"  # Booleans
    RED_DIM = "\033[2;31m"  # None/null/special
    DIM = "\033[2m"  # Brackets/punctuation
    RESET = "\033[0m"  # Reset all

    def __init__(self):
        """Initialize colorizer"""
        self.enabled = True  # Always enabled since we use ANSI directly

    def colorize(self, text: str, indent: int = 0) -> str:
        """
        Colorize a formatted text (dict/list/tuple structure)

        Args:
            text: Plain text representation (already formatted)
            indent: Additional indentation level

        Returns:
            Colorized text with ANSI codes
        """
        if not self.enabled or not text:
            return text

        try:
            # Simple line-by-line colorization to preserve formatting
            return self._colorize_lines(text)

        except Exception:
            # Fallback: return plain text if colorization fails
            return text

    def _colorize_lines(self, text: str) -> str:
        """
        Colorize text line by line using simple regex patterns

        This preserves the existing formatting while adding colors
        """

        # ANSI color codes (semantic coloring)
        CYAN = "\033[36m"  # Keys
        GREEN = "\033[32m"  # Strings
        YELLOW = "\033[33m"  # Numbers
        MAGENTA = "\033[35m"  # Booleans
        RED_DIM = "\033[2;31m"  # None/null
        DIM = "\033[2m"  # Brackets/punctuation
        RESET = "\033[0m"

        lines = text.split("\n")
        colorized_lines = []

        for line in lines:
            # Skip empty lines
            if not line.strip():
                colorized_lines.append(line)
                continue

            colorized = line

            # Colorize JSON keys (anything in quotes followed by colon)
            # e.g., "name": value
            colorized = re.sub(
                r'("[\w_-]+")(:)',
                rf"{CYAN}\1{RESET}{DIM}\2{RESET}",
                colorized,
            )

            # Colorize string values (in quotes, not followed by colon)
            # e.g., "Alice", "2025-10-26"
            colorized = re.sub(
                r'(?<!:)\s+("[\w\s\-:\.@!#$%^&*()+=\[\]{}|;,<>?/~`]+")(?=[,\s\]\}]|$)',
                rf" {GREEN}\1{RESET}",
                colorized,
            )

            # Colorize numbers (integers and floats)
            colorized = re.sub(
                r"\b(\d+\.?\d*)\b(?=[,\s\]\}]|$)",
                rf"{YELLOW}\1{RESET}",
                colorized,
            )

            # Colorize booleans
            colorized = re.sub(
                r"\b(true|false)\b",
                rf"{MAGENTA}\1{RESET}",
                colorized,
                flags=re.IGNORECASE,
            )

            # Colorize None/null
            colorized = re.sub(
                r"\b(null|None)\b",
                rf"{RED_DIM}\1{RESET}",
                colorized,
            )

            # Colorize brackets/braces (dim)
            colorized = re.sub(
                r"([\[\]\{\}\(\),])",
                rf"{DIM}\1{RESET}",
                colorized,
            )

            # Colorize special values
            colorized = re.sub(
                r"(<circular_ref>|<[\w\s]+>)",
                rf"{RED_DIM}\1{RESET}",
                colorized,
            )

            # Colorize ellipsis and truncation messages
            colorized = re.sub(
                r'(\.\.\.|"\.\.\.[\w\s]+"|\.\.\.[\w\s<>:]+)',
                rf"{DIM}\1{RESET}",
                colorized,
            )

            colorized_lines.append(colorized)

        return "\n".join(colorized_lines)

    def _pythonify_to_json(self, text: str) -> str:
        """Legacy method - no longer used"""
        return text

    def colorize_key_value(
        self, key: str, value: str, indent: int = 2
    ) -> tuple[str, str]:
        """Legacy method - no longer used"""
        return key, value

    def _colorize_value(self, value: str) -> str:
        """Legacy method - no longer used"""
        return value


# Global singleton instance
_colorizer: RichColorizer | None = None


def get_colorizer() -> RichColorizer:
    """Get global RichColorizer instance (singleton)"""
    global _colorizer
    if _colorizer is None:
        _colorizer = RichColorizer()
    return _colorizer


def colorize_for_console(text: str, indent: int = 0) -> str:
    """
    Convenience function to colorize text for console

    Args:
        text: Plain text to colorize
        indent: Indentation level (currently unused)

    Returns:
        Colorized text with ANSI codes
    """
    colorizer = get_colorizer()
    return colorizer.colorize(text, indent)


def is_colorization_available() -> bool:
    """Check if colorization is available (always True with ANSI)"""
    return True
