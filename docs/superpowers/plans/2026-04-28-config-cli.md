# Config-Driven CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a TOML config-driven CLI with a simple wizard, then run APITesting using those settings.

**Architecture:** Implement a small config subsystem (`config_loader` + `config_wizard`) and wire it into the CLI flow in `api_testing/__init__.py`. Update the runtime to accept configurable default headers and provide a root `configurations.toml` template plus a config-based `demo.py`.

**Tech Stack:** Python, argparse, tomllib/tomli, dotenv

**Note:** Git commits are listed per step but should only be executed if the user explicitly requests them.

---

## File Structure

- Create: `api_testing/config/__init__.py`
- Create: `api_testing/config/config_loader.py`
- Create: `api_testing/config/config_wizard.py`
- Create: `api_testing/__main__.py`
- Create: `configurations.toml`
- Create: `tests/test_config_loader.py`
- Modify: `requirements.txt`
- Modify: `api_testing/__init__.py`
- Modify: `api_testing/generators/executor.py`
- Modify: `demo.py`

---

### Task 1: Add failing tests for config loader

**Files:**
- Create: `tests/test_config_loader.py`

- [ ] **Step 1: Write failing tests**

```python
import textwrap
import pytest

from api_testing.config.config_loader import load_config


def _write_config(path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_load_config_resolves_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    content = """
    [project]
    spec_path = "datasets/Test.json"
    base_url = "http://localhost:9999"

    [llm]
    provider = "openai"
    model = "gpt-4o-mini"
    temperature = 0.1

    [llm.openai]
    api_key = "${OPENAI_API_KEY}"
    base_url = "https://api.openai.com/v1"

    [embedding]
    provider = "huggingface"
    model = "google/embeddinggemma-300m"
    use_half = false

    [run]
    num_generations = 1
    num_test_cases = 2
    mutation_ratio = 0.0
    header_mutation_ratio = 0.5
    async_mode = false
    max_request_workers = 1
    async_max_concurrent = 1

    [headers]
    Authorization = "Bearer ${OPENAI_API_KEY}"
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    config = load_config(str(path))

    assert config["llm"]["openai"]["api_key"] == "test-key"
    assert config["headers"]["Authorization"] == "Bearer test-key"


def test_missing_required_llm_fields(tmp_path):
    content = """
    [project]
    spec_path = "datasets/Test.json"
    base_url = "http://localhost:9999"

    [llm]
    provider = "openai"
    model = "gpt-4o-mini"
    temperature = 0.1

    [embedding]
    provider = "huggingface"
    model = "google/embeddinggemma-300m"
    use_half = false

    [run]
    num_generations = 1
    num_test_cases = 2
    mutation_ratio = 0.0
    header_mutation_ratio = 0.5
    async_mode = false
    max_request_workers = 1
    async_max_concurrent = 1
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    with pytest.raises(ValueError, match="llm.openai.api_key"):
        load_config(str(path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_loader.py -v`

Expected: FAIL (module import error for `api_testing.config`)

- [ ] **Step 3: Commit (if requested)**

```bash
git add tests/test_config_loader.py
git commit -m "test: add config loader coverage"
```

---

### Task 2: Implement config loader and defaults

**Files:**
- Create: `api_testing/config/__init__.py`
- Create: `api_testing/config/config_loader.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Create config package init**

```python
from .config_loader import (
    DEFAULT_CONFIG,
    apply_cli_overrides,
    build_embedder,
    build_llm,
    load_config,
)

__all__ = [
    "DEFAULT_CONFIG",
    "apply_cli_overrides",
    "build_embedder",
    "build_llm",
    "load_config",
]
```

- [ ] **Step 2: Implement config loader**

```python
from __future__ import annotations

import os
import re
from copy import deepcopy
from typing import Any, Dict

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib

from api_testing.models.llms.azure_open_model import AzureOpenAIModel
from api_testing.models.llms.openai_model import OpenAIModel
from api_testing.models.llms.gemini_model import GeminiModel
from api_testing.models.llms.ollama_model import OllamaModel
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel
from api_testing.models.embedding_models.ollama_embedding_model import OllamaEmbeddingModel

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
        "model": "gpt-4.1-mini",
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


