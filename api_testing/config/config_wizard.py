from __future__ import annotations

import os
from copy import deepcopy
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.theme import Theme

from .config_loader import DEFAULT_CONFIG, EMBEDDING_PROVIDERS, LLM_PROVIDERS
from api_testing.dataset.specification_parser import SpecificationParser

console = Console(
    force_terminal=True,
    theme=Theme(
        {
            "repr.number": "cyan",
            "repr.string": "green",
            "panel.title": "bold yellow",
            "table.header": "bold cyan",
        }
    )
)

FIELD_DESCRIPTIONS: Dict[str, tuple[str, str]] = {
    "project.spec_path": (
        "Spec path",
        "Path to your OpenAPI specification file (.json or .yaml). Must be OpenAPI 3.0. Relative to project root.",
    ),
    "project.base_url": (
        "Base URL",
        "Base URL of the API under test (e.g. http://localhost:30000/api/v4). If blank, extracted from spec servers field.",
    ),
    "project.base_title": (
        "Base title (optional)",
        "Display name for this project, used in cache folder names and logs. Leave blank to auto-detect from spec.",
    ),
    "llm.provider": (
        "LLM provider",
        "Which LLM backend to use: azure_openai | openai | gemini | ollama",
    ),
    "llm.model": (
        "LLM model / deployment",
        "Model name or Azure deployment ID. Must be a valid model for the chosen provider.",
    ),
    "llm.temperature": (
        "LLM temperature",
        "Controls how random or deterministic the model's responses are. 0.0 = always pick most likely token (safe). 1.0 = very random (creative but less predictable). Default: 0.7",
    ),
    "llm.azure_openai.api_key": (
        "Azure API key",
        "Your Azure OpenAI API key. Or use ${AZURE_OPENAI_API_KEY} env var.",
    ),
    "llm.azure_openai.endpoint": (
        "Azure endpoint",
        "Your Azure OpenAI endpoint URL (e.g. https://my-resource.openai.azure.com).",
    ),
    "llm.azure_openai.api_version": (
        "Azure API version",
        "Azure OpenAI API version. Default: 2024-12-01-preview",
    ),
    "llm.openai.api_key": (
        "OpenAI API key",
        "Your OpenAI API key. Or use ${OPENAI_API_KEY} env var.",
    ),
    "llm.openai.base_url": (
        "OpenAI base URL",
        "API base URL. Change this for OpenRouter, local proxies, etc. Default: https://api.openai.com/v1",
    ),
    "llm.gemini.api_key": (
        "Gemini API key",
        "Your Google Gemini API key. Or use ${GOOGLE_API_KEY} env var.",
    ),
    "llm.gemini.project": (
        "Vertex project (optional)",
        "Google Cloud project for Vertex AI (enterprise). Leave blank to use api_key instead.",
    ),
    "llm.gemini.location": (
        "Vertex location",
        "Google Cloud region for Vertex AI. Required if Vertex project is set.",
    ),
    "llm.ollama.base_url": (
        "Ollama base URL",
        "Base URL of your Ollama server. Default: http://localhost:11434",
    ),
    "embedding.provider": (
        "Embedding provider",
        "Which embedding backend to use: huggingface | ollama",
    ),
    "embedding.model": (
        "Embedding model",
        "Model name for embedding generation. For HuggingFace: a sentence-transformers model ID.",
    ),
    "embedding.use_half": (
        "Use half precision",
        "Use float16 (half-precision) to reduce GPU memory usage. Slightly less accurate but much faster on limited hardware. y/n",
    ),
    "embedding.ollama.base_url": (
        "Ollama embedding URL",
        "Base URL of your Ollama server for embeddings. Default: http://localhost:11434",
    ),
    "run.num_generations": (
        "Num generations",
        "Number of full test rounds to run. Each round rebuilds the operation dependency graph from scratch. More rounds = more thorough but slower.",
    ),
    "run.num_test_cases": (
        "Num test cases",
        "Number of test cases generated per endpoint per round. Higher = more coverage but slower.",
    ),
    "run.mutation_ratio": (
        "Mutation ratio",
        "Probability of intentionally breaking request parameters (e.g. sending invalid values) to test if the API returns proper 4xx errors. 0.0 = off, 0.5 = half mutated, 1.0 = all mutated.",
    ),
    "run.header_mutation_ratio": (
        "Header mutation ratio",
        "Probability of fuzzing HTTP headers during testing. 0.0 = off, 0.5 = half fuzzed, 1.0 = all fuzzed.",
    ),
    "run.async_mode": (
        "Async mode",
        "Use async HTTP requests for much higher throughput when testing many endpoints. Recommended for large APIs. y/n",
    ),
    "run.debug": (
        "Debug mode",
        "When true, skip the TUI and print logs to the terminal.",
    ),
    "run.constraint_mining": (
        "Constraint mining",
        "Generate static, dynamic, and combined constraint artifacts during the run. Disable for plain APIPilot output.",
    ),
    "run.max_request_workers": (
        "Max request workers",
        "Maximum number of parallel threads used during test execution. Controls how many endpoint trees run at the same time.",
    ),
    "run.async_max_concurrent": (
        "Async max concurrent",
        "Maximum number of simultaneous async HTTP requests allowed at once per worker thread.",
    ),
    "run.request_timeout_seconds": (
        "Request timeout seconds",
        "Maximum time to wait for a live API response before recording a timeout.",
    ),
}


