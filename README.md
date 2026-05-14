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

### 1. Setup

First, create a virtual environment and install the required dependencies:

```bash
# Create venv and install deps
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

Next, copy `.env.example` to `.env` and configure your API keys (e.g., Azure OpenAI, OpenAI, Gemini, etc.). These keys will be used by the configuration file.

```bash
cp .env.example .env
# Edit .env with your API credentials
```

---

### 2. Configuration (`configurations.toml`)

APIPilot is driven by a `configurations.toml` file. You can create this file manually or use the built-in wizard to generate it for you.

#### Initialization (Recommended)

Run the following command to start the interactive wizard, which will guide you through setting up your project, LLM, and run parameters, then save them to `configurations.toml`:

```bash
# Initialize configuration using the interactive wizard
python -m api_testing --init-config
```

#### Manual Configuration & Parameters

If you prefer to edit `configurations.toml` directly, ensure the following essential parameters are set:

| Section | Parameter | Description |
|---------|-----------|-------------|
| **`[project]`** | `spec_path` | Path to your OpenAPI 3.0 spec (`.json` or `.yaml`). |
| | `base_url` | The root URL of the API (e.g., `http://localhost:8080`). |
| **`[llm]`** | `provider` | Your LLM backend: `openai`, `azure_openai`, `gemini`, or `ollama`. |
| | `model` | The specific model name (e.g., `gpt-4o`, `gemini-1.5-pro`). |
| **`[run]`** | `num_generations` | Number of test rounds (higher = more coverage). |
| | `num_test_cases` | Test cases per endpoint per round. |
| | `async_mode` | Set to `true` for high-performance parallel testing. |

**Important**: For security, use `${ENV_VAR}` syntax for API keys in the `[llm.<provider>]` sections (e.g., `api_key = "${OPENAI_API_KEY}"`). These will be read from your `.env` file automatically.

---

### 3. Running the Tests

Once configured, you can run the tests immediately by skipping the interactive wizard. This is the fastest way to execute tests based on your `configurations.toml` settings.

```bash
# Run using the settings in configurations.toml
python -m api_testing --skip-wizard
```

Alternatively, you can use the provided demo script which also loads `configurations.toml` by default:

```bash
python demo.py
```

---

## Alternative Execution Methods

### 1. Interactive CLI Wizard

If you prefer a guided setup, the CLI includes a rich TUI wizard. It will prompt you for settings and allow you to preview the configuration before running.

```bash
# Start the full TUI wizard
python -m api_testing

# Essential settings only (skips advanced parameters)
python -m api_testing --quick

# Create/update config and exit without running tests
python -m api_testing --init-config
```

#### Useful CLI Flags

| Flag | Description |
|------|-------------|
| `--config PATH` | Use a custom config file (default: `configurations.toml`) |
| `--skip-wizard` | Load config and run immediately without prompts |
| `--explain` | Print descriptions of all configuration fields and exit |
| `-s, --spec PATH` | Override the `spec_path` from the config |
| `-g, --generations N`| Number of test rounds |
| `-c, --test-cases N` | Test cases per endpoint |
| `--async` | Force enable async HTTP mode |

---

### 2. Programmatic Usage (Python API)

For integrating APIPilot into your own scripts or CI/CD pipelines:

```python
from api_testing import APITesting
from api_testing.models.llms.openai_model import OpenAIModel
from api_testing.models.embedding_models.huggingface_embedding_model import HuggingfaceEmbeddingModel

# Initialize LLM and Embedder
llm = OpenAIModel(model="gpt-4o", api_key="<YOUR_KEY>")
embedder = HuggingfaceEmbeddingModel()

# Initialize the tester
tester = APITesting(
    base_url="https://api.example.com/v1",
    spec_path="datasets/my_api.json",
    model=llm,
    embedder=embedder,
)

# Run tests
tester.run_tests(
    num_generations=2,
    num_test_cases=30,
    mutation_ratio=0.2,
    async_mode=True
)
```

---

### 3. Advanced: Direct Executor Access

You can also use the `Executor` directly for low-level control over specific operation testing:

```python
from api_testing.generators.executor import Executor, Strategy

executor = Executor(
    api_url="https://api.example.com",
    strategy=Strategy.NAIVE_VALUE,
    operation=my_operation_instance,
    cache_dir=".cache/example",
    num_test_cases=10,
)

results = executor.exec()
```

