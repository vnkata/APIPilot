# Debug Mode Toggle (TOML) Design

## Summary
Introduce a `run.debug` boolean in `configurations.toml` that disables the TUI and enables verbose console logging when true. Default remains `false`, preserving the existing TUI flow.

## Goals
- Provide a clear “debug mode” in TOML that skips the TUI entirely.
- Ensure debug mode prints logs to the terminal at DEBUG level.
- Keep existing behavior unchanged when `run.debug` is false.

## Non-Goals
- No README updates in this change set.
- No new CLI flags or environment-variable controls.

## Design

### Configuration schema
- Add `run.debug: bool` to the config schema in `api_testing/config/config_loader.py`.
- Default value: `false`.
- Include in TOML rendering (with and without comments) in `api_testing/config/config_wizard.py`.
- Prompt for `run.debug` in the wizard RUN section (Confirm/yes-no).
- Ensure `--init-config` runs the wizard and writes a TOML that includes `run.debug` with a clear prompt explaining its effect (skip TUI, print logs to terminal).

### Runtime behavior
- In `api_testing/__init__.py` after config load, read `run.debug`.
- If `run.debug` is true:
  - Skip `TUIApp` initialization entirely.
  - Do not call `suppress_console_logging()` (leave console logging active).
  - Set console log level to DEBUG via `set_console_level(logging.DEBUG)`.
  - Skip any TUI final report printing in `finally`.
- If `run.debug` is false:
  - Keep current TUI lifecycle (start, suppress during execution, stop, final report).

### CLI help text
- Update the CLI epilog in `api_testing/__init__.py` to mention TOML debug mode (no new flag).

## Data Flow
1. `load_config()` reads TOML and merges with defaults.
2. `main()` checks `config["run"]["debug"]`.
3. Branch:
   - `true`: no TUI, console DEBUG logging.
   - `false`: existing TUI behavior.

## Error Handling
- No new error paths; missing `run.debug` resolves from defaults.
- If config load fails, existing errors remain unchanged.

## Testing
- Manual smoke test:
  - Set `run.debug = true` and ensure no TUI launches; logs appear in terminal.
  - Set `run.debug = false` and ensure TUI launches as before.
- Optional: add unit tests for config loader defaults if test suite coverage is expanded later.

## Open Questions
- None.
