import base64
from datetime import datetime
import json
import os
import re
import time
from typing import Any, Dict
import uuid
from pydantic import BaseModel
import requests

from api_testing.generators.status_code_peport import StatusCodeReport
from api_testing.models.http_data import ResponseData
from api_testing.utils.log import getLogger

def to_placeholder(obj):
    if isinstance(obj, tuple) and len(obj) == 3:
        filename, content, content_type = obj
        return {
            "filename": filename,
            "content": "<BINARY>",
            "content_type": content_type
        }
    # bytes
    if isinstance(obj, (bytes, bytearray)):
        return "<BINARY>"

    # custom object (BytesValue)
    if obj.__class__.__name__ == "BytesValue":
        return "<BINARY>"

    # fallback
    return str(obj)


def unflatten_dict(flat_dict: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
    nested: Dict[str, Any] = {}
    if isinstance(flat_dict, list):
        return [unflatten_dict(item, sep) for item in flat_dict]
    
    if isinstance(flat_dict, dict):
        for path, value in flat_dict.items():
            parts = path.split(sep)
            current = nested

            for i in range(len(parts) - 1):
                key = parts[i]
                is_array = key.endswith("[]")
                clean_key = key[:-2] if is_array else key

                if is_array:
                    # If key doesn't exist, create an empty list
                    if clean_key not in current:
                        current[clean_key] = [{}]
                    
                    # Move into the first element of the list
                    current = current[clean_key][0]
                else:
                    # Standard dictionary navigation
                    if clean_key not in current:
                        current[clean_key] = {}
                    current = current[clean_key]

            # Assign the leaf value
            current[parts[-1]] = value

        return nested
    return flat_dict


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
    def __init__(self, api_url: str, cache_dir: str = "."):
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        self.entries: list[Dict[str, Any]] = []
        _cache_dir = os.path.join(
            cache_dir, "history")
        if not os.path.exists(_cache_dir):
            print(f"History dir not found, I'll create dir {_cache_dir}")
            os.makedirs(_cache_dir)
        self.report = StatusCodeReport(report_file=os.path.join(
            cache_dir, "reports.json"))
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
        base_path = request_data.endpoint_path
        
        path_param_names = re.findall(r"{([^}]+)}", endpoint_path)
        path_parameters = {}
        for key in path_param_names:
            path_parameters[key] = None
            if key in parameters:
                # Thay {key} trong path bằng giá trị thực
                endpoint_path = endpoint_path.replace(f"{{{key}}}", str(parameters[key]))
                path_parameters[key] = parameters[key]
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
        try:
            response = requests.request(method=method, url=url, **request_kwargs, timeout=(5, 300))
            duration_ms = (time.perf_counter() - start_time) * 1000
            response_data = ResponseData.from_requests(response)
            # Record to HAR
            self._record_har_entry(
                method, url, headers, path_parameters, parameters, body, response, duration_ms, expected_code=request_data.expected_code, base_path=base_path
            )
            return response_data
        except requests.exceptions.Timeout:
            response_data = ResponseData.from_requests(None)
            # Record to HAR
            self._record_har_entry(
                method, url, headers, path_parameters, parameters, body, response, duration_ms, expected_code=request_data.expected_code, base_path=base_path
            )
            print("Lỗi: Request đã quá thời gian chờ 5 phút!")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi hệ thống: {e}")
        
    # ----------------------------------------------------------------------
    # Internal helper for MIME-based payload preparation
    # ----------------------------------------------------------------------
    
    def _prepare_payload(self, body: Any, mime_type: str) -> Dict[str, Any]:
        """
        Prepare request payload based on MIME type.
        """
        if body is None or body == {}:
            return {}
        if "__body__" in body:
            body = body.get("__body__") 
            
        if "application/json" in mime_type:
            return {"json": unflatten_dict(body)}

        elif "multipart/form-data" in mime_type or "application/x-www-form-urlencoded" in mime_type:
            if not isinstance(body, dict):
                return {}

            data = {}
            files = {}

            for k, v in body.items():
                if isinstance(v, tuple):
                    # (filename, fileobj, content_type)
                    files[k] = v
                elif hasattr(v, "read"):
                    # file-like object
                    files[k] = v
                else:
                    data[k] = v

            result = {}
            if data:
                result["data"] = unflatten_dict(data)
            if files:
                result["files"] = files
            return result
        elif "application/octet-stream" in mime_type:
            if "__raw_binary__" in body:
                if body["__raw_binary__"] is not None and isinstance(body["__raw_binary__"], tuple) and len(body["__raw_binary__"]) == 3:
                    _, body, __  = body["__raw_binary__"]
                elif body["__raw_binary__"] is not None and isinstance(body["__raw_binary__"],str):
                    raw_data = body["__raw_binary__"]
                    try:
                        # If it's Base64 encoded:
                        binary_content = base64.b64decode(raw_data)
    
                        # Or if it's just a UTF-8 string you need as bytes:
                        binary_content = raw_data.encode('utf-8')
                        
                    except Exception as e:
                        print(f"Conversion failed: {e}")
                        binary_content = b""
                    body = binary_content
                else:
                    return {"data": None}
            # case 1: file-like object
            if hasattr(body, "read"):
                return {"data": body}

            # case 2: raw bytes
            if isinstance(body, (bytes, bytearray)):
                return {"data": body}

            # case 3: filepath
            if isinstance(body, str):
                try:
                    return {"data": open(body, "rb")}
                except Exception:
                    return {"data": body.encode()}

            # fallback
            return {"data": bytes(body)}


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
        path_parameters:  Dict[str, Any],
        params: Dict[str, Any],
        body: Any,
        response: requests.Response,
        duration_ms: float,
        expected_code: str,
        base_path: str
    ):
        """Record a single request/response pair with a unique UUID."""
        entry_id = str(uuid.uuid4())
        # --- Build query parameter list ---
        query_string = [
            {"name": str(k), "value": str(v)} for k, v in (params or {}).items()
        ]
        mime_type = response.headers.get("Content-Type", "")

        # Only attempt to record text if it's actually text/json
        if "json" in mime_type or "text" in mime_type or mime_type == "":
            # Force utf-8 if requests is unsure to avoid chardet
            if not response.encoding:
                response.encoding = 'utf-8'
            response_body = response.text
        else:
            # For binary files, maybe just store a placeholder or base64
            response_body = "<<binary data>>"
        self.report.add(f"{method.lower()}-{base_path}", response.status_code)
        self.report.save()
        
        entry = {
            "_id": entry_id,
            "startedDateTime": datetime.utcnow().isoformat() + "Z",
            "time": duration_ms,
            "expected_code": expected_code,
            "is_expected_status": str(response.status_code)[0] == expected_code[0],
            "request": {
                "path_template": base_path,
                "method": method,
                "url": url,
                "headers": [{"name": k, "value": v} for k, v in headers.items()],
                "bodySize": len(json.dumps(body, default=str)) if body else 0,
                "postData": {
                    "text": json.dumps(body,  default=to_placeholder ) if body else "",
                },
                "path_params": path_parameters,
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
                    "text": response_body,
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

