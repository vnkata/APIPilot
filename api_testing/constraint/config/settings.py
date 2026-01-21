"""
Hierarchical settings for constraint extraction pipeline.

Uses pydantic_settings for configuration management with:
- Default values in code
- Config file (constraint_config.yaml) overrides
- Environment variable overrides (highest priority)
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource
from typing import Optional
from pathlib import Path


class HeuristicStepSettings(BaseModel):
    """Settings for heuristic extraction step.

    Heuristic extraction combines structural constraints from schema
    and description-based constraints using pattern matching.
    """

    enabled: bool = Field(default=True, description="Enable heuristic extraction")
    structural: bool = Field(
        default=True,
        description="Extract structural constraints from schema (enum, range, format, etc.)",
    )
    description: bool = Field(
        default=True,
        description="Extract constraints from field descriptions using pattern catalog",
    )
    use_llm_for_description: bool = Field(
        default=True,
        description="Use LLM fallback when description patterns don't match",
    )

    @field_validator("use_llm_for_description")
    @classmethod
    def validate_llm_requires_description(cls, v, info):
        """LLM description extraction requires description extraction to be enabled."""
        if v and not info.data.get("description", True):
            raise ValueError(
                "use_llm_for_description requires description extraction to be enabled. "
                "Set description=true or use_llm_for_description=false."
            )
        return v


class CoverageCheckStepSettings(BaseModel):
    """Settings for LLM-based coverage check step.

    Coverage check uses LLM to analyze if heuristic results
    sufficiently cover all constraints in the description.
    """

    enabled: bool = Field(
        default=True, description="Enable coverage check to detect missing constraints"
    )


class LLMExtractionStepSettings(BaseModel):
    """Settings for LLM extraction step.

    LLM extraction fills gaps identified by coverage check,
    extracting constraints that couldn't be captured heuristically.
    """

    enabled: bool = Field(
        default=True, description="Enable LLM extraction for missing constraints"
    )
    allow_suggestions: bool = Field(
        default=True,
        description="Allow LLM to suggest new predicate types for unmatched constraints",
    )


class SingleFieldAnalyzerSettings(BaseModel):
    """Settings for single-field response property analyzer.

    Extracts constraints on individual response fields through
    a 3-phase pipeline: heuristic → coverage check → LLM extraction.
    """

    enabled: bool = Field(default=True, description="Enable single-field analyzer")
    heuristic: HeuristicStepSettings = Field(
        default_factory=HeuristicStepSettings,
        description="Heuristic extraction settings",
    )
    coverage_check: CoverageCheckStepSettings = Field(
        default_factory=CoverageCheckStepSettings, description="Coverage check settings"
    )
    llm_extraction: LLMExtractionStepSettings = Field(
        default_factory=LLMExtractionStepSettings, description="LLM extraction settings"
    )

    @model_validator(mode="after")
    def validate_step_dependencies(self):
        """Validate logical dependencies between steps.

        Rules:
        - Coverage check requires heuristic (needs results to analyze)
        - LLM extraction requires coverage check (needs gap detection)
        """
        if not self.enabled:
            return self

        # Coverage check requires heuristic
        if self.coverage_check.enabled and not self.heuristic.enabled:
            raise ValueError(
                "SingleFieldAnalyzer: coverage_check requires heuristic to be enabled. "
                "Coverage check analyzes heuristic results to detect gaps. "
                "Either enable heuristic or disable coverage_check."
            )

        # LLM extraction requires coverage check
        if self.llm_extraction.enabled and not self.coverage_check.enabled:
            raise ValueError(
                "SingleFieldAnalyzer: llm_extraction requires coverage_check to be enabled. "
                "LLM extraction fills gaps identified by coverage check. "
                "Either enable coverage_check or disable llm_extraction."
            )

        return self


class CrossFieldAnalyzerSettings(BaseModel):
    """Settings for cross-field response constraint analyzer.

    Detects relationships between multiple fields in response schemas
    (e.g., field dependencies, mutual exclusivity, conditional constraints).
    """

    enabled: bool = Field(default=True, description="Enable cross-field analyzer")
    heuristic: bool = Field(
        default=True, description="Enable heuristic cross-field pattern extraction"
    )
    coverage_check: bool = Field(
        default=True, description="Enable coverage check for cross-field relationships"
    )
    llm_extraction: bool = Field(
        default=True, description="Enable LLM extraction for missing relationships"
    )

    @model_validator(mode="after")
    def validate_step_dependencies(self):
        """Validate logical dependencies between steps."""
        if not self.enabled:
            return self

        # Coverage check requires heuristic
        if self.coverage_check and not self.heuristic:
            raise ValueError(
                "CrossFieldAnalyzer: coverage_check requires heuristic to be enabled. "
                "Either enable heuristic or disable coverage_check."
            )

        # LLM extraction requires coverage check
        if self.llm_extraction and not self.coverage_check:
            raise ValueError(
                "CrossFieldAnalyzer: llm_extraction requires coverage_check to be enabled. "
                "Either enable coverage_check or disable llm_extraction."
            )

        return self


class RequestResponseAnalyzerSettings(BaseModel):
    """Settings for request-response constraint analyzer.

    Identifies constraints between request parameters and response properties
    (e.g., filtering, pagination, sorting, projection, echo/identity).
    """

    enabled: bool = Field(default=True, description="Enable request-response analyzer")
    heuristic: bool = Field(
        default=True, description="Enable heuristic request-response pattern extraction"
    )
    coverage_check: bool = Field(
        default=True, description="Enable coverage check for parameter mappings"
    )
    llm_extraction: bool = Field(
        default=True, description="Enable LLM extraction for unmatched parameters"
    )

    @model_validator(mode="after")
    def validate_step_dependencies(self):
        """Validate logical dependencies between steps."""
        if not self.enabled:
            return self

        # Coverage check requires heuristic
        if self.coverage_check and not self.heuristic:
            raise ValueError(
                "RequestResponseAnalyzer: coverage_check requires heuristic to be enabled. "
                "Either enable heuristic or disable coverage_check."
            )

        # LLM extraction requires coverage check
        if self.llm_extraction and not self.coverage_check:
            raise ValueError(
                "RequestResponseAnalyzer: llm_extraction requires coverage_check to be enabled. "
                "Either enable coverage_check or disable llm_extraction."
            )

        return self


class ConstraintExtractionSettings(BaseSettings):
    """Main settings for constraint extraction pipeline.

    Configuration priority (highest to lowest):
    1. Environment variables (e.g., CONSTRAINT_SINGLE_FIELD__ENABLED=false)
    2. Config file (constraint_config.yaml in current directory)
    3. Default values defined in code

    Environment variable format:
    - Use double underscores for nesting: CONSTRAINT_SINGLE_FIELD__ENABLED
    - Use triple underscores for nested objects: CONSTRAINT_SINGLE_FIELD__HEURISTIC__STRUCTURAL
    - Case insensitive: constraint_batch_size or CONSTRAINT_BATCH_SIZE both work

    Example:
        # Disable single-field analyzer
        CONSTRAINT_SINGLE_FIELD__ENABLED=false

        # Disable LLM features only
        CONSTRAINT_SINGLE_FIELD__COVERAGE_CHECK__ENABLED=false
        CONSTRAINT_SINGLE_FIELD__LLM_EXTRACTION__ENABLED=false

        # Adjust batch size
        CONSTRAINT_BATCH_SIZE=20
    """

    model_config = SettingsConfigDict(
        env_prefix="CONSTRAINT_",
        env_nested_delimiter="__",
        yaml_file="constraint_config.yaml",
        yaml_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    # Analyzer settings
    single_field: SingleFieldAnalyzerSettings = Field(
        default_factory=SingleFieldAnalyzerSettings,
        description="Single-field response property analyzer settings",
    )
    crossfield_response: CrossFieldAnalyzerSettings = Field(
        default_factory=CrossFieldAnalyzerSettings,
        description="Cross-field response constraint analyzer settings",
    )
    request_response: RequestResponseAnalyzerSettings = Field(
        default_factory=RequestResponseAnalyzerSettings,
        description="Request-response constraint analyzer settings",
    )

    # Global settings
    save_intermediate: bool = Field(
        default=True,
        description="Save intermediate outputs per operation for debugging",
    )
    use_schema_cache: bool = Field(
        default=True,
        description="Use schema-level caching to avoid redundant extraction",
    )
    batch_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Batch size for parallel schema processing",
    )

    @model_validator(mode="after")
    def validate_at_least_one_analyzer(self):
        """Ensure at least one analyzer is enabled."""
        if not any(
            [
                self.single_field.enabled,
                self.crossfield_response.enabled,
                self.request_response.enabled,
            ]
        ):
            raise ValueError(
                "At least one analyzer must be enabled. "
                "Set single_field.enabled, crossfield_response.enabled, or request_response.enabled to true."
            )
        return self

    def requires_llm(self) -> bool:
        """Check if any enabled feature requires LLM.

        Returns:
            True if LLM is needed for any enabled feature
        """
        llm_features = []

        if self.single_field.enabled:
            llm_features.extend(
                [
                    self.single_field.heuristic.use_llm_for_description,
                    self.single_field.coverage_check.enabled,
                    self.single_field.llm_extraction.enabled,
                ]
            )

        if self.crossfield_response.enabled:
            llm_features.extend(
                [
                    self.crossfield_response.coverage_check,
                    self.crossfield_response.llm_extraction,
                ]
            )

        if self.request_response.enabled:
            llm_features.extend(
                [
                    self.request_response.coverage_check,
                    self.request_response.llm_extraction,
                ]
            )

        return any(llm_features)

    def get_summary(self) -> dict:
        """Get human-readable summary of active settings.

        Returns:
            Dictionary with summary of enabled features
        """
        summary = {
            "analyzers": {},
            "global": {
                "save_intermediate": self.save_intermediate,
                "use_schema_cache": self.use_schema_cache,
                "batch_size": self.batch_size,
            },
            "requires_llm": self.requires_llm(),
        }

        if self.single_field.enabled:
            summary["analyzers"]["single_field"] = {
                "enabled": True,
                "heuristic": self.single_field.heuristic.enabled,
                "coverage_check": self.single_field.coverage_check.enabled,
                "llm_extraction": self.single_field.llm_extraction.enabled,
            }

        if self.crossfield_response.enabled:
            summary["analyzers"]["crossfield_response"] = {
                "enabled": True,
                "heuristic": self.crossfield_response.heuristic,
                "coverage_check": self.crossfield_response.coverage_check,
                "llm_extraction": self.crossfield_response.llm_extraction,
            }

        if self.request_response.enabled:
            summary["analyzers"]["request_response"] = {
                "enabled": True,
                "heuristic": self.request_response.heuristic,
                "coverage_check": self.request_response.coverage_check,
                "llm_extraction": self.request_response.llm_extraction,
            }

        return summary


# Singleton pattern for settings
_settings_instance: Optional[ConstraintExtractionSettings] = None


def get_constraint_settings(
    config_file: Optional[Path] = None, reload: bool = False
) -> ConstraintExtractionSettings:
    """Get or create constraint extraction settings instance.

    Uses singleton pattern to ensure consistent settings across application.

    Args:
        config_file: Optional path to YAML config file (overrides default)
        reload: Force reload settings (useful for testing)

    Returns:
        ConstraintExtractionSettings instance

    Example:
        # Load default settings
        settings = get_constraint_settings()

        # Load from specific file
        settings = get_constraint_settings(Path("custom_config.yaml"))

        # Force reload (for testing)
        settings = get_constraint_settings(reload=True)
    """
    global _settings_instance

    if _settings_instance is None or reload:
        if config_file:
            # Load from specific file
            _settings_instance = ConstraintExtractionSettings(
                _env_file=str(config_file)
            )
        else:
            # Use default loading (env vars + default yaml if exists)
            _settings_instance = ConstraintExtractionSettings()

    return _settings_instance


__all__ = [
    "HeuristicStepSettings",
    "CoverageCheckStepSettings",
    "LLMExtractionStepSettings",
    "SingleFieldAnalyzerSettings",
    "CrossFieldAnalyzerSettings",
    "RequestResponseAnalyzerSettings",
    "ConstraintExtractionSettings",
    "get_constraint_settings",
]
