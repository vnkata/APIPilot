# APIPilot: REST API Testing with Verified LLM-Inferred Dependencies and Response-Driven Refinement

APIPilot is a verification-guided framework for REST API testing that infers and validates operation dependencies using LLMs and execution feedback, enabling reliable workflow generation and iterative refinement.

## Architecture

![Reflexion RL diagram](./figures/architecture.png)

## Available Baseline Tools

- **RESTifAI** (`RESTifAI`): A LLM-based REST API testing framework designed to generate reusable and executable production-ready test suites. The approach validates OpenAPI specifications through structural conformance testing and verifying business logic scenarios through functional test case generation.
  _Reference_: https://doi.org/10.48550/arXiv.2512.08706
  _Repository_: https://github.com/casablancahotelsoftware/RESTifAI

- **AutoRestTest** (`AutoRestTest`): A mutation-based API testing methodology that leverages LLM-generated request values combined with reinforcement learning techniques to maximize the detection of unique HTTP 500 server errors and successful 2xx responses across distinct API operations.
  _Reference_: https://doi.org/10.48550/arXiv.2501.08600
  _Repository_: https://github.com/selab-gatech/AutoRestTest/

- **KAT** (`KAT`): A novel AI-driven approach that leverages the large language model GPT in conjunction with advanced prompting techniques to autonomously generate test cases to validate RESTful APIs.
  _Reference_: https://doi.org/10.48550/arXiv.2407.10227

## Evaluation Dataset: API Services

The experimental evaluation encompasses 11 diverse REST API services, selected to represent varying complexity levels and domain-specific characteristics:

#### Locally Deployed Services

- **genome-nexus**: A bioinformatics service providing genomic variant annotation capabilities
  _Source_: https://github.com/genome-nexus/genome-nexus
- **language-tool**: A natural language processing service offering grammar and linguistic analysis
  _Source_: https://github.com/languagetool-org/languagetool
- **rest-countries**: A geographical information service providing country-specific metadata
  _Source_: https://github.com/apilayer/restcountries
- **GitLab**: A web-based DevOps lifecycle tool providing Git repository management, issue tracking, and CI/CD pipeline features
  _Source_: https://gitlab.com/gitlab-org/gitlab
- **Jhipster Sample Application**: Jhipster Sample Application API
  _Source_: https://github.com/jhipster/jhipster-sample-app
- **Petstore**: This is a sample server Petstore server.
  _Source_: https://github.com/swagger-api/swagger-petstore
- **Spring PetClinic**: Spring PetClinic Sample Application.

  _Source_: https://github.com/spring-projects/spring-petclinic

#### Remotely Hosted Services

- **Bills API**: API to get and search for information regarding Bills, their stages, associated amendments and publications.
- **Canada Holidays API**: This API lists all 31 public holidays for all 13 provinces and territories in Canada, including federal holidays.
- **fdic**: Federal Deposit Insurance Corporation banking institution data service
  _Documentation_: https://api.fdic.gov/banks/docs/
- **ohsome**: OpenStreetMap geospatial data analysis and statistics service
  _Documentation_: https://docs.ohsome.org/ohsome-api/v1/

#### Results

The `results/` directory stores structured outputs and analysis artifacts produced during the API testing and fault discovery process. It serves as the primary location for reproducible results and post-execution analysis.

- `results/results.xlsx`: A central report spreadsheet summarizing statistics across multiple runs.
- `results/unique_500_entries.jsonl`: A JSON Lines file containing 185 entries of 500-error cases grouped by operations.

**Happy testing! 🚀**

---

## How to use the tool

### Setup

```bash
# create venv and install deps
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure your API keys (Azure OpenAI, OpenAI, Gemini, etc.):

```bash
cp .env.example .env
# then edit .env with your API credentials
```

---

### 1. CLI (Recommended)

The CLI uses a rich TUI wizard — prompts guide you through every setting, then preview the config before saving.

```bash
# Full TUI wizard — prompts for all settings then runs
python -m api_testing

