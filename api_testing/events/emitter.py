import logging
import threading
import queue
from typing import Callable, List, Optional
from .types import EventData, EventType, Phase

logger = logging.getLogger(__name__)

class EventEmitter:
    _instance: Optional['EventEmitter'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._subscribers: List[Callable[[EventData], None]] = []
        self._subscriber_lock = threading.Lock()
        self._event_queue: queue.Queue = queue.Queue()
        self._running = threading.Event()
        self._processor_thread: Optional[threading.Thread] = None

    @classmethod
    def get(cls) -> 'EventEmitter':
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def subscribe(self, callback: Callable[[EventData], None]) -> None:
        with self._subscriber_lock:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[EventData], None]) -> None:
        with self._subscriber_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def emit(self, event_type: EventType, phase: Phase = None, **kwargs) -> None:
        data = EventData(event_type=event_type, phase=phase, **kwargs)
        self._event_queue.put(data)

    def _process_events(self) -> None:
        while self._running.is_set():
            try:
                event = self._event_queue.get(timeout=0.1)
                with self._subscriber_lock:
                    subscribers = list(self._subscribers)
                for subscriber in subscribers:
                    try:
                        subscriber(event)
                    except Exception:
                        logger.exception("Exception in event subscriber")
                self._event_queue.task_done()
            except queue.Empty:
                continue

    def start(self) -> None:
        self._running.set()
        self._processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self._processor_thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._processor_thread:
            self._processor_thread.join(timeout=1.0)

def get_emitter() -> EventEmitter:
    return EventEmitter.get()