# Rich TUI for APITesting Wizard - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace verbose debug logging with a Rich-based TUI that shows progress through each phase of API testing (config wizard → spec parse → graph build → config build → graph analyze → test execution → final report), displays per-operation status in a live table, and keeps debug logs flowing to `.cache/<api>/logs/` file only.

**Architecture:** Observer/Event Emitter pattern. Event emitter singleton notifies observers of lifecycle events. TUI runs as a separate observer, receives events, updates Rich display. Async-safe queue for thread-to-TUI communication.

**Tech Stack:** Python, `rich` (already in requirements.txt), existing logging infrastructure

---

## File Structure

```
api_testing/
  events/
    __init__.py          # Event package init
    types.py             # Phase, EventType enums; event dataclasses
    emitter.py           # EventEmitter singleton
  tui/
    __init__.py          # TUI package init
    themes.py            # TUITheme with colors/symbols
    display.py           # TUIDisplay class - Rich panels, live table
    progress.py          # ProgressTracker - per-op tracking, async aggregation
    report.py            # ReportGenerator - final Rich report
  __init__.py            # Modify: add emitter calls, suppress DEBUG console
  generators/
    executor.py          # Modify: add emitter calls
  utils/
    log.py               # Modify: add console_level parameter
  config/
    config_wizard.py     # Modify: use Rich prompts
```

---

## Task 1: Create Event Types and Emitter

**Files:**
- Create: `api_testing/events/__init__.py`
- Create: `api_testing/events/types.py`
- Create: `api_testing/events/emitter.py`

### Steps

- [ ] **Step 1: Create events package init**

```python
from .types import Phase, EventType, OperationStatus, EventData
from .emitter import EventEmitter, get_emitter

__all__ = ["Phase", "EventType", "OperationStatus", "EventData", "EventEmitter", "get_emitter"]
```

- [ ] **Step 2: Create event types**

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

class Phase(Enum):
    CONFIG_WIZARD = "config_wizard"
    SPEC_PARSE = "spec_parse"
    GRAPH_BUILD = "graph_build"
    CONFIG_BUILD = "config_build"
    GRAPH_ANALYZE = "graph_analyze"
    TEST_EXECUTION = "test_execution"
    FINAL_REPORT = "final_report"

class EventType(Enum):
    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"
    OPERATION_UPDATE = "operation_update"
    EXECUTION_COMPLETE = "execution_complete"
    ERROR = "error"

class OperationStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAIL = "fail"
    SKIPPED = "skipped"

@dataclass
class EventData:
    phase: Optional[Phase] = None
    event_type: Optional[EventType] = None
    operation_name: Optional[str] = None
    operation_method: Optional[str] = None
    operation_path: Optional[str] = None
    status: Optional[OperationStatus] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    response_size: Optional[int] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation: int = 0
    total_generations: int = 1
    completed_operations: int = 0
    total_operations: int = 0
```

- [ ] **Step 3: Create event emitter**

```python
import threading
import queue
from typing import Callable, List, Optional
from .types import EventData, EventType, Phase

class EventEmitter:
    _instance: Optional['EventEmitter'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._subscribers: List[Callable[[EventData], None]] = []
        self._event_queue: queue.Queue = queue.Queue()
        self._running = False
        self._processor_thread: Optional[threading.Thread] = None

    @classmethod
    def get(cls) -> 'EventEmitter':
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def subscribe(self, callback: Callable[[EventData], None]):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[EventData], None]):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(self, event_type: EventType, phase: Phase = None, **kwargs):
        data = EventData(event_type=event_type, phase=phase, **kwargs)
        self._event_queue.put(data)

    def _process_events(self):
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.1)
                for subscriber in self._subscribers:
                    try:
                        subscriber(event)
                    except Exception:
                        pass
                self._event_queue.task_done()
            except queue.Empty:
                continue

    def start(self):
        self._running = True
        self._processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processor_thread.start()

    def stop(self):
        self._running = False
        if self._processor_thread:
            self._processor_thread.join(timeout=1.0)

def get_emitter() -> EventEmitter:
    return EventEmitter.get()
```

- [ ] **Step 4: Commit**

```bash
git add api_testing/events/__init__.py api_testing/events/types.py api_testing/events/emitter.py
git commit -m "feat: add event types and emitter for TUI"
```

---

## Task 2: Create TUI Themes

**Files:**
- Create: `api_testing/tui/__init__.py`
- Create: `api_testing/tui/themes.py`

### Steps

- [ ] **Step 1: Create TUI package init**

```python
from .display import TUIDisplay
from .progress import ProgressTracker
from .report import ReportGenerator
from .themes import DEFAULT_THEME, TUITheme

