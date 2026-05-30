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