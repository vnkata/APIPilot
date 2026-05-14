from typing import Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from rich.align import Align

from .themes import DEFAULT_THEME, TUITheme

class ReportGenerator:
    def __init__(self, theme: TUITheme = DEFAULT_THEME, width: int = 100):
        self.console = Console(force_terminal=True, width=width)
        self.theme = theme
        self.width = width

    def print_final_report(
        self,
        title: str,
        duration_seconds: float,
        total_requests: int,
        status_distribution: Dict[int, int],
        total_operations: int,
        successful_operations: int,
        unique_5xx_errors: int,
    ):
        summary_table = Table(
            box=ROUNDED,
            border_style=self.theme.info,
            title="Summary Statistics",
            title_style=f"bold {self.theme.info}",
            show_header=False,
        )
        summary_table.add_column("Metric", style=self.theme.text_dim)
        summary_table.add_column("Value", style=f"bold {self.theme.text}", justify="right")

        minutes, secs = divmod(int(duration_seconds), 60)

        summary_table.add_row("API Title", title)
        summary_table.add_row("Duration", f"{minutes}m {secs}s")
        summary_table.add_row("Total Requests", f"{total_requests:,}")
        summary_table.add_row("Total Operations", str(total_operations))

        panel = Panel(
            Align.center(summary_table),
            box=DOUBLE,
            border_style=self.theme.primary,
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(panel)