from __future__ import annotations

from rich.console import Console

from api_testing.config.config_loader import DEFAULT_CONFIG
from api_testing.config.config_wizard import (
    _build_summary_table,
    _confirm_field,
    _render_toml,
    _render_toml_with_comments,
)


def test_render_toml_includes_debug_flag() -> None:
    rendered = _render_toml(DEFAULT_CONFIG)

    assert "debug = false" in rendered
    assert "constraint_mining = true" in rendered
    assert "request_timeout_seconds = 300.0" in rendered


def test_render_toml_with_comments_includes_debug_flag() -> None:
    rendered = _render_toml_with_comments(DEFAULT_CONFIG)

    assert (
        "debug = false  # When true, skip the TUI and print logs to the terminal."
        in rendered
    )
    assert "constraint_mining = true  # Generate static, dynamic, and combined constraint artifacts during the run." in rendered


def test_summary_table_includes_debug_label_and_value() -> None:
    console = Console(record=True, force_terminal=True, width=120)
    table = _build_summary_table(DEFAULT_CONFIG)

    console.print(table)
    output = console.export_text()

    assert "Debug mode" in output
    assert "Constraint mining" in output
    assert "False" in output


def test_confirm_field_prints_help_and_uses_label(monkeypatch) -> None:
    console = Console(record=True, force_terminal=True, width=120)
    calls = {}

    def fake_ask(prompt, default=True, console=None):
        calls["prompt"] = prompt
        calls["default"] = default
        calls["console"] = console
        return True

    monkeypatch.setattr("api_testing.config.config_wizard.Confirm.ask", fake_ask)

    result = _confirm_field(
        "Debug mode (skip TUI, print logs)",
        "When true, skip the TUI and print logs to the terminal.",
        default=False,
        console=console,
    )

    assert result is True
    assert calls["prompt"] == "[cyan]Debug mode (skip TUI, print logs)[/cyan]"
    assert calls["default"] is False
    assert calls["console"] is console
    assert "When true, skip the TUI and print logs to the terminal." in console.export_text()
