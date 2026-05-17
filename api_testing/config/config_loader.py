from __future__ import annotations

import os
import re
from copy import deepcopy
from typing import Any, Dict

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

from api_testing.models.embedding_models.huggingface_embedding_model import (
    HuggingfaceEmbeddingModel,
)
from api_testing.models.embedding_models.ollama_embedding_model import (
    OllamaEmbeddingModel,
)
from api_testing.models.llms.azure_open_model import AzureOpenAIModel
from api_testing.models.llms.gemini_model import GeminiModel
from api_testing.models.llms.ollama_model import OllamaModel
from api_testing.models.llms.openai_model import OpenAIModel

ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")

LLM_PROVIDERS = {"azure_openai", "openai", "gemini", "ollama"}
EMBEDDING_PROVIDERS = {"huggingface", "ollama"}

DEFAULT_CONFIG: Dict[str, Any] = {
    "project": {
        "spec_path": "",
        "base_url": "",
        "base_title": "",
    },
    "llm": {
        "provider": "azure_openai",
        "model": "gpt-4.1-mini-2",
        "temperature": 0.7,
        "azure_openai": {
            "api_key": "${AZURE_OPENAI_API_KEY}",
            "endpoint": "${AZURE_OPENAI_ENDPOINT}",
            "api_version": "2024-12-01-preview",
        },
        "openai": {
            "api_key": "${OPENAI_API_KEY}",
            "base_url": "https://api.openai.com/v1",
        },
        "gemini": {
            "api_key": "${GOOGLE_API_KEY}",
            "project": "",
            "location": "",
        },
        "ollama": {
            "base_url": "http://localhost:11434",
        },
        "prompts": {},
    },
    "embedding": {
        "provider": "huggingface",
        "model": "google/embeddinggemma-300m",
        "use_half": False,
        "ollama": {
            "base_url": "http://localhost:11434",
        },
    },
    "run": {
        "num_generations": 1,
        "num_test_cases": 20,
        "mutation_ratio": 0.0,
        "header_mutation_ratio": 0.5,
        "async_mode": False,
        "debug": False,
        "max_request_workers": 10,
        "async_max_concurrent": 20,
    },
    "headers": {},
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _resolve_env_value(value: str) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        env_value = os.getenv(name)
        if env_value is None:
            return match.group(0)
        return env_value

    return ENV_PATTERN.sub(replace, value)


def _resolve_env(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: _resolve_env(value) for key, value in data.items()}
    if isinstance(data, list):
        return [_resolve_env(value) for value in data]
    if isinstance(data, str):
        return _resolve_env_value(data)
    return data


def resolve_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    return _resolve_env(config)


def _is_unresolved_placeholder(value: str) -> bool:
    return bool(ENV_PATTERN.search(value))


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, str) and _is_unresolved_placeholder(value):
        return True
    return False


def _require(value: Any, key_path: str) -> None:
    if _is_missing(value):
        raise ValueError(f"Missing required config: {key_path}")


def validate_config(config: Dict[str, Any]) -> None:
    llm = config.get("llm", {})
    _validate_llm_config(llm, "llm")

    prompts = llm.get("prompts", {})
    if prompts is not None and not isinstance(prompts, dict):
        raise ValueError("llm.prompts must be a table of prompt class overrides")
    for prompt_name, prompt_override in (prompts or {}).items():
        if not isinstance(prompt_override, dict):
            raise ValueError(f"llm.prompts.{prompt_name} must be a table")
        merged_llm = deep_merge(llm, prompt_override)
        merged_llm.pop("prompts", None)
        _validate_llm_config(merged_llm, f"llm.prompts.{prompt_name}")

    embedding = config.get("embedding", {})
    emb_provider = embedding.get("provider")
    _require(emb_provider, "embedding.provider")
    if emb_provider not in EMBEDDING_PROVIDERS:
        raise ValueError(f"Invalid embedding.provider: {emb_provider}")

    if emb_provider == "huggingface":
        _require(embedding.get("model"), "embedding.model")
    elif emb_provider == "ollama":
        _require(embedding.get("model"), "embedding.model")
        _require(embedding.get("ollama", {}).get("base_url"), "embedding.ollama.base_url")

    headers = config.get("headers")
    if headers is not None and not isinstance(headers, dict):
        raise ValueError("headers must be a table of key/value pairs")
    if isinstance(headers, dict):
        for name, value in headers.items():
            if isinstance(value, str) and _is_unresolved_placeholder(value):
                raise ValueError(f"Missing required config: headers.{name}")


