import types

import api_testing as api_testing_module


def _base_config(debug_mode: bool):
    return {
        "project": {
            "spec_path": "datasets/Test.json",
            "base_url": "http://localhost:9999",
            "base_title": "Test API",
        },
        "run": {
            "num_generations": 1,
            "num_test_cases": 1,
            "mutation_ratio": 0.0,
            "header_mutation_ratio": 0.0,
            "async_mode": False,
            "max_request_workers": 1,
            "async_max_concurrent": 1,
            "debug": debug_mode,
        },
        "headers": {},
    }


def _make_args():
    return types.SimpleNamespace(
        config="configurations.toml",
        init_config=False,
        quick=False,
        skip_wizard=False,
        spec=None,
        async_mode=None,
        async_max_concurrent=None,
        generations=None,
        test_cases=None,
        mutation_ratio=None,
        header_mutation_ratio=None,
        max_workers=None,
    )


def _setup_common(monkeypatch, config, args):
    state = {}

    def _record(key):
        state[key] = state.get(key, 0) + 1

    class DummyAPITesting:
        def __init__(self, base_title=None, **kwargs):
            state["tester_created"] = True
            self.base_title = base_title or "Dummy API"
            self.logger = types.SimpleNamespace(debug=lambda *args, **kwargs: None)

        def run_tests(self, **kwargs):
            state["run_tests_called"] = True
            state["run_tests_kwargs"] = kwargs
            return 3, {"op": 1}

    class DummyTUIApp:
        def __init__(self):
            _record("tui_created")

        def start(self):
            _record("tui_started")

        def stop(self):
            _record("tui_stopped")

        def print_final_report(self, **kwargs):
            _record("tui_reported")

    def _set_console_level(level):
        state["console_level"] = level

    def _restore_console_logging():
        state["restored"] = True

    def _suppress_console_logging():
        state["suppressed"] = True

    class DummyEmbedder:
        def load_model(self):
            state["embedder_loaded"] = True

    monkeypatch.setattr(api_testing_module, "load_config", lambda path: config)
    monkeypatch.setattr(api_testing_module, "apply_cli_overrides", lambda cfg, args: cfg)
    monkeypatch.setattr(
        api_testing_module.PromptFactory,
        "from_config",
        staticmethod(lambda cfg: types.SimpleNamespace(common_llm=object())),
    )
    monkeypatch.setattr(api_testing_module, "build_embedder", lambda cfg: DummyEmbedder())
    monkeypatch.setattr(api_testing_module, "APITesting", DummyAPITesting)
    monkeypatch.setattr(api_testing_module, "TUIApp", DummyTUIApp)
    monkeypatch.setattr(api_testing_module, "set_console_level", _set_console_level)
    monkeypatch.setattr(api_testing_module, "restore_console_logging", _restore_console_logging)
    monkeypatch.setattr(api_testing_module, "suppress_console_logging", _suppress_console_logging)
    monkeypatch.setattr(api_testing_module, "parse_args", lambda: args)

    return state


def test_main_debug_mode_skips_tui(monkeypatch):
    config = _base_config(True)
    args = _make_args()
    state = _setup_common(monkeypatch, config, args)

    api_testing_module.main()

    assert state.get("tui_created", 0) == 0
    assert state.get("tui_started", 0) == 0
    assert state.get("tui_stopped", 0) == 0
    assert state.get("tui_reported", 0) == 0
    assert state.get("restored") is None
    assert state.get("suppressed") is None
    assert state.get("console_level") == api_testing_module.logging.DEBUG
    assert state.get("run_tests_called") is True


def test_main_non_debug_runs_tui(monkeypatch):
    config = _base_config(False)
    args = _make_args()
    state = _setup_common(monkeypatch, config, args)

    api_testing_module.main()

    assert state.get("tui_created", 0) == 1
    assert state.get("tui_started", 0) == 1
    assert state.get("tui_stopped", 0) == 1
    assert state.get("tui_reported", 0) == 1
    assert state.get("restored") is True
    assert state.get("suppressed") is True
    assert state.get("console_level") == api_testing_module.logging.INFO
    assert state.get("run_tests_called") is True


def test_main_passes_constraint_pipeline_config_to_run_tests(monkeypatch):
    config = _base_config(True)
    config["constraint_pipeline"] = {"enabled": True, "run_after_tests": True}
    config["counter_examples"] = {
        "counter_examples_per_pair": 2,
        "request_budget": 4,
    }
    args = _make_args()
    state = _setup_common(monkeypatch, config, args)

    api_testing_module.main()

    assert state["run_tests_kwargs"]["constraint_pipeline"] == config[
        "constraint_pipeline"
    ]
    assert state["run_tests_kwargs"]["counter_examples"] == config["counter_examples"]