__all__ = ["TUIDisplay", "ProgressTracker", "ReportGenerator", "DEFAULT_THEME", "TUITheme"]
```

- [ ] **Step 2: Create TUI themes**

```python
from dataclasses import dataclass

@dataclass
class TUITheme:
    primary: str = "cyan"
    secondary: str = "blue"
    accent: str = "magenta"
    text: str = "white"
    text_dim: str = "dim"
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "cyan"

    symbol_success: str = "✓"
    symbol_error: str = "✗"
    symbol_warning: str = "⚠"
    symbol_info: str = "●"
    symbol_progress: str = "→"
    symbol_bullet: str = "◆"

    symbol_success_color: str = "green"
    symbol_error_color: str = "red"
    symbol_warning_color: str = "yellow"
    symbol_info_color: str = "cyan"
    symbol_progress_color: str = "cyan"
    symbol_bullet_color: str = "blue"

    status_2xx: str = "green"
    status_3xx: str = "cyan"
    status_4xx: str = "yellow"
    status_5xx: str = "red"
    status_unknown: str = "dim"

    progress_complete: str = "cyan"
    progress_remaining: str = "dim"

    def get_status_color(self, code: int) -> str:
        if 200 <= code < 300:
            return self.status_2xx
        elif 300 <= code < 400:
            return self.status_3xx
        elif 400 <= code < 500:
            return self.status_4xx
        elif 500 <= code < 600:
            return self.status_5xx
        return self.status_unknown

DEFAULT_THEME = TUITheme()
```

- [ ] **Step 3: Commit**

```bash
git add api_testing/tui/__init__.py api_testing/tui/themes.py
git commit -m "feat: add TUI themes"
```

---

## Task 3: Create Progress Tracker

**Files:**
- Create: `api_testing/tui/progress.py`

### Steps

- [ ] **Step 1: Create progress tracker**

```python
from dataclasses import dataclass, field
from typing import Dict, Optional
from collections import defaultdict
from api_testing.events.types import OperationStatus

@dataclass
class OperationProgress:
    name: str
    method: str
    path: str
    status: OperationStatus = OperationStatus.PENDING
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    response_size: Optional[int] = None
    generation: int = 0

class ProgressTracker:
    def __init__(self):
        self._operations: Dict[str, OperationProgress] = {}
        self._generation_stats: Dict[int, dict] = defaultdict(lambda: {
            "completed": 0,
            "failed": 0,
            "total": 0
        })

    def add_operation(self, name: str, method: str, path: str, generation: int = 0):
        key = f"{generation}:{name}"
        self._operations[key] = OperationProgress(
            name=name,
            method=method,
            path=path,
            generation=generation
        )
        self._generation_stats[generation]["total"] += 1

    def update_operation(self, name: str, generation: int, status: OperationStatus,
                         status_code: Optional[int] = None, duration_ms: Optional[float] = None,
                         response_size: Optional[int] = None):
        key = f"{generation}:{name}"
        if key in self._operations:
            op = self._operations[key]
            op.status = status
            op.status_code = status_code
            op.duration_ms = duration_ms
            op.response_size = response_size

            if status == OperationStatus.SUCCESS:
                self._generation_stats[generation]["completed"] += 1
            elif status == OperationStatus.FAIL:
                self._generation_stats[generation]["failed"] += 1

    def get_operations(self):
        return list(self._operations.values())

    def get_generation_stats(self, generation: int) -> dict:
        return self._generation_stats.get(generation, {"completed": 0, "failed": 0, "total": 0})

    def get_total_completed(self) -> int:
        return sum(s["completed"] for s in self._generation_stats.values())

    def get_total_failed(self) -> int:
        return sum(s["failed"] for s in self._generation_stats.values())

    def get_total_operations(self) -> int:
        return sum(s["total"] for s in self._generation_stats.values())

    def reset(self):
        self._operations.clear()
        self._generation_stats.clear()
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/tui/progress.py
git commit -m "feat: add progress tracker"
```

---

## Task 4: Create TUI Display

**Files:**
- Create: `api_testing/tui/display.py`

### Steps

- [ ] **Step 1: Create TUI display**

```python
from typing import Optional, List, Dict
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED, DOUBLE

from .themes import DEFAULT_THEME, TUITheme
from .progress import ProgressTracker

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
            content = Align.center(Text("".join([str(title), "\n", str(desc)])))

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
            content = Text("".join([str(title), "\n", str(detail_text)]))

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

    def _build_execution_table(self, operations: List, title_suffix: str = "") -> Panel:
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
        stats_panel = self._build_stats_table(stats[0], stats[1], stats[2], current_gen, 1)

        header = Text()
        header.append("⚡ ", style=f"bold {self.theme.warning}")
        header.append(title.upper(), style=f"bold {self.theme.primary}")
        header.append(" ⚡", style=f"bold {self.theme.warning}")

        from rich.columns import Columns
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
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/tui/display.py
git commit -m "feat: add TUI display with live execution table"
```

---

## Task 5: Create Report Generator

**Files:**
- Create: `api_testing/tui/report.py`

### Steps

- [ ] **Step 1: Create report generator**

```python
from typing import Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
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
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/tui/report.py
git commit -m "feat: add report generator"
```

---

## Task 6: Modify Log Utility to Suppress Console DEBUG

**Files:**
- Modify: `api_testing/utils/log.py`

### Steps

- [ ] **Step 1: Add console_level parameter to configure_logging**

```python
import logging
import os