def _validate_llm_config(llm: Dict[str, Any], key_prefix: str) -> None:
    provider = llm.get("provider")
    _require(provider, f"{key_prefix}.provider")
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Invalid {key_prefix}.provider: {provider}")
    _require(llm.get("model"), f"{key_prefix}.model")

    if provider == "azure_openai":
        azure = llm.get("azure_openai", {})
        _require(azure.get("api_key"), f"{key_prefix}.azure_openai.api_key")
        _require(azure.get("endpoint"), f"{key_prefix}.azure_openai.endpoint")
    elif provider == "openai":
        openai_cfg = llm.get("openai", {})
        _require(openai_cfg.get("api_key"), f"{key_prefix}.openai.api_key")
    elif provider == "gemini":
        gemini = llm.get("gemini", {})
        api_key = gemini.get("api_key")
        project = gemini.get("project")
        location = gemini.get("location")
        has_vertex = not _is_missing(project) and not _is_missing(location)
        if _is_missing(api_key) and not has_vertex:
            raise ValueError(f"Missing required config: {key_prefix}.gemini.api_key")
        if not _is_missing(project) or not _is_missing(location):
            _require(project, f"{key_prefix}.gemini.project")
            _require(location, f"{key_prefix}.gemini.location")
    elif provider == "ollama":
        ollama = llm.get("ollama", {})
        _require(ollama.get("base_url"), f"{key_prefix}.ollama.base_url")


def load_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Config file not found: {path}. Run with --init-config to create one."
        )

    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    merged = deep_merge(DEFAULT_CONFIG, data)
    resolved = resolve_env_vars(merged)
    validate_config(resolved)
    return resolved


def build_llm(config: Dict[str, Any]):
    llm = config["llm"]
    return build_llm_from_config(llm)


def build_llm_from_config(llm: Dict[str, Any]):
    provider = llm["provider"]
    temperature = float(llm.get("temperature", 0.0))
    model = llm["model"]

    if provider == "azure_openai":
        azure = llm.get("azure_openai", {})
        return AzureOpenAIModel(
            model=model,
            api_key=azure.get("api_key"),
            endpoint=azure.get("endpoint"),
            api_version=azure.get("api_version"),
            temperature=temperature,
        )
    if provider == "openai":
        openai_cfg = llm.get("openai", {})
        return OpenAIModel(
            model=model,
            api_key=openai_cfg.get("api_key"),
            base_url=openai_cfg.get("base_url"),
            temperature=temperature,
        )
    if provider == "gemini":
        gemini = llm.get("gemini", {})
        return GeminiModel(
            model_name=model,
            api_key=gemini.get("api_key"),
            project=gemini.get("project") or None,
            location=gemini.get("location") or None,
            temperature=temperature,
        )
    if provider == "ollama":
        ollama = llm.get("ollama", {})
        return OllamaModel(
            model=model,
            base_url=ollama.get("base_url"),
            temperature=temperature,
        )
    raise ValueError(f"Unsupported llm.provider: {provider}")


def build_embedder(config: Dict[str, Any]):
    embedding = config["embedding"]
    provider = embedding["provider"]
    model = embedding.get("model")

    if provider == "huggingface":
        return HuggingfaceEmbeddingModel(
            model=model,
            use_half=bool(embedding.get("use_half", False)),
        )
    if provider == "ollama":
        ollama_cfg = embedding.get("ollama", {})
        return OllamaEmbeddingModel(
            base_url=ollama_cfg.get("base_url"),
            model_name=model,
        )

    raise ValueError(f"Unsupported embedding.provider: {provider}")


def apply_cli_overrides(config: Dict[str, Any], args) -> Dict[str, Any]:
    result = deepcopy(config)

    if getattr(args, "spec", None):
        result["project"]["spec_path"] = args.spec

    run = result["run"]
    if getattr(args, "generations", None) is not None:
        run["num_generations"] = args.generations
    if getattr(args, "test_cases", None) is not None:
        run["num_test_cases"] = args.test_cases
    if getattr(args, "mutation_ratio", None) is not None:
        run["mutation_ratio"] = args.mutation_ratio
    if getattr(args, "header_mutation_ratio", None) is not None:
        run["header_mutation_ratio"] = args.header_mutation_ratio
    if getattr(args, "async_mode", None) is not None:
        run["async_mode"] = args.async_mode
    if getattr(args, "max_workers", None) is not None:
        run["max_request_workers"] = args.max_workers
    if getattr(args, "async_max_concurrent", None) is not None:
        run["async_max_concurrent"] = args.async_max_concurrent

    return result
