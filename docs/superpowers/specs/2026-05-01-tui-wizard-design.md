# Rich TUI for APITesting Wizard - Design

## Goal

Replace verbose debug logging in CLI with a modern Rich-based Terminal User Interface (TUI) that:
- Shows progress through each phase of API testing (config wizard → spec parse → graph build → config build → graph analyze → test execution → final report)
- Displays per-operation status updates in a live table during execution
- Keeps debug logs flowing to `.cache/<api>/logs/` file only (not to terminal)
- Mirrors the elegant phase-based UI of AutoRestTest baseline

## Non-Goals

- No time-duration limiting (not a RL agent, it's deterministic graph traversal)
- No Q-learning or mutation ratio display during execution (simple pass/fail per request)
- No dynamic exploration/exploitation - runs full dependency graph

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    TUI Display                       │
│  (Rich panels, live updates, progress tracking)      │
└───────────────────────┬─────────────────────────────┘
                        │ events (observer pattern)
┌───────────────────────▼─────────────────────────────┐
│              Event Bus / Observer System             │
│   (phase_start, operation_update, execution_complete)│
└───────────────────────┬─────────────────────────────┘
                        │ notifications
┌───────────────────────▼─────────────────────────────┐
│              APITesting Orchestrator                 │
│   (parse spec → build graph → execute tests)          │
└───────────────────────┬─────────────────────────────┘
                        │ logs (to file only)
                    ┌───▼───┐
                    │ .log  │
                    └───────┘
```

### Pattern: Observer/Callback

- Event emitter singleton (`api_testing/events/emitter.py`) notifies observers of lifecycle events
- TUI runs as a separate observer, receives events, updates Rich display
- Existing code stays mostly unchanged; just add `EventEmitter.get().emit("phase_start", ...)` calls
- Async-safe queue for thread-to-TUI communication (during parallel async execution)

## Phase Structure (7 phases)

| # | Phase | Display | Duration |
|---|-------|---------|----------|
| 1 | Config Wizard | Interactive Rich prompts (text inputs, confirmations) | User-controlled |
| 2 | Parse Specification | Loading spinner + "Loaded X operations" | Fast |
| 3 | Build Operation Graph | Live table: operation name, status (pending/embedding/LLM/done), progress bar | Slow (LLM calls) |
| 4 | Build Configuration | Progress bar with count (N/M operations) | Medium |
| 5 | Analyze Graph | Forest diagram preview (root nodes listed) | Fast |
| 6 | Execute Tests | Live table with all operations, status codes, success/fail, real-time updates | Slowest |
| 7 | Final Report | Rich table: summary stats, status code distribution bar chart | End |

## Components to Create

### New Files

| File | Purpose |
|------|---------|
| `api_testing/events/__init__.py` | Event package init |
| `api_testing/events/types.py` | Event dataclasses and Phase enum |
| `api_testing/events/emitter.py` | EventEmitter singleton - emits and queues events |
| `api_testing/tui/__init__.py` | TUI package init |
| `api_testing/tui/themes.py` | TUITheme dataclass with colors/symbols |
| `api_testing/tui/display.py` | TUIDisplay class - Rich panels, live table, phase headers |
| `api_testing/tui/progress.py` | ProgressTracker - per-operation tracking, async tree aggregation |
| `api_testing/tui/report.py` | ReportGenerator - final Rich-formatted report |

### Modify Existing Files

| File | Changes |
|------|---------|
| `api_testing/__init__.py` | Import emitter, emit events in `run_tests()`, suppress DEBUG console output |
| `api_testing/generators/executor.py` | Import emitter, emit `operation_update` events during exec/exec_async |
| `api_testing/utils/log.py` | Add `console_level` parameter to suppress DEBUG in terminal |
| `api_testing/config/config_wizard.py` | Use Rich `Prompt` and `Confirm` for interactive prompts |

## Events and Data Flow

### Event Types

```python
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
```

### Data Flow

1. Config wizard emits events → TUI shows prompts with Rich
2. `APITesting._load_()` → `phase_start(spec_parse)` → `operation_update` (per spec) → `phase_complete`
3. `APITesting.run_tests()` → `phase_start(graph_build)` → `operation_update` (per graph node) → `phase_complete`
4. For each generation: `operation_update` (running/completed/failed per op) in unified merged view
5. At end: `execution_complete` → Final Report

## Phase Display Details

### Phase 1: Config Wizard

- Rich `Prompt.ask()` for text inputs, `Confirm.ask()` for y/n questions
- Shows current section highlighted: `[project]` / `[llm]` / `[embedding]` / `[run]` / `[headers]`
- Progress indicator: "Step 2 of 6: LLM Configuration"

### Phase 2: Parse Specification

- Spinner + "Loading specification from {spec_path}..."
- On complete: "✓ Parsed {count} operations from {spec_title}"

### Phase 3: Build Operation Graph

- Live table with columns: `Operation` | `Method` | `Endpoint` | `Status` | `Progress`
- Status values: `pending` → `embedding` → `LLM mapping` → `complete`
- Progress bar per operation (for LLM calls that take time)
- Shows current operation name when processing

### Phase 4: Build Configuration

- Progress bar: "Building configuration... [{bar}] {percent}%"
- Below: "Processing: {operation_name} ({count}/{total})"

### Phase 5: Analyze Graph

- Simple panel: "Analyzing dependency graph..."
- On complete: "✓ Found {n} root operations, {m} total sequences"

### Phase 6: Execute Tests (main phase)

- Full live table with columns:
  - `#` | `Operation` | `Method` | `Path` | `Status` | `Duration` | `Size`
- Status shows: `pending` → `running` → `200` / `404` / `500` etc.
- Generation indicator: "Generation 1/{num_generations}"
- Async trees merged into single unified view (all parallel operations interleaved)
- Requests/second and total count at bottom

### Phase 7: Final Report

- Rich Table with summary stats
- Status code distribution with visual bars (like AutoRestTest)
- Success rate, total time, operations covered, operations with 5xx errors

## Debug Logs

- Continue logging to `.cache/<api>/logs/*.log` via existing `configure_logging`
- DEBUG level logs written to file but NOT printed to console during wizard
- Console logging level controlled by `console_level` in log configuration
- After wizard completes, show: `"Full logs available at: .cache/<api>/logs/"`

## Async Handling

- During `async_mode`, multiple trees execute in parallel via `asyncio.gather`
- Events from different trees arrive concurrently via thread-safe queue
- `ProgressTracker` merges updates from all trees by operation name
- TUI displays unified view: all operations interleaved by completion time

## Testing Approach

- Manual verification: run `python demo.py` and observe TUI phases
- Check `.cache/<api>/logs/` contains debug logs after run
- Verify config wizard prompts display correctly with Rich

## Dependencies

- `rich` - already in `requirements.txt` (AutoRestTest baseline uses it)
- No new dependencies required

## File Structure

```
api_testing/
  events/
    __init__.py
    types.py        # Phase, EventType, event dataclasses
    emitter.py      # EventEmitter singleton
  tui/
    __init__.py
    themes.py       # TUITheme with colors/symbols
    display.py      # TUIDisplay class
    progress.py     # ProgressTracker
    report.py       # ReportGenerator
  __init__.py       # Modify: add emitter calls, suppress DEBUG console
  generators/
    executor.py     # Modify: add emitter calls
  utils/
    log.py          # Modify: add console_level parameter
  config/
    config_wizard.py # Modify: use Rich prompts
```