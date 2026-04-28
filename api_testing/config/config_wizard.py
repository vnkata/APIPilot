from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict

from .config_loader import DEFAULT_CONFIG, EMBEDDING_PROVIDERS, LLM_PROVIDERS


def _prompt_text(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or (default or "")


def _prompt_int(label: str, default: int) -> int:
    value = _prompt_text(label, str(default))
    return int(value)


def _prompt_float(label: str, default: float) -> float:
    value = _prompt_text(label, str(default))
    return float(value)


def _prompt_bool(label: str, default: bool) -> bool:
    default_str = "y" if default else "n"
    value = _prompt_text(f"{label} (y/n)", default_str).lower()
    return value in ("y", "yes", "true", "1")


def _prompt_choice(label: str, choices: list[str], default: str) -> str:
    choices_display = ", ".join(choices)
    value = _prompt_text(f"{label} ({choices_display})", default).lower()
    if value not in choices:
        raise ValueError(f"Invalid choice: {value}")
    return value


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _render_toml(config: Dict[str, Any]) -> str:
    lines: list[str] = []

    project = config["project"]
    lines.append("[project]")
    lines.append(f"spec_path = {_toml_value(project.get('spec_path', ''))}")
    lines.append(f"base_url = {_toml_value(project.get('base_url', ''))}")
    lines.append(f"base_title = {_toml_value(project.get('base_title', ''))}")
    lines.append("")

    llm = config["llm"]
    lines.append("[llm]")
    lines.append(f"provider = {_toml_value(llm.get('provider', ''))}")
    lines.append(f"model = {_toml_value(llm.get('model', ''))}")
    lines.append(f"temperature = {_toml_value(llm.get('temperature', 0.0))}")
    lines.append("")

    azure = llm.get("azure_openai", {})
    lines.append("[llm.azure_openai]")
    lines.append(f"api_key = {_toml_value(azure.get('api_key', ''))}")
    lines.append(f"endpoint = {_toml_value(azure.get('endpoint', ''))}")
    lines.append(f"api_version = {_toml_value(azure.get('api_version', ''))}")
    lines.append("")

    openai_cfg = llm.get("openai", {})
    lines.append("[llm.openai]")
    lines.append(f"api_key = {_toml_value(openai_cfg.get('api_key', ''))}")
    lines.append(f"base_url = {_toml_value(openai_cfg.get('base_url', ''))}")
    lines.append("")

    gemini = llm.get("gemini", {})
    lines.append("[llm.gemini]")
    lines.append(f"api_key = {_toml_value(gemini.get('api_key', ''))}")
    lines.append(f"project = {_toml_value(gemini.get('project', ''))}")
    lines.append(f"location = {_toml_value(gemini.get('location', ''))}")
    lines.append("")

    ollama = llm.get("ollama", {})
    lines.append("[llm.ollama]")
    lines.append(f"base_url = {_toml_value(ollama.get('base_url', ''))}")
    lines.append("")

    embedding = config["embedding"]
    lines.append("[embedding]")
    lines.append(f"provider = {_toml_value(embedding.get('provider', ''))}")
    lines.append(f"model = {_toml_value(embedding.get('model', ''))}")
    lines.append(f"use_half = {_toml_value(embedding.get('use_half', False))}")
    lines.append("")

    emb_ollama = embedding.get("ollama", {})
    lines.append("[embedding.ollama]")
    lines.append(f"base_url = {_toml_value(emb_ollama.get('base_url', ''))}")
    lines.append("")

    run = config["run"]
    lines.append("[run]")
    lines.append(f"num_generations = {_toml_value(run.get('num_generations', 1))}")
    lines.append(f"num_test_cases = {_toml_value(run.get('num_test_cases', 20))}")
    lines.append(f"mutation_ratio = {_toml_value(run.get('mutation_ratio', 0.0))}")
    lines.append(f"header_mutation_ratio = {_toml_value(run.get('header_mutation_ratio', 0.5))}")
    lines.append(f"async_mode = {_toml_value(run.get('async_mode', False))}")
    lines.append(f"max_request_workers = {_toml_value(run.get('max_request_workers', 10))}")
    lines.append(f"async_max_concurrent = {_toml_value(run.get('async_max_concurrent', 20))}")
    lines.append("")

    headers = config.get("headers", {})
    if headers:
        lines.append("[headers]")
        for key, value in headers.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")

    return "\n".join(lines)


def run_wizard(path: str, quick_mode: bool = False) -> Dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)

    config["project"]["spec_path"] = _prompt_text(
        "Spec path", config["project"]["spec_path"]
    )
    config["project"]["base_url"] = _prompt_text(
        "Base URL", config["project"]["base_url"]
    )
    config["project"]["base_title"] = _prompt_text(
        "Base title (optional)", config["project"]["base_title"]
    )

    provider = _prompt_choice(
        "LLM provider",
        sorted(LLM_PROVIDERS),
        config["llm"]["provider"],
    )
    config["llm"]["provider"] = provider
    config["llm"]["model"] = _prompt_text("LLM model/deployment", config["llm"]["model"])
    config["llm"]["temperature"] = _prompt_float("LLM temperature", config["llm"]["temperature"])

    if provider == "azure_openai":
        azure = config["llm"]["azure_openai"]
        azure["api_key"] = _prompt_text("Azure API key", azure["api_key"])
        azure["endpoint"] = _prompt_text("Azure endpoint", azure["endpoint"])
        azure["api_version"] = _prompt_text("Azure API version", azure["api_version"])
    elif provider == "openai":
        openai_cfg = config["llm"]["openai"]
        openai_cfg["api_key"] = _prompt_text("OpenAI API key", openai_cfg["api_key"])
        openai_cfg["base_url"] = _prompt_text("OpenAI base URL", openai_cfg["base_url"])
    elif provider == "gemini":
        gemini = config["llm"]["gemini"]
        gemini["api_key"] = _prompt_text("Gemini API key", gemini["api_key"])
        gemini["project"] = _prompt_text("Vertex project (optional)", gemini["project"])
        gemini["location"] = _prompt_text("Vertex location (optional)", gemini["location"])
    elif provider == "ollama":
        ollama = config["llm"]["ollama"]
        ollama["base_url"] = _prompt_text("Ollama base URL", ollama["base_url"])

    emb_provider = _prompt_choice(
        "Embedding provider",
        sorted(EMBEDDING_PROVIDERS),
        config["embedding"]["provider"],
    )
    config["embedding"]["provider"] = emb_provider
    config["embedding"]["model"] = _prompt_text(
        "Embedding model", config["embedding"]["model"]
    )
    config["embedding"]["use_half"] = _prompt_bool(
        "Use half precision", config["embedding"]["use_half"]
    )

    if emb_provider == "ollama":
        emb_ollama = config["embedding"]["ollama"]
        emb_ollama["base_url"] = _prompt_text(
            "Ollama embedding base URL", emb_ollama["base_url"]
        )

    if not quick_mode:
        run = config["run"]
        run["num_generations"] = _prompt_int("Num generations", run["num_generations"])
        run["num_test_cases"] = _prompt_int("Num test cases", run["num_test_cases"])
        run["mutation_ratio"] = _prompt_float("Mutation ratio", run["mutation_ratio"])
        run["header_mutation_ratio"] = _prompt_float(
            "Header mutation ratio", run["header_mutation_ratio"]
        )
        run["async_mode"] = _prompt_bool("Async mode", run["async_mode"])
        run["max_request_workers"] = _prompt_int(
            "Max request workers", run["max_request_workers"]
        )
        run["async_max_concurrent"] = _prompt_int(
            "Async max concurrent", run["async_max_concurrent"]
        )

    headers: Dict[str, str] = {}
    while True:
        key = _prompt_text("Header name (blank to finish)", "").strip()
        if not key:
            break
        value = _prompt_text(f"Header value for {key}", "")
        headers[key] = value
    config["headers"] = headers

    confirm = _prompt_bool("Write configuration to file", True)
    if not confirm:
        raise SystemExit("Configuration wizard cancelled")

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(_render_toml(config))

    print(f"Wrote configuration to {path}")
    return config
