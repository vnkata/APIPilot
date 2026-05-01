from typing import Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED, DOUBLE
from rich.columns import Columns

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
        report_title = Text()
        report_title.append("FINAL REPORT", style=f"bold {self.theme.primary}")

        status_table = Table(
            box=ROUNDED,
            border_style=self.theme.accent,
            title="Status Code Distribution",
            title_style=f"bold {self.theme.secondary}",
            show_header=True,
            header_style=f"bold {self.theme.text}",
        )
        status_table.add_column("Code", style=self.theme.text_dim, width=6, justify="center")
        status_table.add_column("Count", justify="right", width=10)
        status_table.add_column("Distribution", width=40)

        max_count = max(status_distribution.values()) if status_distribution else 1
        for code, count in sorted(status_distribution.items()):
            color = self.theme.get_status_color(code)
            bar_width = int((count / max_count) * 35)
            bar = f"[{color}]{'█' * bar_width}{'░' * (35 - bar_width)}[/{color}]"
            status_table.add_row(
                f"[{color}]{code}[/{color}]",
                f"[{color}]{count:,}[/{color}]",
                bar,
            )

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
        success_pct = (successful_operations / max(total_operations, 1)) * 100
        success_color = (
            self.theme.success if success_pct >= 70 else
            self.theme.warning if success_pct >= 40 else
            self.theme.error
        )

        summary_table.add_row("API Title", title)
        summary_table.add_row("Duration", f"{minutes}m {secs}s")
        summary_table.add_row("Total Requests", f"{total_requests:,}")
        summary_table.add_row("Total Operations", str(total_operations))
        summary_table.add_row(
            "Successful Operations",
            f"[{success_color}]{successful_operations} ({success_pct:.1f}%)[/{success_color}]",
        )
        summary_table.add_row(
            "Unique 5xx Errors",
            f"[{self.theme.error if unique_5xx_errors > 0 else self.theme.success}]{unique_5xx_errors}[/]",
        )

        panel = Panel(
            Columns([summary_table, status_table], expand=True, equal=True),
            box=DOUBLE,
            border_style=self.theme.primary,
            padding=(1, 2),
        )

        self.console.print()
        self.console.print(panel)