def _resolve_env_value(value: str, missing: set[str]) -> str:
    def replace(match: re.Match) -> str:
        name = match.group(1)
        env_value = os.getenv(name)
        if env_value is None:
            missing.add(name)
            return match.group(0)
        return env_value

    return ENV_PATTERN.sub(replace, value)


def _resolve_env(data: Any, missing: set[str]) -> Any:
    if isinstance(data, dict):
        return {key: _resolve_env(value, missing) for key, value in data.items()}
    if isinstance(data, list):
        return [_resolve_env(value, missing) for value in data]
    if isinstance(data, str):
        return _resolve_env_value(data, missing)
    return data


def resolve_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    missing: set[str] = set()
    resolved = _resolve_env(config, missing)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"Missing environment variables: {missing_list}")
    return resolved


def _require(value: Any, key_path: str) -> None:
    if value is None:
        raise ValueError(f"Missing required config: {key_path}")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"Missing required config: {key_path}")


def validate_config(config: Dict[str, Any]) -> None:
    _require(config.get("project", {}).get("spec_path"), "project.spec_path")
    _require(config.get("project", {}).get("base_url"), "project.base_url")

    llm = config.get("llm", {})
    provider = llm.get("provider")
    _require(provider, "llm.provider")
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Invalid llm.provider: {provider}")
    _require(llm.get("model"), "llm.model")

    if provider == "azure_openai":
        azure = llm.get("azure_openai", {})
        _require(azure.get("api_key"), "llm.azure_openai.api_key")
        _require(azure.get("endpoint"), "llm.azure_openai.endpoint")
    elif provider == "openai":
        openai_cfg = llm.get("openai", {})
        _require(openai_cfg.get("api_key"), "llm.openai.api_key")
    elif provider == "gemini":
        gemini = llm.get("gemini", {})
        has_vertex = gemini.get("project") and gemini.get("location")
        if not gemini.get("api_key") and not has_vertex:
            raise ValueError("Missing required config: llm.gemini.api_key")
    elif provider == "ollama":
        ollama = llm.get("ollama", {})
        _require(ollama.get("base_url"), "llm.ollama.base_url")

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
```

- [ ] **Step 3: Add tomli fallback dependency**

```text
tomli
```

- [ ] **Step 4: Run tests to verify pass**

Run: `pytest tests/test_config_loader.py -v`

Expected: PASS

- [ ] **Step 5: Commit (if requested)**

```bash
git add requirements.txt api_testing/config/__init__.py api_testing/config/config_loader.py tests/test_config_loader.py
git commit -m "feat: add TOML config loader"
```

---

### Task 3: Implement config wizard and TOML writer

**Files:**
- Create: `api_testing/config/config_wizard.py`

- [ ] **Step 1: Implement wizard**

```python
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
    value = _prompt_text(label + " (y/n)", default_str).lower()
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
    return f"\"{escaped}\""


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
```

- [ ] **Step 2: Commit (if requested)**

```bash
git add api_testing/config/config_wizard.py
git commit -m "feat: add config wizard"
```

---

### Task 4: Wire CLI to config loader and wizard

**Files:**
- Create: `api_testing/__main__.py`
- Modify: `api_testing/__init__.py`

- [ ] **Step 1: Add CLI entrypoint**

```python
from api_testing import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update CLI args and orchestration**

