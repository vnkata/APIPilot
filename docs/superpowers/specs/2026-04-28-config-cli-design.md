# Config-Driven CLI for APITesting - Design

## Goal
Add a config-driven CLI workflow that can create and load `configurations.toml` via a simple interactive wizard, then run APITesting with those settings.

## Non-Goals
- No rich TUI (text prompts only for now).
- No changes to the core testing logic beyond reading config values and passing them through.
- No new dependency on full CLI frameworks.

## Architecture
Introduce a small config subsystem with two responsibilities:
1) Load and validate a TOML config into a typed dict.
2) Provide a simple wizard that writes a new TOML file.

The CLI entry in `api_testing/__init__.py` orchestrates these: it runs the wizard when requested, otherwise loads config, applies CLI overrides, builds LLM/embedder instances, and runs tests.

## Config Schema (TOML)
Root file: `configurations.toml`

Sections:

```toml
[project]
spec_path = "datasets/GitLabIssues.json"
base_url = "http://localhost:30000/api/v4"
base_title = ""  # optional

[llm]
provider = "azure_openai" # azure_openai | openai | gemini | ollama
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
project = ""    # optional
location = ""   # optional

[llm.ollama]
base_url = "http://localhost:11434"

[embedding]
provider = "huggingface" # huggingface | ollama
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

Notes:
- Env var interpolation supports `${VAR_NAME}` syntax.
- Missing provider-specific sections are allowed when unused.

## CLI Flow
Default config path is repo root `configurations.toml`.

Behavior:
- `apitesting` (no flags): run wizard, write config, then run tests using it.
- `apitesting --init-config`: run wizard and exit.
- `apitesting --skip-wizard`: load config and run tests.
- `--config PATH`: override config file path.
- Existing overrides (`--spec`, `--time`, `--async`, etc.) still apply to the loaded config.

## Wizard Flow (Simple Text Prompts)
Prompts (in order):
1) `spec_path`, `base_url`
2) LLM provider, model, temperature, provider-specific keys
3) Embedding provider, model, use_half, provider-specific keys
4) Run parameters (generations, test cases, mutation, async, concurrency)
5) Optional headers (loop until blank key)
6) Confirm and write

## Data Flow
1) Read TOML -> resolve env vars -> validate -> merge CLI overrides.
2) Build `llm` and `embedder` objects.
3) Initialize `APITesting` with `base_url`, `spec_path`, `model`, `embedder`.
4) Call `run_tests` with run settings.

## Error Handling
- Missing config file: clear error with path and example to run `--init-config`.
- Unknown provider: list valid providers.
- Missing required keys: list required keys for that provider.
- Missing `spec_path`: error before any execution.

## Files and Responsibilities
- `api_testing/config/config_loader.py`: parse TOML, resolve env vars, validate, return config dict.
- `api_testing/config/config_wizard.py`: prompt for values, build config dict, write TOML.
- `api_testing/__init__.py`: CLI args + orchestration for wizard/config/run.
- `demo.py`: simplified to load config and run (example).
- `configurations.toml`: default config template (repo root).

## Testing
Manual run:
- `python demo.py`
- `python -c "from api_testing import parse_args"` (CLI path)

No automated tests added for now; we can add a small parser test later.
