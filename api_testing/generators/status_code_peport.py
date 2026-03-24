import json
import os
from collections import defaultdict


class StatusCodeReport:
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

    def __init__(self, report_file: str):
        self.report_file = report_file
        self.data = defaultdict(lambda: defaultdict(int))
        self.load()

    # ---------------------------------------------------------
    # record response
    # ---------------------------------------------------------
    def add(self, endpoint: str, status_code: int):
        """
        Add a status code record for an endpoint.
        """
        endpoint = endpoint.strip("/")
        status_code = str(status_code)
        self.data[endpoint][status_code] += 1

    # ---------------------------------------------------------
    # export json
    # ---------------------------------------------------------
    def save(self):
        """
        Save report to json file.
        """
        os.makedirs(os.path.dirname(self.report_file), exist_ok=True)

        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
            f.flush()
    # ---------------------------------------------------------
    # load existing report (optional)
    # ---------------------------------------------------------
    def load(self):
        """
        Load existing report file if present.
        """
        if not os.path.exists(self.report_file):
            return

        with open(self.report_file, "r", encoding="utf-8") as f:
            raw = json.load(f)

        for endpoint, codes in raw.items():
            for code, count in codes.items():
                self.data[endpoint][code] = count