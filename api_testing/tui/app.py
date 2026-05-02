import time
from api_testing.events import get_emitter, EventType, Phase, EventData
from api_testing.events.emitter import EventEmitter
from api_testing.tui.display import TUIDisplay
from api_testing.tui.progress import ProgressTracker
from api_testing.tui.report import ReportGenerator
from api_testing.tui.themes import DEFAULT_THEME
from api_testing.utils.log import suppress_console_logging

class TUIApp:
    def __init__(self, theme=DEFAULT_THEME, width=100):
        EventEmitter.reset()
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
        self._emitter.drain_queue()
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
        self._current_phase = event.phase

        if event.phase == Phase.TEST_EXECUTION:
            suppress_console_logging()
            self.display.start_live_display(self.tracker, "API Testing")
        else:
            self.display.print_phase_start(phase_name, event.message or "")

    def _handle_phase_complete(self, event: EventData):
        phase_name = event.phase.value.replace("_", " ").title() if event.phase else "Unknown"

        if self._current_phase == Phase.TEST_EXECUTION:
            pass
        else:
            self.display.print_phase_complete(phase_name, event.message or "")

    def _handle_operation_update(self, event: EventData):
        if event.operation_name and event.status_code is not None:
            self.tracker.add_operation_result(
                name=event.operation_name,
                method=event.operation_method or "",
                path=event.operation_path or "",
                generation=event.generation,
                status_code=event.status_code,
            )
            if self._current_phase == Phase.TEST_EXECUTION:
                self.display.update_live_display()

    def _handle_execution_complete(self, event: EventData):
        self.display.stop_live_display()

    def print_final_report(self, **kwargs):
        self.report_gen.print_final_report(**kwargs)