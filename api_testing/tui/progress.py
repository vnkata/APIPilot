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
        key = f"{generation}:{method}:{path}"
        self._operations[key] = OperationProgress(
            name=name,
            method=method,
            path=path,
            generation=generation
        )
        self._generation_stats[generation]["total"] += 1

    def update_operation(self, name: str, method: str, path: str, generation: int, status: OperationStatus,
                         status_code: Optional[int] = None, duration_ms: Optional[float] = None,
                         response_size: Optional[int] = None):
        key = f"{generation}:{method}:{path}"
        if key in self._operations:
            op = self._operations[key]
            if status == OperationStatus.SUCCESS and op.status != OperationStatus.SUCCESS:
                self._generation_stats[generation]["completed"] += 1
            elif status == OperationStatus.FAIL and op.status != OperationStatus.FAIL:
                self._generation_stats[generation]["failed"] += 1
            op.status = status
            op.status_code = status_code
            op.duration_ms = duration_ms
            op.response_size = response_size

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