def _get(key: str, config: Dict[str, Any]) -> Any:
    parts = key.split(".")
    val = config
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p, "")
        else:
            return ""
    return val


def _build_summary_table(config: Dict[str, Any]) -> Table:
    table = Table(
        show_header=True,
        header_style="bold cyan",
        title="[bold yellow]CONFIGURATION PREVIEW[/bold yellow]",
        title_style="bold yellow",
    )
    table.add_column("Field", style="bold")
    table.add_column("Value", style="cyan")

    sections = [
        ("PROJECT", ["project.spec_path", "project.base_url", "project.base_title"]),
        ("LLM", ["llm.provider", "llm.model", "llm.temperature"]),
        ("EMBEDDING", ["embedding.provider", "embedding.model", "embedding.use_half"]),
        (
            "RUN",
            [
                "run.num_generations",
                "run.num_test_cases",
                "run.mutation_ratio",
                "run.header_mutation_ratio",
                "run.async_mode",
                "run.debug",
                "run.constraint_mining",
                "run.max_request_workers",
                "run.async_max_concurrent",
                "run.request_timeout_seconds",
            ],
        ),
    ]

    for section_name, keys in sections:
        table.add_row(f"[bold yellow]{section_name}[/bold yellow]", "")
        for key in keys:
            label, _ = FIELD_DESCRIPTIONS.get(key, (key, ""))
            value = str(_get(key, config))
            table.add_row(f"  {label}", value)

    headers = config.get("headers", {})
    if headers:
        table.add_row("[bold yellow]HEADERS[/bold yellow]", "")
        for k, v in headers.items():
            table.add_row(f"  {k}", v)

    return table


def _apply_base_url_from_spec(config: Dict[str, Any]) -> Dict[str, Any]:
    project = config.get("project", {})
    base_url = project.get("base_url", "")
    spec_path = project.get("spec_path", "")

    if base_url:
        return config
    if not spec_path or not os.path.exists(spec_path):
        return config

    parser = SpecificationParser(spec_path=spec_path)
    spec_url = parser.get_api_url()
    if spec_url:
        project["base_url"] = spec_url

    return config