logger = None
_log_dir = "./logs"
_log_level = logging.DEBUG
_log_llm_model = 'default'
_console_level = logging.INFO

def getLogger(name: str|None = None):
    global logger
    if logger is None:
        return configure_logging(name)
    if name:
        logger.name = name
    return logger

def configure_logging(class_name: str = __name__, log_dir=None, level=None, llm_model=None, console_level=None):
    global logger, _log_dir, _log_level, _log_llm_model, _console_level
    log_dir = os.path.join(log_dir, "logs") if log_dir else _log_dir
    level = level or _log_level
    llm_model = llm_model or _log_llm_model
    console_level = console_level or _console_level

    print(f"Logging to {log_dir} at level {level} for model {llm_model}")

    os.makedirs(log_dir, exist_ok=True)
    log = logging.getLogger(class_name)
    log.setLevel(level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level)
    log.addHandler(console_handler)

    log_path = os.path.join(log_dir, f"{llm_model}.log")
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    log.addHandler(file_handler)

    logger = log
    return logger

def set_console_level(level: int):
    global _console_level, logger
    _console_level = level
    if logger:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(level)
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/utils/log.py
git commit -m "feat: add console_level parameter to suppress DEBUG in terminal"
```

---

## Task 7: Wire Emitter into APITesting Orchestrator

**Files:**
- Modify: `api_testing/__init__.py`

### Steps

- [ ] **Step 1: Import emitter and add phase events to run_tests**

Add to imports:
```python
from api_testing.events import get_emitter, EventType, Phase, OperationStatus
from api_testing.utils.log import configure_logging, set_console_level
```

In `run_tests` method, after setup futures complete, add:
```python
emitter = get_emitter()
emitter.emit(EventType.PHASE_START, Phase.GRAPH_BUILD, message="Building operation graph...")
```

After graph/config load:
```python
emitter.emit(EventType.PHASE_COMPLETE, Phase.GRAPH_BUILD, message=f"Graph built with {len(nodes)} operations")
```

For each node in DFS, emit operation updates:
```python
emitter.emit(
    EventType.OPERATION_UPDATE,
    phase=Phase.TEST_EXECUTION,
    operation_name=node.name,
    operation_method=node.name.split('-')[0] if '-' in node.name else '',
    operation_path=node.name,
    status=OperationStatus.RUNNING,
    generation=idx + 1,
    total_generations=num_generations,
    completed_operations=completed_count,
    total_operations=total_count,
)
```

After execution completes:
```python
emitter.emit(EventType.EXECUTION_COMPLETE, Phase.FINAL_REPORT, message="All generations complete")
```

Also add at the start of run_tests:
```python
emitter.emit(EventType.PHASE_START, Phase.CONFIG_BUILD, message="Building configuration...")
```

- [ ] **Step 2: Set console level to INFO at start of APITesting**

In `_load_` or `run_tests`, add:
```python
set_console_level(logging.INFO)
```

- [ ] **Step 3: Commit**

```bash
git add api_testing/__init__.py
git commit -m "feat: wire event emitter into APITesting orchestrator"
```

---

## Task 8: Wire Emitter into Executor

**Files:**
- Modify: `api_testing/generators/executor.py`

### Steps

- [ ] **Step 1: Import emitter and emit operation events**

Add to imports:
```python
from api_testing.events import get_emitter, EventType, Phase, OperationStatus
```

In `exec()` method, after getting responses:
```python
emitter = get_emitter()
for entry in entries:
    status = OperationStatus.SUCCESS if isSuccessful(entry.get("response", {}).get("status", 0)) else OperationStatus.FAIL
    emitter.emit(
        EventType.OPERATION_UPDATE,
        phase=Phase.TEST_EXECUTION,
        operation_name=self.operation.uuid if self.operation else "unknown",
        status=status,
        status_code=entry.get("response", {}).get("status"),
        duration_ms=entry.get("duration_ms"),
        response_size=len(str(entry.get("response", {}).get("body", ""))),
    )
