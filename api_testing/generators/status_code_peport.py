import json
import os
import threading
from collections import defaultdict

"""
    Collect and export status code statistics per endpoint.

    Example output:
    {
      "get-projects/": {
        "404": 6078,
        "400": 1369,
        "200": 361
      }
    }
"""
class StatusCodeReport:
    _save_lock = threading.Lock()
    _instance = None

    def __init__(self, report_file: str, _global=False):
        self.report_file = report_file
        self.data = defaultdict(lambda: defaultdict(int))
        if _global and os.path.exists(report_file):
            self.load()

    @staticmethod
    def make_shared(report_file: str) -> 'StatusCodeReport':
        if StatusCodeReport._instance is None:
            StatusCodeReport._instance = StatusCodeReport(report_file, _global=True)
        return StatusCodeReport._instance

    def add(self, endpoint: str, status_code: int):
        endpoint = endpoint.strip("/")
        status_code = str(status_code)
        self.data[endpoint][status_code] += 1

    def save(self):
        os.makedirs(os.path.dirname(self.report_file), exist_ok=True)
        with StatusCodeReport._save_lock:
            if os.path.exists(self.report_file):
                with open(self.report_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                for ep, codes in existing.items():
                    for code, count in codes.items():
                        self.data[ep][code] = count
            with open(self.report_file, "w", encoding="utf-8") as f:
                json.dump(dict(self.data), f, indent=2, ensure_ascii=False)
                f.flush()

    def load(self):
        if not os.path.exists(self.report_file):
            return
        with open(self.report_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for endpoint, codes in raw.items():
            for code, count in codes.items():
                self.data[endpoint][code] = count