```python
from dotenv import load_dotenv
from api_testing.config.config_loader import (
    apply_cli_overrides,
    build_embedder,
    build_llm,
    load_config,
)
from api_testing.config.config_wizard import run_wizard

def parse_args():
    parser = argparse.ArgumentParser(
        description="APITesting - Automated REST API Testing with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  apitesting                    # Run with wizard and write configurations.toml
  apitesting --init-config      # Create configurations.toml and exit
  apitesting --skip-wizard      # Use configurations.toml directly

For more information, visit: https://github.com/thanhtuit96/API-Testing
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configurations.toml (default: configurations.toml)",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Run the configuration wizard and exit",
    )
    parser.add_argument(
        "--skip-wizard",
        action="store_true",
        help="Skip configuration wizard and use configurations.toml directly",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick setup wizard (essential settings only)",
    )
    parser.add_argument(
        "-s",
        "--spec",
        type=str,
        default=None,
        help="Override specification path (relative to project root)",
    )
    parser.add_argument(
        "--async",
        dest="async_mode",
        action="store_true",
        default=None,
        help="Enable async HTTP requests for faster execution (uses httpx.AsyncClient)",
    )
    parser.add_argument(
        "--async-max-concurrent",
        type=int,
        default=None,
        help=f"Maximum concurrent async requests (default: {DEFAULT_ASYNC_MAX_CONCURRENT})",
    )
    parser.add_argument(
        "-g",
        "--generations",
        type=int,
        default=None,
        help="Number of test generations to run",
    )
    parser.add_argument(
        "-c",
        "--test-cases",
        type=int,
        default=None,
        help="Number of test cases per endpoint",
    )
    parser.add_argument(
        "--mutation-ratio",
        type=float,
        default=None,
        help="Ratio of mutated requests to induce 4xx errors",
    )
    parser.add_argument(
        "--header-mutation-ratio",
        type=float,
        default=None,
        help="Ratio of header mutations",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum concurrent request workers (default: auto)",
    )
    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    config_path = args.config or "configurations.toml"
    if args.init_config:
        run_wizard(config_path, quick_mode=args.quick)
        return

    if not args.skip_wizard:
        run_wizard(config_path, quick_mode=args.quick)

    config = load_config(config_path)
    config = apply_cli_overrides(config, args)

    llm = build_llm(config)
    embedder = build_embedder(config)
    headers = config.get("headers", {})

    tester = APITesting(
        base_url=config["project"]["base_url"],
        base_title=config["project"].get("base_title") or None,
        spec_path=config["project"]["spec_path"],
        model=llm,
        embedder=embedder,
    )

    run = config["run"]
    tester.run_tests(
        num_generations=run["num_generations"],
        num_test_cases=run["num_test_cases"],
        mutation_ratio=run["mutation_ratio"],
        header_mutation_ratio=run["header_mutation_ratio"],
        async_mode=run["async_mode"],
        max_request_workers=run["max_request_workers"],
        async_max_concurrent=run["async_max_concurrent"],
        headers=headers,
    )
```

- [ ] **Step 3: Commit (if requested)**

```bash
git add api_testing/__init__.py api_testing/__main__.py
git commit -m "feat: wire CLI to config wizard"
```

---

### Task 5: Pass default headers into request generation

**Files:**
- Modify: `api_testing/__init__.py`
- Modify: `api_testing/generators/executor.py`

- [ ] **Step 1: Update Executor to accept default headers**

```python
class Executor:
  def __init__(
      self,
      api_url: str = None,
      strategy: Strategy = Strategy.SMART_VALUE,
      operation: OperationProperties = None,
      cache_dir = None,
      model = None,
      configuration = None,
      num_test_cases = 1,
      context_pool = None,
      mutation_ratio = 0.1,
      header_mutation_ratio = 0.5,
      max_request_workers: int = DEFAULT_MAX_REQUEST_WORKERS,
      use_async: bool = False,
      async_max_concurrent: int = DEFAULT_ASYNC_MAX_CONCURRENT,
      default_headers: Optional[Dict[str, str]] = None,
  ):
    self.api_url = api_url
    self.strategy = strategy
    self.operation = operation
    self.cache_dir = cache_dir or "."
    self.model = model
    self.configuration = configuration
    self.use_async = use_async
    self.async_max_concurrent = async_max_concurrent
    self.default_headers = {str(k): str(v) for k, v in (default_headers or {}).items()}
```

- [ ] **Step 2: Merge default headers in request generation**

```python
      base_headers = {
          "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
          "Accept": "*/*",
      }
      headers = {**base_headers, **self.default_headers}
```

- [ ] **Step 3: Pass headers from APITesting.run_tests**

