from datetime import datetime
import json
import os
import re
import time
from typing import Any, Dict
import uuid
from pydantic import BaseModel
import requests

from api_testing.models.http_data import ResponseData
from api_testing.utils.log import getLogger


class Requestor:
    """
    Executes HTTP requests for various MIME types using RequestData.

    Supports:
      - application/json
      - application/x-www-form-urlencoded
      - multipart/form-data
      - text/plain
      - application/xml / text/xml
    """
    def __init__(self, api_url: str, cache_dir: str = None):
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        self.entries: list[Dict[str, Any]] = []
        _cache_dir = os.path.join(
            cache_dir, "history")
        if not os.path.exists(_cache_dir):
            print(f"History dir not found, I'll create dir {_cache_dir}")
            os.makedirs(_cache_dir)
        self.cache_file = os.path.join(
            _cache_dir, self.session_id + ".har")
        self.logger = getLogger(__name__)

    # ----------------------------------------------------------------------
    # Main execution method
    # ----------------------------------------------------------------------
    def exec(
        self,
        request_data: "RequestData",
    ) -> "ResponseData":
        """
        Send an HTTP request with MIME-type aware handling.

        Args:
            request_data (RequestData): The prepared request data.

        Returns:
            ResponseData: Wrapped HTTP response.
        """
        parameters = (request_data.parameters or {}).copy()  # shallow copy
        endpoint_path = request_data.endpoint_path

        # Tự động phát hiện các path param: /users/{id}/projects/{project_id}
        path_param_names = re.findall(r"{([^}]+)}", endpoint_path)

        for key in path_param_names:
            if key in parameters:
                # Thay {key} trong path bằng giá trị thực
                endpoint_path = endpoint_path.replace(f"{{{key}}}", str(parameters[key]))
                # Xoá key khỏi query params (đã dùng cho path)
                parameters.pop(key, None)
            else:
                self.logger.warning(f"⚠️ Missing path parameter '{key}' in parameters; keeping as placeholder.")

        url = f"{self.api_url}/{endpoint_path.lstrip('/')}"
        method = request_data.http_method.upper()
        headers = request_data.resolve_headers()
        cookies = request_data.resolve_cookies()
        mime_type = request_data.mime_type
        body = request_data.body
        request_kwargs = self._prepare_payload(body, mime_type)
        request_kwargs.update({
            "headers": headers, 
            "cookies": cookies,         
            "params":  parameters # ✅ Add query params here
        })
        start_time = time.perf_counter()

        response = requests.request(method=method, url=url, **request_kwargs)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response_data = ResponseData.from_requests(response)
        # Record to HAR
        self._record_har_entry(
            method, url, headers,parameters, body, response, duration_ms, expected_code=request_data.expected_code
        )

        return response_data
    
    # ----------------------------------------------------------------------
    # Internal helper for MIME-based payload preparation
    # ----------------------------------------------------------------------
    def _prepare_payload(self, body: Any, mime_type: str) -> Dict[str, Any]:
        """
        Prepare request payload based on MIME type.
        """
        if body is None:
            return {}

        if "application/json" in mime_type:
            return {"json": body}

        elif "application/x-www-form-urlencoded" in mime_type:
            if isinstance(body, dict):
                return {"data": body}
            return {"data": json.loads(body)}

        elif "multipart/form-data" in mime_type:
            return {"files": body if isinstance(body, dict) else None}

        elif "text/plain" in mime_type:
            return {"data": body if isinstance(body, (str, bytes)) else str(body)}

        elif "application/xml" in mime_type or "text/xml" in mime_type:
            return {"data": body if isinstance(body, str) else str(body)}

        # fallback: raw data
        return {"data": body}
    # ----------------------------------------------------------------------
    # HAR Recording
    # ----------------------------------------------------------------------
    def _record_har_entry(
        self,
        method: str,
        url: str,
        headers: Dict[str, Any],
        params: Dict[str, Any],
        body: Any,
        response: requests.Response,
        duration_ms: float,
        expected_code: str
    ):
        """Record a single request/response pair with a unique UUID."""
        entry_id = str(uuid.uuid4())
        # --- Build query parameter list ---
        query_string = [
            {"name": str(k), "value": str(v)} for k, v in (params or {}).items()
        ]

        entry = {
            "_id": entry_id,
            "startedDateTime": datetime.utcnow().isoformat() + "Z",
            "time": duration_ms,
            "expected_code": expected_code,
            "is_expected_status": str(response.status_code)[0] == expected_code[0],
            "request": {
                "method": method,
                "url": url,
                "headers": [{"name": k, "value": v} for k, v in headers.items()],
                "bodySize": len(json.dumps(body, default=str)) if body else 0,
                "postData": {
                    "text": json.dumps(body, default=str) if body else "",
                },
                "queryString": query_string,
            },
            "response": {
                "status": response.status_code,
                "statusText": response.reason,
                "headers": [
                    {"name": k, "value": v} for k, v in response.headers.items()
                ],
                "content": {
                    "mimeType": response.headers.get("Content-Type", ""),
                    "size": len(response.content),
                    "text": response.text,
                },
            },
        }
        self.entries.append(entry)
        self._save_har()
        
    def _save_har(self):
        """Write all recorded HAR entries to disk (append mode)."""
        data = {
            "log": {
                "version": "1.2",
                "creator": {"name": "Executor", "version": "1.0"},
                "sessionId": self.session_id,
                "entries": self.entries,
            }
        }
        with open(self.cache_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