```

Same for `exec_async()` method.

- [ ] **Step 2: Commit**

```bash
git add api_testing/generators/executor.py
git commit -m "feat: wire event emitter into Executor"
```

---

## Task 9: Modify Config Wizard to Use Rich Prompts

**Files:**
- Modify: `api_testing/config/config_wizard.py`

### Steps

- [ ] **Step 1: Import Rich and update prompt functions**

Add to imports:
```python
from rich.prompt import Prompt, Confirm
from rich.console import Console
```

Add at start of functions:
```python
console = Console()
```

Replace `input()` calls with `Prompt.ask()`:
```python
# Old: value = input(f"{label}{suffix}: ").strip()
# New: value = Prompt.ask(f"[cyan]{label}[/cyan]{suffix}", default=default or "")
```

Replace boolean prompts:
```python
# Old: value = input(f"{label} (y/n): ").lower()
# New: value = Confirm.ask(f"[yellow]{label}[/yellow]", default=default)
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/config/config_wizard.py
git commit -m "feat: use Rich prompts in config wizard"
```

---

## Task 10: Create TUI Integration Layer

**Files:**
- Create: `api_testing/tui/app.py` (orchestrates TUI based on events)

### Steps

- [ ] **Step 1: Create TUI app that listens to events**

```python
from api_testing.events import get_emitter, EventType, Phase, EventData
from api_testing.tui import TUIDisplay, ProgressTracker, ReportGenerator, DEFAULT_THEME
from api_testing.tui.progress import OperationProgress

class TUIApp:
    def __init__(self, theme=DEFAULT_THEME, width=100):
        self.display = TUIDisplay(theme=theme, width=width)
        self.tracker = ProgressTracker()
        self.report_gen = ReportGenerator(theme=theme, width=width)
        self._current_phase = None
        self._emitter = get_emitter()
        self._generation_stats = {}

    def start(self):
        self._emitter.subscribe(self._on_event)
        self._emitter.start()

    def stop(self):
        self._emitter.stop()
        self._emitter.unsubscribe(self._on_event)

    def _on_event(self, event: EventData):
        if event.event_type == EventType.PHASE_START:
            self._handle_phase_start(event)
        elif event.event_type == EventType.PHASE_COMPLETE:
            self._handle_phase_complete(event)
        elif event.event_type == EventType.OPERATION_UPDATE:
            self._handle_operation_update(event)
        elif event.event_type == EventType.EXECUTION_COMPLETE:
            self._handle_execution_complete(event)

    def _handle_phase_start(self, event: EventData):
        phase_name = event.phase.value.replace("_", " ").title() if event.phase else "Unknown"
        self.display.print_phase_start(phase_name, event.message or "")
        self._current_phase = event.phase

    def _handle_phase_complete(self, event: EventData):
        phase_name = event.phase.value.replace("_", " ").title() if event.phase else "Unknown"
        self.display.print_phase_complete(phase_name, event.message or "")

    def _handle_operation_update(self, event: EventData):
        if event.operation_name:
            self.tracker.add_operation(
                name=event.operation_name,
                method=event.operation_method or "",
                path=event.operation_path or "",
                generation=event.generation,
            )
            self.tracker.update_operation(
                name=event.operation_name,
                generation=event.generation,
                status=event.status,
                status_code=event.status_code,
                duration_ms=event.duration_ms,
                response_size=event.response_size,
            )
            if self._current_phase == Phase.TEST_EXECUTION:
                self.display.update_live_display()

    def _handle_execution_complete(self, event: EventData):
        self.display.stop_live_display()

    def print_final_report(self, **kwargs):
        self.report_gen.print_final_report(**kwargs)
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/tui/app.py
git commit -m "feat: add TUI app integration layer"
```

---

## Task 11: Integrate TUI into Main CLI

**Files:**
- Modify: `api_testing/__init__.py` (add TUI app initialization and final report)

### Steps

- [ ] **Step 1: Import and initialize TUI app in CLI**

Add to imports:
```python
from api_testing.tui.app import TUIApp
```

In `main()` function, before running tests:
```python
tui_app = TUIApp()
tui_app.start()
```

After tests complete:
```python
tui_app.print_final_report(
    title=base_title,
    duration_seconds=elapsed,
    total_requests=total_testcase,
    status_distribution=status_counts,
    total_operations=len(successFull),
    successful_operations=len(successFull),
    unique_5xx_errors=unique_5xx,
)
tui_app.stop()
```

- [ ] **Step 2: Commit**

```bash
git add api_testing/__init__.py
git commit -m "feat: integrate TUI app into main CLI"
```

---

## Verification

- [ ] **Step 1: Run demo.py and verify TUI displays**

Run: `python demo.py`

Expected: Rich TUI shows phases, live execution table, final report

- [ ] **Step 2: Verify debug logs still written to file**

Check: `.cache/<api>/logs/<model>.log` contains DEBUG level logs

---

## Plan Complete

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**