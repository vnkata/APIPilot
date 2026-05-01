from typing import Optional, List, Dict
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED, DOUBLE
from rich.columns import Columns

from .themes import DEFAULT_THEME, TUITheme
from .progress import ProgressTracker, OperationProgress

class TUIDisplay:
    def __init__(self, theme: TUITheme = DEFAULT_THEME, width: int = 100):
        self.console = Console(force_terminal=True, width=width)
        self.theme = theme
        self.width = width
        self._live: Optional[Live] = None
        self._tracker: Optional[ProgressTracker] = None

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
            box=DOUBLE,
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

    def _build_execution_table(self, operations: List[OperationProgress], title_suffix: str = "") -> Panel:
        table = Table(
            box=ROUNDED,
            border_style=self.theme.accent,
            show_header=True,
            header_style=f"bold {self.theme.secondary}",
            padding=(0, 1),
        )
        table.add_column("#", width=4, justify="center")
        table.add_column("Operation", width=25)
        table.add_column("Method", width=6, justify="center")
        table.add_column("Path", width=35)
        table.add_column("Status", width=8, justify="center")
        table.add_column("Duration", width=10, justify="right")
        table.add_column("Size", width=10, justify="right")

        for idx, op in enumerate(operations, 1):
            status_str = op.status.value
            status_color = self.theme.text_dim
            if op.status.value == "success":
                status_color = self.theme.success
                status_str = str(op.status_code) if op.status_code else "OK"
            elif op.status.value == "fail":
                status_color = self.theme.error
                status_str = str(op.status_code) if op.status_code else "ERR"
            elif op.status.value == "running":
                status_color = self.theme.warning
                status_str = "..."

            duration_str = f"{op.duration_ms:.0f}ms" if op.duration_ms else "-"
            size_str = f"{op.response_size}B" if op.response_size else "-"

            table.add_row(
                str(idx),
                op.name[:25],
                f"[{self.theme.info}]{op.method}[/{self.theme.info}]",
                op.path[:35],
                f"[{status_color}]{status_str}[/{status_color}]",
                duration_str,
                size_str,
            )

        header = Text()
        header.append("EXECUTION", style=f"bold {self.theme.primary}")
        if title_suffix:
            header.append(f" - {title_suffix}", style=self.theme.text_dim)

        return Panel(
            table,
            title=header,
            title_align="left",
            box=DOUBLE,
            border_style=self.theme.primary,
            padding=(1, 1),
        )

    def _build_stats_table(self, completed: int, failed: int, total: int, generation: int, total_gen: int) -> Panel:
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Metric", style=self.theme.text_dim, ratio=2)
        table.add_column("Value", style=f"bold {self.theme.text}", justify="right", ratio=1)

        success_rate = (completed / max(total, 1)) * 100
        success_color = self.theme.success if success_rate >= 70 else (self.theme.warning if success_rate >= 40 else self.theme.error)

        table.add_row("Completed:", f"[{self.theme.success}]{completed:,}[/{self.theme.success}]")
        table.add_row("Failed:", f"[{self.theme.error}]{failed:,}[/{self.theme.error}]")
        table.add_row("Success Rate:", f"[{success_color}]{success_rate:.1f}%[/{success_color}]")
        table.add_row("Generation:", f"[{self.theme.info}]{generation}/{total_gen}[/{self.theme.info}]")

        header = Text()
        header.append("STATISTICS", style=f"bold {self.theme.primary}")

        return Panel(
            table,
            title=header,
            title_align="left",
            box=ROUNDED,
            border_style=self.theme.info,
            padding=(0, 1),
        )

    def start_live_display(self, tracker: ProgressTracker, title: str = "API Testing"):
        self._tracker = tracker
        self._live = Live(
            self._generate_live_display(title),
            console=self.console,
            refresh_per_second=4,
            transient=False,
        )
        self._live.start()

    def _generate_live_display(self, title: str):
        if not self._tracker:
            return Panel(Text("Initializing..."), title=title)

        operations = self._tracker.get_operations()
        stats = self._tracker.get_total_completed(), self._tracker.get_total_failed(), self._tracker.get_total_operations()

        from collections import Counter
        generation_counts = Counter(op.generation for op in operations)
        current_gen = max(generation_counts.keys()) if generation_counts else 0

        table_panel = self._build_execution_table(operations)
        stats_panel = self._build_stats_table(stats[0], stats[1], stats[2], current_gen, self._tracker.get_max_generation())

        header = Text()
        header.append("⚡ ", style=f"bold {self.theme.warning}")
        header.append(title.upper(), style=f"bold {self.theme.primary}")
        header.append(" ⚡", style=f"bold {self.theme.warning}")

        return Panel(
            Columns([stats_panel, table_panel], expand=True),
            title=header,
            title_align="center",
            box=DOUBLE,
            border_style=self.theme.primary,
            padding=(1, 2),
        )

    def update_live_display(self):
        if self._live and self._tracker:
            self._live.update(self._generate_live_display("API Testing"))

    def stop_live_display(self):
        if self._live:
            self._live.stop()
            self._live = None