```python
    def run_tests(self, num_generations=1, num_test_cases=20, mutation_ratio=0.0, header_mutation_ratio=0.5,
                  async_mode: bool = False, max_request_workers: Optional[int] = None,
                  async_max_concurrent: int = DEFAULT_ASYNC_MAX_CONCURRENT,
                  headers: Optional[Dict[str, str]] = None):
        ...
        executor = Executor(
            api_url = self.base_url,
            strategy= Strategy.NAIVE_VALUE,
            operation=nodes.get(node.name),
            cache_dir=self.project_dir,
            model=self.model,
            num_test_cases=num_test_cases,
            configuration=configurations.get(node.name),
            mutation_ratio=mutation_ratio,
            header_mutation_ratio=header_mutation_ratio,
            context_pool=context_pool,
            max_request_workers=max_request_workers,
            use_async=async_mode,
            async_max_concurrent=async_max_concurrent,
            default_headers=headers,
        )
```

- [ ] **Step 4: Commit (if requested)**

```bash
git add api_testing/__init__.py api_testing/generators/executor.py
git commit -m "feat: support default headers from config"
```

---

### Task 6: Add root configuration template and update demo

**Files:**
- Create: `configurations.toml`
- Modify: `demo.py`

- [ ] **Step 1: Add configuration template**

```toml
[project]
spec_path = "datasets/GitLabIssues.json"
base_url = "http://localhost:30000/api/v4"
base_title = ""

[llm]
provider = "azure_openai"
model = "gpt-4.1-mini"
temperature = 0.7

[llm.azure_openai]
api_key = "${AZURE_OPENAI_API_KEY}"
endpoint = "${AZURE_OPENAI_ENDPOINT}"
api_version = "2024-12-01-preview"

[llm.openai]
api_key = "${OPENAI_API_KEY}"
base_url = "https://api.openai.com/v1"

[llm.gemini]
api_key = "${GOOGLE_API_KEY}"
project = ""
location = ""

[llm.ollama]
base_url = "http://localhost:11434"

[embedding]
provider = "huggingface"
model = "google/embeddinggemma-300m"
use_half = false

[embedding.ollama]
base_url = "http://localhost:11434"

[run]
num_generations = 1
num_test_cases = 20
mutation_ratio = 0.5
header_mutation_ratio = 0.5
async_mode = true
max_request_workers = 10
async_max_concurrent = 20

[headers]
PRIVATE-TOKEN = "${GITLAB_PRIVATE_TOKEN}"
```

- [ ] **Step 2: Update demo to load config**

```python
from api_testing import APITesting
from api_testing.config.config_loader import build_embedder, build_llm, load_config
from dotenv import load_dotenv
import time

load_dotenv()

print("============= API Testing =============")
start_time = time.perf_counter()

config = load_config("configurations.toml")
llm = build_llm(config)
embedder = build_embedder(config)

test = APITesting(
    base_url=config["project"]["base_url"],
    base_title=config["project"].get("base_title") or None,
    spec_path=config["project"]["spec_path"],
    model=llm,
    embedder=embedder,
)

run = config["run"]
test.run_tests(
    num_generations=run["num_generations"],
    num_test_cases=run["num_test_cases"],
    mutation_ratio=run["mutation_ratio"],
    header_mutation_ratio=run["header_mutation_ratio"],
    async_mode=run["async_mode"],
    max_request_workers=run["max_request_workers"],
    async_max_concurrent=run["async_max_concurrent"],
    headers=config.get("headers", {}),
)

elapsed = time.perf_counter() - start_time
print("\n========================================")
print(f"Total execution time: {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
print("========================================")
```

- [ ] **Step 3: Commit (if requested)**

```bash
git add configurations.toml demo.py
git commit -m "feat: add config-based demo"
```

---

### Task 7: Verify end-to-end flow

**Files:**
- None (verification only)

- [ ] **Step 1: Run demo**

Run: `python demo.py`

Expected: Uses `configurations.toml` values and starts running tests.

- [ ] **Step 2: Commit (if requested)**

```bash
git add -A
git commit -m "chore: verify config CLI flow"
```
