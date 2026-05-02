from dataclasses import dataclass
from typing import Dict, List, Optional
from collections import defaultdict
from api_testing.events.types import OperationStatus

@dataclass
class OperationData:
    name: str
    method: str
    path: str
    generation: int
    status_codes: Dict[int, int]  # status_code -> count
    has_success: bool = False  # operation got at least one 2xx
    has_failure: bool = False  # operation got a non-success (non-2xx, non-0)

class ProgressTracker:
    def __init__(self):
        self._operations: Dict[str, OperationData] = {}
        self._generation_stats: Dict[int, dict] = defaultdict(lambda: {
            "completed": 0,  # operations with at least one 2xx
            "failed": 0,     # operations with no 2xx but has failure
            "total": 0      # unique operations
        })
        self._total_requests: int = 0

    def add_operation_result(self, name: str, method: str, path: str, generation: int, status_code: int):
        key = f"{generation}:{method}:{path}"
        is_new_operation = key not in self._operations
        self._total_requests += 1

        if is_new_operation:
            self._operations[key] = OperationData(
                name=name,
                method=method,
                path=path,
                generation=generation,
                status_codes=defaultdict(int)
            )
            self._generation_stats[generation]["total"] += 1

        op = self._operations[key]
        op.status_codes[status_code] += 1

        # Track at operation level whether we got success/failure
        if 200 <= status_code < 300:
            op.has_success = True
        elif status_code > 0:
            op.has_failure = True

        # Only count completed/failed ONCE per operation
        if is_new_operation:
            if status_code > 0 and 200 <= status_code < 300:
                self._generation_stats[generation]["completed"] += 1
            elif status_code > 0:  # any non-zero status that's not 2xx
                self._generation_stats[generation]["failed"] += 1

    def get_operations(self) -> List[OperationData]:
        return list(self._operations.values())

    def get_max_generation(self) -> int:
        return max(self._generation_stats.keys()) if self._generation_stats else 0

    def get_generation_stats(self, generation: int) -> dict:
        return self._generation_stats.get(generation, {"completed": 0, "failed": 0, "total": 0})

    def get_total_completed(self) -> int:
        return sum(s["completed"] for s in self._generation_stats.values())

    def get_total_failed(self) -> int:
        return sum(s["failed"] for s in self._generation_stats.values())

    def get_total_operations(self) -> int:
        return sum(s["total"] for s in self._generation_stats.values())

    def get_total_requests(self) -> int:
        return self._total_requests

    def reset(self):
        self._operations.clear()
        self._generation_stats.clear()
        self._total_requests = 0