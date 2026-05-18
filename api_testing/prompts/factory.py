from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Type

from api_testing.config.config_loader import build_llm_from_config, deep_merge


class PromptFactory:
    """Creates prompt wrappers with class-specific LLM config fallback."""

    def __init__(self, common_llm: Any, prompt_llms: Dict[str, Any] | None = None):
        self.common_llm = common_llm
        self.prompt_llms = prompt_llms or {}

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "PromptFactory":
        common_config = deepcopy(config["llm"])
        prompt_overrides = common_config.pop("prompts", {}) or {}
        common_llm = build_llm_from_config(common_config)

        prompt_llms = {}
        for class_name, override in prompt_overrides.items():
            merged_config = deep_merge(common_config, override)
            merged_config.pop("prompts", None)
            prompt_llms[class_name] = build_llm_from_config(merged_config)

        return cls(common_llm=common_llm, prompt_llms=prompt_llms)

    def get_llm(self, prompt_cls_or_name: Type[Any] | str) -> Any:
        class_name = (
            prompt_cls_or_name
            if isinstance(prompt_cls_or_name, str)
            else prompt_cls_or_name.__name__
        )
        return self.prompt_llms.get(class_name, self.common_llm)

    def create(self, prompt_cls: Type[Any], *args: Any, **kwargs: Any) -> Any:
        kwargs.setdefault("llm", self.get_llm(prompt_cls))
        return prompt_cls(*args, **kwargs)
