# Debug Mode TUI Toggle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `run.debug` TOML setting that disables the TUI and enables console debug logging when true, while preserving current behavior when false.

**Architecture:** The configuration loader defines a new `run.debug` default, the wizard renders/prompts it into generated TOML, and the CLI runtime branches on it to either launch the TUI or run in plain console mode.

**Tech Stack:** Python, tomllib/tomli, Rich (wizard), existing logging utilities.

---

## File Structure

- Modify: `api_testing/config/config_loader.py` (add `run.debug` default)
- Modify: `tests/test_config_loader.py` (tests for debug default/override)
- Modify: `api_testing/config/config_wizard.py` (field description, prompt, summary table, TOML render)
- Modify: `configurations.toml` (sample config includes debug field)
- Modify: `api_testing/__init__.py` (CLI epilog + runtime branch for TUI)

---

### Task 1: Add tests + config default for run.debug

**Files:**
- Modify: `tests/test_config_loader.py`
- Modify: `api_testing/config/config_loader.py`

- [ ] **Step 1: Write failing tests for debug default/override**

Append to `tests/test_config_loader.py`:

```python
def test_debug_defaults_false(tmp_path):
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

    assert config["run"]["debug"] is False


def test_debug_can_be_true(tmp_path):
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
    debug = true
    """
    path = tmp_path / "configurations.toml"
    _write_config(path, content)

    config = load_config(str(path))

    assert config["run"]["debug"] is True
```

- [ ] **Step 2: Run tests to see expected failure**

Run: `pytest tests/test_config_loader.py -k debug -v`

Expected: FAIL with `KeyError: 'debug'` (default missing in config).

- [ ] **Step 3: Add debug default in config loader**

In `api_testing/config/config_loader.py`, update `DEFAULT_CONFIG["run"]` to include `debug`:

```python
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
```

- [ ] **Step 4: Re-run tests**

Run: `pytest tests/test_config_loader.py -k debug -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_config_loader.py api_testing/config/config_loader.py
git commit -m "test: cover run.debug default" 
```

---

### Task 2: Update wizard + TOML render + sample config

**Files:**
- Modify: `api_testing/config/config_wizard.py`
- Modify: `configurations.toml`

- [ ] **Step 1: Add field description and summary table entry**

In `api_testing/config/config_wizard.py`, add to `FIELD_DESCRIPTIONS`:

```python
    "run.debug": (
        "Debug mode",
        "When true, skip the TUI and print logs to the terminal.",
    ),
```

And include it in the RUN section of `_build_summary_table`:

```python
            [
                "run.num_generations",
                "run.num_test_cases",
                "run.mutation_ratio",
                "run.header_mutation_ratio",
                "run.async_mode",
                "run.debug",
                "run.max_request_workers",
                "run.async_max_concurrent",
            ],
```

- [ ] **Step 2: Prompt for debug mode in the wizard**

In the RUN section of `run_wizard`, after the async mode prompt, add:

```python
            _, debug_help = FIELD_DESCRIPTIONS["run.debug"]
            console.print(f"[dim]{debug_help}[/dim]")
            debug_mode = Confirm.ask(
                "[cyan]Debug mode (skip TUI, print logs)[/cyan]",
                default=bool(config["run"]["debug"]),
                console=console,
            )
            config["run"]["debug"] = debug_mode
```

- [ ] **Step 3: Render run.debug in TOML output**

In `_render_toml`:

```python
    run = config["run"]
    lines.append("[run]")
    lines.append(f"num_generations = {_toml_value(run.get('num_generations', 1))}")
    lines.append(f"num_test_cases = {_toml_value(run.get('num_test_cases', 20))}")
    lines.append(f"mutation_ratio = {_toml_value(run.get('mutation_ratio', 0.0))}")
    lines.append(f"header_mutation_ratio = {_toml_value(run.get('header_mutation_ratio', 0.5))}")
    lines.append(f"async_mode = {_toml_value(run.get('async_mode', False))}")
    lines.append(f"debug = {_toml_value(run.get('debug', False))}")
    lines.append(f"max_request_workers = {_toml_value(run.get('max_request_workers', 10))}")
    lines.append(f"async_max_concurrent = {_toml_value(run.get('async_max_concurrent', 20))}")
    lines.append("")
```