# Quick wizard — essential settings only (skips run parameters)
python -m api_testing --quick

# Create config and exit (no tests)
python -m api_testing --init-config

# Print all field descriptions (reference), then exit
python -m api_testing --explain

# Skip wizard and run from existing config
python -m api_testing --skip-wizard

# Custom config path
python -m api_testing --config path/to/my_config.toml

# Override individual settings from config
python -m api_testing --skip-wizard --spec datasets/my_api.json --async
```

#### CLI Flags

| Flag | Description |
|------|-------------|
| `--config PATH` | Path to config file (default: `configurations.toml`) |
| `--init-config` | Run TUI wizard and write config, then exit |
| `--skip-wizard` | Skip wizard, load config and run immediately |
| `--quick` | Quick wizard (essential settings only) |
| `--explain` | Print all field descriptions and exit |
| `-s, --spec PATH` | Override spec path |
| `--async` | Enable async HTTP mode |
| `--async-max-concurrent N` | Max concurrent async requests |
| `-g, --generations N` | Number of test generations |
| `-c, --test-cases N` | Test cases per endpoint |
| `--mutation-ratio N` | Parameter mutation probability (0.0–1.0) |
| `--header-mutation-ratio N` | Header mutation probability (0.0–1.0) |
| `--max-workers N` | Max concurrent request workers |

---

### 2. Demo (config-driven)

The simplest way to run without the wizard is to edit `configurations.toml` with your settings, then:

```bash
python demo.py
```

`demo.py` loads settings from `configurations.toml` automatically. See the annotated template in `configurations.toml` for all available options.

---

### 3. Programmatic (Python API)

For fine-grained control, use the Python API directly:

```python
from api_testing import APITesting
from api_testing.models.llms.openai_model import OpenAIModel
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel

llm = OpenAIModel(model="gpt-4.1-mini", api_key="<YOUR_KEY>")
embedder = HuggingfaceEmbeddingModel()

tester = APITesting(
    base_url="https://api.example.com/v1",
    spec_path="datasets/my_api.json",
    model=llm,
    embedder=embedder,
)

tester.run_tests(
    num_generations=2,
    num_test_cases=30,
    mutation_ratio=0.2,
    async_mode=True,
    max_request_workers=10,
    async_max_concurrent=20,
    headers={"PRIVATE-TOKEN": "my-token"},
)
```

---

### 4. Advanced: use `Executor` directly

```python
from api_testing.generators.executor import Executor, Strategy

executor = Executor(
    api_url="https://api.example.com",
    strategy=Strategy.NAIVE_VALUE,
    operation=<OperationProperties instance>,
    cache_dir=".cache/example",
    num_test_cases=10,
)

entries = executor.exec()
```

---

### 5. Generate endpoint-level 500 report from HAR history

```bash
python endpoint_500_report.py \
  --dir ".cache/GitLab Issues API 2"

python endpoint_500_report.py \
  --dir ".cache/GitLab Issues API 2/history" \
  --spec "datasets/GitLabIssues.json"
```

Outputs:
- `endpoint_500_report.csv` — one row per endpoint with `has_500` flag
- `endpoint_500_summary.json` — total endpoints vs. endpoints that hit HTTP 500

---

### Configuration File (`configurations.toml`)

The config file is TOML with these sections:

| Section | Purpose |
|---------|---------|
| `[project]` | `spec_path`, `base_url`, `base_title` |
| `[llm]` | Provider, model, temperature |
| `[llm.*]` | Provider-specific credentials (fill the one you use) |
| `[embedding]` | Embedding provider and model |
| `[run]` | Test generation and execution parameters |
| `[headers]` | Static headers for every request |

Sensitive values support `${ENV_VAR}` interpolation — never hardcode secrets in the config file. See the commented template in `configurations.toml` for full documentation of every field.
