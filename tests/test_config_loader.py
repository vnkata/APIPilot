import textwrap
import pytest

from api_testing.config.config_loader import load_config
from api_testing.prompts.factory import PromptFactory
from api_testing.prompts.smart_value_generate import SmartValueGenerate
from api_testing.prompts.semantic_oracle_judge import SemanticOracleJudge


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


def test_openai_provider_does_not_require_azure_env(tmp_path):
    content = """
    [project]
    spec_path = "datasets/Test.json"
    base_url = "http://localhost:9999"

    [llm]
    provider = "openai"
    model = "gpt-4o-mini"
    temperature = 0.1

    [llm.openai]
    api_key = "literal-key"
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
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    config = load_config(str(path))

    assert config["llm"]["openai"]["api_key"] == "literal-key"


def test_missing_openai_key_with_unresolved_placeholder(tmp_path):
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
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    with pytest.raises(ValueError, match="llm.openai.api_key"):
        load_config(str(path))


def test_unresolved_header_placeholder_raises(tmp_path):
    content = """
    [project]
    spec_path = "datasets/Test.json"
    base_url = "http://localhost:9999"

    [llm]
    provider = "openai"
    model = "gpt-4o-mini"
    temperature = 0.1

    [llm.openai]
    api_key = "literal-key"
    base_url = "https://api.openai.com/v1"

    [embedding]
    provider = "huggingface"
    model = "google/embeddinggemma-300m"
    use_half = false

    [headers]
    Authorization = "Bearer ${OPENAI_API_KEY}"

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

    with pytest.raises(ValueError, match="headers.Authorization"):
        load_config(str(path))


def test_run_debug_defaults_false(tmp_path, monkeypatch):
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
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    config = load_config(str(path))

    assert config["run"]["debug"] is False


def test_run_debug_allows_override_true(tmp_path, monkeypatch):
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
    debug = true
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    config = load_config(str(path))

    assert config["run"]["debug"] is True


def test_prompt_llm_override_inherits_common_provider(tmp_path):
    content = """
    [project]
    spec_path = "datasets/Test.json"
    base_url = "http://localhost:9999"

    [llm]
    provider = "openai"
    model = "gpt-4o-mini"
    temperature = 0.0

    [llm.openai]
    api_key = "literal-key"
    base_url = "https://api.openai.com/v1"

    [llm.prompts.SmartValueGenerate]
    temperature = 0.7

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

    config = load_config(str(path))
    factory = PromptFactory.from_config(config)

    assert factory.common_llm.temperature == 0.0
    assert factory.get_llm(SmartValueGenerate).temperature == 0.7
    assert factory.get_llm(SemanticOracleJudge) is factory.common_llm


def test_prompt_llm_override_can_swap_provider(tmp_path):
    content = """
    [project]
    spec_path = "datasets/Test.json"
    base_url = "http://localhost:9999"

    [llm]
    provider = "openai"
    model = "gpt-4o-mini"
    temperature = 0.0

    [llm.openai]
    api_key = "literal-key"
    base_url = "https://api.openai.com/v1"

    [llm.prompts.SemanticOracleJudge]
    provider = "litellm"
    model = "claude-3-5-sonnet-latest"
    temperature = 0.2

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

    config = load_config(str(path))
    factory = PromptFactory.from_config(config)

    judge_llm = factory.get_llm(SemanticOracleJudge)
    assert judge_llm.model_name == "claude-3-5-sonnet-latest"
    assert judge_llm.temperature == 0.2
    assert factory.get_llm(SmartValueGenerate) is factory.common_llm