In `_render_toml_with_comments`:

```python
    run = config["run"]
    lines.append("[run]")
    lines.append(f"num_generations = {_toml_value(run.get('num_generations', 1))}{_comment('run.num_generations')}")
    lines.append(f"num_test_cases = {_toml_value(run.get('num_test_cases', 20))}{_comment('run.num_test_cases')}")
    lines.append(f"mutation_ratio = {_toml_value(run.get('mutation_ratio', 0.0))}{_comment('run.mutation_ratio')}")
    lines.append(f"header_mutation_ratio = {_toml_value(run.get('header_mutation_ratio', 0.5))}{_comment('run.header_mutation_ratio')}")
    lines.append(f"async_mode = {_toml_value(run.get('async_mode', False))}{_comment('run.async_mode')}")
    lines.append(f"debug = {_toml_value(run.get('debug', False))}{_comment('run.debug')}")
    lines.append(f"max_request_workers = {_toml_value(run.get('max_request_workers', 10))}{_comment('run.max_request_workers')}")
    lines.append(f"async_max_concurrent = {_toml_value(run.get('async_max_concurrent', 20))}{_comment('run.async_max_concurrent')}")
    lines.append("")
```

- [ ] **Step 4: Update sample TOML**

In `configurations.toml` under `[run]`, add:

```toml
debug = false  # When true, skip the TUI and print logs to the terminal.
```

Place it after `async_mode` to keep related flags together.

- [ ] **Step 5: Quick sanity check of wizard TOML render**

Run: `python -c "from api_testing.config.config_wizard import _render_toml, DEFAULT_CONFIG; print([line for line in _render_toml(DEFAULT_CONFIG).splitlines() if line.startswith('debug =')][0])"`

Expected output: `debug = false`

- [ ] **Step 6: Commit**

```bash
git add api_testing/config/config_wizard.py configurations.toml
git commit -m "feat: add run.debug to config wizard" 
```

---

### Task 3: Gate TUI runtime on run.debug + CLI help text

**Files:**
- Modify: `api_testing/__init__.py`

- [ ] **Step 1: Update CLI epilog to mention TOML debug mode**

In the `epilog` block in `api_testing/__init__.py`, add a line like:

```text
  configurations.toml          # Set run.debug=true to disable TUI and print logs
```

- [ ] **Step 2: Gate TUI startup and final report**

Update `main()` to branch on `run.debug`. Example structure:

```python
    run = config["run"]
    debug_mode = bool(run.get("debug", False))

    tester = APITesting(
        base_url=config["project"]["base_url"],
        base_title=config["project"].get("base_title") or None,
        spec_path=config["project"]["spec_path"],
        model=llm,
        embedder=embedder,
    )

    if debug_mode:
        set_console_level(logging.DEBUG)
    else:
        set_console_level(logging.INFO)

    tui_app = None
    if not debug_mode:
        tui_app = TUIApp()
        tui_app.start()

    start_time = time.perf_counter()
```

Then in the `finally` block, guard TUI calls:

```python
    finally:
        elapsed = time.perf_counter() - start_time
        if tui_app:
            restore_console_logging()
            tui_app.stop()
            tui_app.print_final_report(
                title=tester.base_title,
                duration_seconds=elapsed,
                total_requests=total_testcase,
                status_distribution={},
                total_operations=len(successFull),
                successful_operations=len(successFull),
                unique_5xx_errors=0,
            )
```

- [ ] **Step 3: Manual sanity check (optional but recommended)**

1) Set `run.debug = true` in `configurations.toml`.
2) Run: `python -c "from api_testing import main; main()"`
3) Expected: No TUI; logs print to terminal.

Then set `run.debug = false` and repeat to see the TUI.

- [ ] **Step 4: Commit**

```bash
git add api_testing/__init__.py
git commit -m "feat: skip TUI when run.debug is true"
```

---

## Self-Review Checklist

- Spec coverage: `run.debug` default, wizard prompt/render, runtime TUI gating, CLI help text, sample TOML.
- Placeholder scan: no TODO/TBD in plan steps.
- Type consistency: `run.debug` treated as bool everywhere.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-06-debug-tui-toggle.md`. Two execution options:

1. Subagent-Driven (recommended) — I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution — Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
