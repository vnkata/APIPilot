import time
import threading
from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED

from .themes import DEFAULT_THEME, TUITheme
from .progress import ProgressTracker, OperationData

class TUIDisplay:
    def __init__(self, theme: TUITheme = DEFAULT_THEME, width: int = 100):
        self.console = Console(force_terminal=True, width=width)
        self.theme = theme
        self.width = width
        self._live: Optional[Live] = None
        self._tracker: Optional[ProgressTracker] = None
        self._start_time: float = 0
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None

    def clear(self):
        self.console.clear()

    def print_phase_start(self, phase_name: str, description: str = ""):
        title = Text()
        title.append(f" {phase_name.upper()} ", style=f"bold {self.theme.primary}")
        content = Align.center(title)
        if description:
            desc = Text(description, style=self.theme.text_dim, justify="center")
            content = Text(f"{title}\n{desc}")

        panel = Panel(
            content,
            box=ROUNDED,
            border_style=self.theme.primary,
            padding=(1, 2),
        )
        self.console.print()
        self.console.print(panel)

    def print_phase_complete(self, phase_name: str, details: Optional[str] = None):
        title = Text()
        title.append(self.theme.symbol_success + " ", style=self.theme.success)
        title.append(f"{phase_name} Complete", style=f"bold {self.theme.success}")

        content = Align.center(title)
        if details:
            detail_text = Text(details, style=self.theme.text_dim, justify="center")
            content = Text(f"{title}\n{detail_text}")

        panel = Panel(
            content,
            box=ROUNDED,
            border_style=self.theme.success,
            padding=(0, 2),
        )
        self.console.print(panel)

    def print_message(self, message: str, status: str = "info"):
        symbols = {
            "info": (self.theme.symbol_info, self.theme.symbol_info_color),
            "success": (self.theme.symbol_success, self.theme.symbol_success_color),
            "warning": (self.theme.symbol_warning, self.theme.symbol_warning_color),
            "error": (self.theme.symbol_error, self.theme.symbol_error_color),
        }
        symbol, color = symbols.get(status, (self.theme.symbol_bullet, self.theme.symbol_bullet_color))
        self.console.print(f"  [{color}]{symbol}[/{color}] {message}")

    def _get_status_color(self, status_code: int) -> str:
        if 200 <= status_code < 300:
            return self.theme.success
        elif 300 <= status_code < 400:
            return self.theme.info
        elif 400 <= status_code < 500:
            return self.theme.warning
        elif 500 <= status_code < 600:
            return self.theme.error
        return self.theme.text_dim

    def _build_status_line(self, op: OperationData) -> Text:
        if not op.status_codes or not isinstance(op.status_codes, dict):
            return Text("")
        sorted_codes = sorted(op.status_codes.items(), key=lambda x: x[1], reverse=True)
        if not sorted_codes:
            return Text("")
        max_count = sorted_codes[0][1] if sorted_codes else 1
        bar_width = 10

        parts = []
        for code, count in sorted_codes:
            filled = int((count / max_count) * bar_width) if max_count > 0 else 0
            bar = "█" * filled + "░" * (bar_width - filled)
            color = self._get_status_color(code)
            parts.append(f"[{color}]{code} ({count}) {bar}[/{color}]")

        return Text.from_markup("  ".join(parts))

    def _build_operation_block(self, op: OperationData) -> list:
        """Returns list of Text lines: name + one per status code."""
        lines = []
        lines.append(Text.from_markup(f"[bold]{op.name}[/bold]"))
        if op.status_codes and isinstance(op.status_codes, dict) and op.status_codes:
            try:
                max_count = max(op.status_codes.values())
            except (TypeError, ValueError):
                max_count = 1
            for code, count in sorted(op.status_codes.items(), key=lambda x: x[1], reverse=True):
                filled = int((count / max_count) * 10)
                bar = "█" * filled + "░" * (10 - filled)
                color = self._get_status_color(code)
                lines.append(Text.from_markup(f"  [{color}]{code:>3}[/{color}] ({count:>3}) [dim]{bar}[/dim]"))
        else:
            lines.append(Text.from_markup(f"  [dim]Waiting...[/dim]"))
        return lines

    def _build_operations_list(self) -> list:
        if not self._tracker:
            return [Text.from_markup("[dim]Waiting for operations...[/dim]")]

        blocks = []
        for op in self._tracker.get_operations():
            blocks.extend(self._build_operation_block(op))
            blocks.append(Text(""))

        return blocks

    def _build_operation_text(self) -> Text:
        """Build a single Text object with all operations preserving colors."""
        try:
            operations = self._build_operations_list()
            if not operations:
                return Text.from_markup("[dim]Waiting for operations...[/dim]")

            parts = []
            for op in operations:
                if isinstance(op, Text):
                    parts.append(op)
                else:
                    parts.append(Text(str(op)))
            return Text("\n").join(parts)
        except Exception:
            return Text.from_markup("[dim]Updating...[/dim]")

    def _build_display(self) -> Panel:
        elapsed = time.time() - self._start_time
        total_requests = self._tracker.get_total_requests() if self._tracker else 0

        header = Text()
        header.append(">> ", style=f"bold {self.theme.warning}")
        header.append("API TESTING", style=f"bold {self.theme.primary}")
        header.append(" <<", style=f"bold {self.theme.warning}")
        header.append("    Total: ", style=self.theme.text_dim)
        header.append(f"{total_requests:,}", style=f"bold {self.theme.success}")
        header.append("   Elapsed: ", style=self.theme.text_dim)
        header.append(f"{elapsed:.1f}s", style=f"bold {self.theme.text}")

        content = self._build_operation_text()

        return Panel(
            content,
            title=header,
            title_align="left",
            box=ROUNDED,
            border_style=self.theme.primary,
            padding=(1, 2),
        )

    def start_live_display(self, tracker: ProgressTracker, title: str = "API Testing"):
        if self._live:
            self.stop_live_display()
        self._tracker = tracker
        self._start_time = time.time()
        self._live = Live(
            self._build_display(),
            console=self.console,
            refresh_per_second=60,
            transient=True,
        )
        self._stop_event = threading.Event()
        self._update_thread = threading.Thread(target=self._run_update_loop, daemon=True)
        self._live.start()
        self._update_thread.start()

    def _run_update_loop(self):
        while not self._stop_event.wait(0.017):  # ~60 FPS
            self.update_live_display()

    def update_live_display(self):
        if self._live and self._tracker:
            try:
                self._live.update(self._build_display())
            except Exception as e:
                import sys
                print(f"Live update error: {e}", file=sys.stderr)

    def stop_live_display(self):
        if self._stop_event:
            self._stop_event.set()
        if self._update_thread:
            self._update_thread.join(timeout=0.5)
        if self._live:
            self._live.stop()
            self._live = None
            self._update_thread = None
            self._stop_event = None