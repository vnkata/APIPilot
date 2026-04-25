# AGENTS.md

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure API keys (Azure OpenAI, OpenAI, etc.).

## Key Commands

```bash
# Run the demo (edit demo.py first to set your API keys)
python demo.py

# Run pytest tests
pytest tests/

# Generate 500-error report from HAR history
python endpoint_500_report.py --dir ".cache/GitLab Issues API 2"
python endpoint_500_report.py --dir ".cache/GitLab Issues API 2/history" --spec "datasets/GitLabIssues.json"
```

## Project Structure

- `api_testing/` - Main framework code
  - `generators/executor.py` - `Executor` class runs test cases
  - `dataset/specification_parser.py` - `SpecificationParser` parses OpenAPI specs
  - `configuration/configuration_parser.py` - `ConfigurationParser` builds configs
  - `inputs/` - Value generators (random, fuzz, LLM-based)
  - `models/llms/` - LLM integrations (OpenAI, Azure, Gemini, Ollama)
  - `models/embedding_models/` - Embedding model integrations
- `datasets/` - OpenAPI specification files (`.json`) for test targets
- `baselines/` - Baseline comparison frameworks (RESTifAI, AutoRestTest)
- `services/` - Locally deployable API services for testing

## Architecture Notes

- `APITesting` class (`api_testing/__init__.py`) is the main entry point
- Uses OpenAPI specs to generate test cases and discover operation dependencies
- `Executor` with `Strategy.NAIVE_VALUE` generates and executes HTTP requests
- Results cached in `.cache/<api_title>/` directory (gitignored)
- `endpoint_500_report.py` is a standalone CLI tool, not part of `api_testing` package

## Important Conventions

- HAR history files are stored in `.cache/<project>/history/*.har`
- Cached specification format uses `specification.json` with `operations` dict
- The framework uses `prance` for parsing OpenAPI specifications
- LLM calls are tracked via `utils/llm_tracker.py`