def run_wizard(path: str, quick_mode: bool = False) -> Dict[str, Any]:
    config = deepcopy(DEFAULT_CONFIG)

    with console.screen():
        # ── PROJECT ──────────────────────────────────────────────
        console.print(Panel.fit("[bold]PROJECT SETTINGS[/bold]"))

        _, spec_help = FIELD_DESCRIPTIONS["project.spec_path"]
        spec_path = _prompt_field(
            "Spec path",
            spec_help,
            default=config["project"]["spec_path"] if config["project"]["spec_path"] else "",
            console=console,
        )
        config["project"]["spec_path"] = spec_path

        _, url_help = FIELD_DESCRIPTIONS["project.base_url"]
        base_url = _prompt_field(
            "Base URL",
            url_help,
            default=config["project"]["base_url"] if config["project"]["base_url"] else "",
            console=console,
        )
        config["project"]["base_url"] = base_url

        _, title_help = FIELD_DESCRIPTIONS["project.base_title"]
        base_title = _prompt_field(
            "Base title (optional)",
            title_help,
            default=config["project"]["base_title"] if config["project"]["base_title"] else "",
            console=console,
        )
        config["project"]["base_title"] = base_title
        console.print()

        # ── LLM ───────────────────────────────────────────────────
        console.print(Panel.fit("[bold]LLM SETTINGS[/bold]"))

        _, prov_help = FIELD_DESCRIPTIONS["llm.provider"]
        provider = _prompt_field(
            "LLM provider",
            prov_help,
            choices=sorted(LLM_PROVIDERS),
            default=config["llm"]["provider"] if config["llm"]["provider"] else "",
            console=console,
        )
        config["llm"]["provider"] = provider

        _, model_help = FIELD_DESCRIPTIONS["llm.model"]
        model = _prompt_field(
            "LLM model / deployment",
            model_help,
            default=config["llm"]["model"],
            console=console,
        )
        config["llm"]["model"] = model

        _, temp_help = FIELD_DESCRIPTIONS["llm.temperature"]
        temperature = _prompt_field(
            "LLM temperature",
            temp_help,
            default=str(config["llm"]["temperature"]),
            console=console,
        )
        config["llm"]["temperature"] = float(temperature)

        if provider == "azure_openai":
            azure = config["llm"]["azure_openai"]
            _, ak_help = FIELD_DESCRIPTIONS["llm.azure_openai.api_key"]
            azure["api_key"] = _prompt_field(
                "Azure API key",
                ak_help,
                default=azure["api_key"],
                console=console,
            )
            _, ep_help = FIELD_DESCRIPTIONS["llm.azure_openai.endpoint"]
            azure["endpoint"] = _prompt_field(
                "Azure endpoint",
                ep_help,
                default=azure["endpoint"],
                console=console,
            )
            _, ver_help = FIELD_DESCRIPTIONS["llm.azure_openai.api_version"]
            azure["api_version"] = _prompt_field(
                "Azure API version",
                ver_help,
                default=azure["api_version"],
                console=console,
            )
        elif provider == "openai":
            openai_cfg = config["llm"]["openai"]
            _, ak_help = FIELD_DESCRIPTIONS["llm.openai.api_key"]
            openai_cfg["api_key"] = _prompt_field(
                "OpenAI API key",
                ak_help,
                default=openai_cfg["api_key"],
                console=console,
            )
            _, bu_help = FIELD_DESCRIPTIONS["llm.openai.base_url"]
            openai_cfg["base_url"] = _prompt_field(
                "OpenAI base URL",
                bu_help,
                default=openai_cfg["base_url"],
                console=console,
            )
        elif provider == "gemini":
            gemini = config["llm"]["gemini"]
            _, ak_help = FIELD_DESCRIPTIONS["llm.gemini.api_key"]
            gemini["api_key"] = _prompt_field(
                "Gemini API key",
                ak_help,
                default=gemini["api_key"],
                console=console,
            )
            _, proj_help = FIELD_DESCRIPTIONS["llm.gemini.project"]
            gemini["project"] = _prompt_field(
                "Vertex project (optional)",
                proj_help,
                default=gemini["project"],
                console=console,
            )
            _, loc_help = FIELD_DESCRIPTIONS["llm.gemini.location"]
            gemini["location"] = _prompt_field(
                "Vertex location",
                loc_help,
                default=gemini["location"],
                console=console,
            )
        elif provider == "ollama":
            ollama = config["llm"]["ollama"]
            _, bu_help = FIELD_DESCRIPTIONS["llm.ollama.base_url"]
            ollama["base_url"] = _prompt_field(
                "Ollama base URL",
                bu_help,
                default=ollama["base_url"],
                console=console,
            )
        console.print()

        # ── EMBEDDING ───────────────────────────────────────────
        console.print(Panel.fit("[bold]EMBEDDING SETTINGS[/bold]"))

        _, embProv_help = FIELD_DESCRIPTIONS["embedding.provider"]
        emb_provider = _prompt_field(
            "Embedding provider",
            embProv_help,
            choices=sorted(EMBEDDING_PROVIDERS),
            default=config["embedding"]["provider"],
            console=console,
        )
        config["embedding"]["provider"] = emb_provider

        _, embMod_help = FIELD_DESCRIPTIONS["embedding.model"]
        embedding_model = _prompt_field(
            "Embedding model",
            embMod_help,
            default=config["embedding"]["model"],
            console=console,
        )
        config["embedding"]["model"] = embedding_model

        _, half_help = FIELD_DESCRIPTIONS["embedding.use_half"]
        use_half = Confirm.ask(
            f"[cyan]Use half precision[/cyan]",
            default=bool(config["embedding"]["use_half"]),
            console=console,
        )
        config["embedding"]["use_half"] = use_half

        if emb_provider == "ollama":
            emb_ollama = config["embedding"]["ollama"]
            _, embUrl_help = FIELD_DESCRIPTIONS["embedding.ollama.base_url"]
            emb_ollama["base_url"] = _prompt_field(
                "Ollama embedding URL",
                embUrl_help,
                default=emb_ollama["base_url"],
                console=console,
            )
        console.print()

        # ── RUN ──────────────────────────────────────────────────
        if not quick_mode:
            console.print(Panel.fit("[bold]RUN SETTINGS[/bold]"))

            _, ng_help = FIELD_DESCRIPTIONS["run.num_generations"]
            num_gens = _prompt_field(
                "Num generations",
                ng_help,
                default=str(config["run"]["num_generations"]),
                console=console,
            )
            config["run"]["num_generations"] = int(num_gens)

            _, ntc_help = FIELD_DESCRIPTIONS["run.num_test_cases"]
            num_cases = _prompt_field(
                "Num test cases",
                ntc_help,
                default=str(config["run"]["num_test_cases"]),
                console=console,
            )
            config["run"]["num_test_cases"] = int(num_cases)

            _, mut_help = FIELD_DESCRIPTIONS["run.mutation_ratio"]
            mut_ratio = _prompt_field(
                "Mutation ratio",
                mut_help,
                default=str(config["run"]["mutation_ratio"]),
                console=console,
            )
            config["run"]["mutation_ratio"] = float(mut_ratio)

            _, hdrMut_help = FIELD_DESCRIPTIONS["run.header_mutation_ratio"]
            hdr_mut_ratio = _prompt_field(
                "Header mutation ratio",
                hdrMut_help,
                default=str(config["run"]["header_mutation_ratio"]),
                console=console,
            )
            config["run"]["header_mutation_ratio"] = float(hdr_mut_ratio)

            _, async_help = FIELD_DESCRIPTIONS["run.async_mode"]
            async_mode = Confirm.ask(
                f"[cyan]Async mode[/cyan]",
                default=bool(config["run"]["async_mode"]),
                console=console,
            )
            config["run"]["async_mode"] = async_mode

            _, debug_help = FIELD_DESCRIPTIONS["run.debug"]
            config["run"]["debug"] = _confirm_field(
                "Debug mode (skip TUI, print logs)",
                debug_help,
                default=bool(config["run"]["debug"]),
                console=console,
            )

            _, mining_help = FIELD_DESCRIPTIONS["run.constraint_mining"]
            config["run"]["constraint_mining"] = _confirm_field(
                "Constraint mining",
                mining_help,
                default=bool(config["run"]["constraint_mining"]),
                console=console,
            )

            _, mw_help = FIELD_DESCRIPTIONS["run.max_request_workers"]
            max_workers = _prompt_field(
                "Max request workers",
                mw_help,
                default=str(config["run"]["max_request_workers"]),
                console=console,
            )
            config["run"]["max_request_workers"] = int(max_workers)

            _, amc_help = FIELD_DESCRIPTIONS["run.async_max_concurrent"]
            async_conc = _prompt_field(
                "Async max concurrent",
                amc_help,
                default=str(config["run"]["async_max_concurrent"]),
                console=console,
            )
            config["run"]["async_max_concurrent"] = int(async_conc)

            _, timeout_help = FIELD_DESCRIPTIONS["run.request_timeout_seconds"]
            timeout_seconds = _prompt_field(
                "Request timeout seconds",
                timeout_help,
                default=str(config["run"]["request_timeout_seconds"]),
                console=console,
            )
            config["run"]["request_timeout_seconds"] = float(timeout_seconds)
            console.print()

        # ── HEADERS ─────────────────────────────────────────────
        console.print(Panel.fit("[bold]CUSTOM HEADERS[/bold]"))
        console.print("[dim]Press Enter on an empty name to finish.[/dim]")
        headers: Dict[str, str] = {}
        while True:
            key = Prompt.ask("[cyan]Header name[/cyan]", default="", console=console).strip()
            if not key:
                break
            value = Prompt.ask(f"[cyan]Value for {key}[/cyan]", default="", console=console)
            headers[key] = value
        config["headers"] = headers
        console.print()

        # ── SUMMARY & CONFIRM ───────────────────────────────────
        config = _apply_base_url_from_spec(config)
        console.print(Panel.fit("[bold]CONFIGURATION PREVIEW[/bold]", border_style="yellow"))
        table = _build_summary_table(config)
        console.print(table)
        console.print()

        save = Confirm.ask("[yellow]Save this configuration?[/yellow]", default=True, console=console)
        if not save:
            raise SystemExit("Configuration wizard cancelled")

    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    use_comments = Confirm.ask(
        "[cyan]Include field descriptions as inline comments in the generated TOML?[/cyan]",
        default=True,
        console=console,
    )

    rendered = _render_toml_with_comments(config) if use_comments else _render_toml(config)

    console.print(Panel.fit(rendered, title="configurations.toml", border_style="cyan"))

    if not Confirm.ask("[cyan]Write this configuration to file?[/cyan]", default=True, console=console):
        console.print("[yellow]Aborted — no file written[/yellow]")
        return None

    path = os.path.abspath(path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(rendered)

    console.print(f"[green]Wrote configuration to {path}[/green]")
    return config


def _prompt_field(label: str, help_text: str, **kwargs) -> Any:
    console.print(f"[dim]{help_text}[/dim]")
    return Prompt.ask(f"[cyan]{label}[/cyan]", **kwargs)


def _confirm_field(label: str, help_text: str, *, default: bool, console: Console) -> bool:
    console.print(f"[dim]{help_text}[/dim]")
    return Confirm.ask(
        f"[cyan]{label}[/cyan]",
        default=default,
        console=console,
    )


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _comment(key: str) -> str:
    _, help_text = FIELD_DESCRIPTIONS[key]
    return f"  # {help_text}"


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
    lines.append(f"debug = {_toml_value(run.get('debug', False))}")
    lines.append(f"constraint_mining = {_toml_value(run.get('constraint_mining', True))}")
    lines.append(f"max_request_workers = {_toml_value(run.get('max_request_workers', 10))}")
    lines.append(f"async_max_concurrent = {_toml_value(run.get('async_max_concurrent', 20))}")
    lines.append(f"request_timeout_seconds = {_toml_value(run.get('request_timeout_seconds', 300.0))}")
    lines.append("")

    return "\n".join(lines)


def _render_toml_with_comments(config: Dict[str, Any]) -> str:
    lines: list[str] = []

    project = config["project"]
    lines.append("[project]")
    lines.append(f"spec_path = {_toml_value(project.get('spec_path', ''))}{_comment('project.spec_path')}")
    lines.append(f"base_url = {_toml_value(project.get('base_url', ''))}{_comment('project.base_url')}")
    lines.append(f"base_title = {_toml_value(project.get('base_title', ''))}{_comment('project.base_title')}")
    lines.append("")

    llm = config["llm"]
    lines.append("[llm]")
    lines.append(f"provider = {_toml_value(llm.get('provider', ''))}{_comment('llm.provider')}")
    lines.append(f"model = {_toml_value(llm.get('model', ''))}{_comment('llm.model')}")
    lines.append(f"temperature = {_toml_value(llm.get('temperature', 0.0))}{_comment('llm.temperature')}")
    lines.append("")

    azure = llm.get("azure_openai", {})
    lines.append("[llm.azure_openai]")
    lines.append(f"api_key = {_toml_value(azure.get('api_key', ''))}{_comment('llm.azure_openai.api_key')}")
    lines.append(f"endpoint = {_toml_value(azure.get('endpoint', ''))}{_comment('llm.azure_openai.endpoint')}")
    lines.append(f"api_version = {_toml_value(azure.get('api_version', ''))}{_comment('llm.azure_openai.api_version')}")
    lines.append("")

    openai_cfg = llm.get("openai", {})
    lines.append("[llm.openai]")
    lines.append(f"api_key = {_toml_value(openai_cfg.get('api_key', ''))}{_comment('llm.openai.api_key')}")
    lines.append(f"base_url = {_toml_value(openai_cfg.get('base_url', ''))}{_comment('llm.openai.base_url')}")
    lines.append("")

    gemini = llm.get("gemini", {})
    lines.append("[llm.gemini]")
    lines.append(f"api_key = {_toml_value(gemini.get('api_key', ''))}{_comment('llm.gemini.api_key')}")
    lines.append(f"project = {_toml_value(gemini.get('project', ''))}{_comment('llm.gemini.project')}")
    lines.append(f"location = {_toml_value(gemini.get('location', ''))}{_comment('llm.gemini.location')}")
    lines.append("")

    ollama = llm.get("ollama", {})
    lines.append("[llm.ollama]")
    lines.append(f"base_url = {_toml_value(ollama.get('base_url', ''))}{_comment('llm.ollama.base_url')}")
    lines.append("")

    embedding = config["embedding"]
    lines.append("[embedding]")
    lines.append(f"provider = {_toml_value(embedding.get('provider', ''))}{_comment('embedding.provider')}")
    lines.append(f"model = {_toml_value(embedding.get('model', ''))}{_comment('embedding.model')}")
    lines.append(f"use_half = {_toml_value(embedding.get('use_half', False))}{_comment('embedding.use_half')}")
    lines.append("")

    emb_ollama = embedding.get("ollama", {})
    lines.append("[embedding.ollama]")
    lines.append(f"base_url = {_toml_value(emb_ollama.get('base_url', ''))}{_comment('embedding.ollama.base_url')}")
    lines.append("")

    run = config["run"]
    lines.append("[run]")
    lines.append(f"num_generations = {_toml_value(run.get('num_generations', 1))}{_comment('run.num_generations')}")
    lines.append(f"num_test_cases = {_toml_value(run.get('num_test_cases', 20))}{_comment('run.num_test_cases')}")
    lines.append(f"mutation_ratio = {_toml_value(run.get('mutation_ratio', 0.0))}{_comment('run.mutation_ratio')}")
    lines.append(f"header_mutation_ratio = {_toml_value(run.get('header_mutation_ratio', 0.5))}{_comment('run.header_mutation_ratio')}")
    lines.append(f"async_mode = {_toml_value(run.get('async_mode', False))}{_comment('run.async_mode')}")
    lines.append(f"debug = {_toml_value(run.get('debug', False))}{_comment('run.debug')}")
    lines.append(f"constraint_mining = {_toml_value(run.get('constraint_mining', True))}{_comment('run.constraint_mining')}")
    lines.append(f"max_request_workers = {_toml_value(run.get('max_request_workers', 10))}{_comment('run.max_request_workers')}")
    lines.append(f"async_max_concurrent = {_toml_value(run.get('async_max_concurrent', 20))}{_comment('run.async_max_concurrent')}")
    lines.append(f"request_timeout_seconds = {_toml_value(run.get('request_timeout_seconds', 300.0))}{_comment('run.request_timeout_seconds')}")
    lines.append("")

    return "\n".join(lines)


def explain_fields():
    console.print("\n[bold yellow]=== APITesting Configuration Fields ===[/bold yellow]\n")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field", style="bold")
    table.add_column("Description", style="dim")

    for key, (label, help_text) in FIELD_DESCRIPTIONS.items():
        if key in ("headers.key", "headers.value", "confirm"):
            continue
        default = DEFAULT_CONFIG
        for part in key.split("."):
            if isinstance(default, dict):
                default = default.get(part, "")
            else:
                default = ""
        default_str = str(default) if default else ""
        suffix = f" [default: {default_str}]" if default_str else ""
        table.add_row(label, f"{help_text}{suffix}")

    console.print(table)
