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
        try:
            if event.event_type == EventType.PHASE_START:
                self._handle_phase_start(event)
            elif event.event_type == EventType.PHASE_COMPLETE:
                self._handle_phase_complete(event)
            elif event.event_type == EventType.OPERATION_UPDATE:
                self._handle_operation_update(event)
            elif event.event_type == EventType.EXECUTION_COMPLETE:
                self._handle_execution_complete(event)
        except Exception as e:
            # Re-raise with more context if possible, or just let EventEmitter catch it
            # But let's log the event data to help debug
            import sys
            print(f"Error processing event {event.event_type}: {e}", file=sys.stderr)
            print(f"Event data: {event}", file=sys.stderr)
            raise e

    def _handle_phase_start(self, event: EventData):
        if not event or not event.phase:
            return
        phase_name = event.phase.value.replace("_", " ").title()
        self._current_phase = event.phase

        if event.phase == Phase.TEST_EXECUTION:
            suppress_console_logging()
            self.display.start_live_display(self.tracker, "API Testing")
        else:
            self.display.print_phase_start(phase_name, event.message or "")

    def _handle_phase_complete(self, event: EventData):
        if not event or not event.phase:
            return
        phase_name = event.phase.value.replace("_", " ").title()

        if self._current_phase == Phase.TEST_EXECUTION:
            pass
        else:
            self.display.print_phase_complete(phase_name, event.message or "")

    def _handle_operation_update(self, event: EventData):
        if event and event.operation_name and event.status_code is not None:
            # Ensure generation is at least an int for comparison safety
            gen = event.generation if isinstance(event.generation, int) else 0
            
            self.tracker.add_operation_result(
                name=event.operation_name,
                method=event.operation_method or "",
                path=event.operation_path or "",
                generation=gen,
                status_code=event.status_code,
            )

    def _handle_execution_complete(self, event: EventData):
        self.display.stop_live_display()

    def print_final_report(self, **kwargs):
        self.report_gen.print_final_report(**kwargs)