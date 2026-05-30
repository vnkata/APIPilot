import base64
from datetime import datetime
from enum import Enum
import json
import logging
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Dict, Optional, Union
import uuid

import requests

from api_testing.generators.status_code_peport import StatusCodeReport
from api_testing.models.http_data import ResponseData
from api_testing.utils.log import getLogger


# ==================== Constants & Enums ====================

class MimeType(str, Enum):
    """Supported MIME types for HTTP requests."""
    JSON = "application/json"
    JSON_LD = "application/ld+json"
    FORM_DATA = "multipart/form-data"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    OCTET_STREAM = "application/octet-stream"
    TEXT_PLAIN = "text/plain"
    XML = "application/xml"
    TEXT_XML = "text/xml"
    GRAPHQL = "application/graphql"
    PDF = "application/pdf"
    PROTOBUF = "application/x-protobuf"
    IMAGE_JPEG = "image/jpeg"
    IMAGE_PNG = "image/png"
    IMAGE_SVG = "image/svg+xml"
    VIDEO_MP4 = "video/mp4"
    AUDIO_MPEG = "audio/mpeg"


class RequestConfig:
    """Configuration constants for request execution."""
    
    DEFAULT_TIMEOUT_CONNECT: float = 5.0
    DEFAULT_TIMEOUT_READ: float = 300.0
    TIMEOUT: tuple[float, float] = (DEFAULT_TIMEOUT_CONNECT, DEFAULT_TIMEOUT_READ)
    
    PATH_PARAM_PATTERN: str = r"{([^}]+)}"
    DEFAULT_SEPARATOR: str = "."
    ARRAY_SUFFIX: str = "[]"
    
    CACHE_SUBDIR: str = "history"
    HISTORY_EXTENSION: str = ".har"
    REPORTS_FILE: str = "reports.json"


# ==================== Helper Functions ====================

def to_placeholder(obj: Any) -> Union[str, Dict[str, Any]]:
    """Convert objects to placeholder representations for serialization."""
    if isinstance(obj, tuple) and len(obj) == 3:
        filename, content, content_type = obj
        return {
            "filename": filename,
            "content": "<BINARY>",
            "content_type": content_type
        }
    
    if isinstance(obj, (bytes, bytearray)):
        return "<BINARY>"
    
    if obj.__class__.__name__ == "BytesValue":
        return "<BINARY>"
    
    return str(obj)


def unflatten_dict(
    flat_dict: Union[Dict[str, Any], list],
    sep: str = RequestConfig.DEFAULT_SEPARATOR
) -> Union[Dict[str, Any], list]:
    """
    Convert flat dot-notation dictionary to nested dictionary.
    
    Example:
        >>> unflatten_dict({"user.name": "John", "user.age": 30})
        {"user": {"name": "John", "age": 30}}
    """
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

    Thread-local storage optimization:
      - Uses thread-local entries to reduce lock contention
      - Report updates still use lock (rare operation)
      - Entries use thread-local storage with merge at flush
    """
    def __init__(self, api_url: str, cache_dir: str = "."):
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        self.entries: list[Dict[str, Any]] = []
        self._entries_lock = threading.Lock()
        self._report_lock = threading.Lock()
        self._dirty = False
        self._local = threading.local()
        _cache_dir = os.path.join(
            cache_dir, "history")
        if not os.path.exists(_cache_dir):
            os.makedirs(_cache_dir)
        self.report = StatusCodeReport.make_shared(os.path.join(
            cache_dir, "reports.json"))
        self.cache_file = os.path.join(
            _cache_dir, self.session_id + ".har")
        self.logger = getLogger(__name__)

    def _get_local_entries(self) -> list:
        """Get thread-local entries list, creating if needed."""
        if not hasattr(self._local, 'entries'):
            self._local.entries = []
        return self._local.entries

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
            self.logger.debug(f"Parameters: {parameters}")
            self._record_har_entry(
                ruuid=request_data.uuid, method=method, url=url, headers=headers, path_parameters=path_parameters, 
                params=parameters, body=body, response=response_data,
                duration_ms=duration_ms, expected_code=request_data.expected_code,
                base_path=base_path
            )
            return response_data
        except requests.exceptions.Timeout:
            response_data = ResponseData.from_requests(None)
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Record to HAR
            self._record_har_entry(
                ruuid=request_data.uuid, method=method, url=url, headers=headers, path_parameters=path_parameters, 
                params=parameters, body=body, response=response_data, duration_ms=duration_ms, expected_code=request_data.expected_code, base_path=base_path
            )
            self.logger.error("Lỗi: Request đã quá thời gian chờ 5 phút!")
            return response_data
        except requests.exceptions.RequestException as e:
            response_data = ResponseData.from_requests(None)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._record_har_entry(
                ruuid=request_data.uuid,
                method=method,
                url=url,
                headers=headers,
                path_parameters=path_parameters,
                params=parameters,
                body=body,
                response=response_data,
                duration_ms=duration_ms,
                expected_code=request_data.expected_code,
                base_path=base_path,
            )
            self.logger.error(f"System error: {e}")
            return response_data
        
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
        
        return {"data": bytes(body) if not isinstance(body, bytes) else body}


# ==================== URL Builder ====================

class URLBuilder:
    """Handles URL construction and path parameter resolution."""
    
    def __init__(self, api_url: str):
        """Initialize with base API URL."""
        self.api_url = api_url.rstrip("/")
        self.logger = getLogger(__name__)
    
    def build(
        self, endpoint_path: str, parameters: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Dict[str, Any], Dict[str, Any]]:
        """
        Build full URL, extract path parameters, and remaining query parameters.
        
        Returns:
            Tuple of (full_url, path_parameters, remaining_parameters)
        """
        parameters = (parameters or {}).copy()
        path_param_names = re.findall(RequestConfig.PATH_PARAM_PATTERN, endpoint_path)
        path_parameters = {}
        
        resolved_path = endpoint_path
        for param_name in path_param_names:
            if param_name in parameters:
                value = parameters.pop(param_name)
                path_parameters[param_name] = value
                resolved_path = resolved_path.replace(f"{{{param_name}}}", str(value))
            else:
                path_parameters[param_name] = None
                self.logger.warning(
                    f"⚠️ Missing path parameter '{param_name}'; keeping as placeholder"
                )
        
        full_url = f"{self.api_url}/{resolved_path.lstrip('/')}"
        return full_url, path_parameters, parameters


# ==================== HAR Entry Builder ====================

class HAREntryBuilder:
    """Constructs HAR (HTTP Archive) format entries."""
    
    @staticmethod
    def build(
        ruuid: str,
        method: str,
        url: str,
        base_path: str,
        path_parameters: Dict[str, Any],
        request_kwargs: Dict[str, Any],
        response: ResponseData,
        duration_ms: float,
        expected_code: str,
    ) -> Dict[str, Any]:
        """Build a HAR entry from request/response data."""
        prepared_headers = request_kwargs.get("headers", {}) or {}
        params = request_kwargs.get("params", {}) or {}
        
        query_string = [
            {"name": str(k), "value": v} for k, v in params.items()
        ]
        mime_type = response.headers.get("Content-Type", "")

        # Only attempt to record text if it's actually text/json
        if "json" in mime_type or "text" in mime_type or mime_type == "":
            # Force utf-8 if requests is unsure to avoid chardet
            if not response.encoding:
                response.encoding = 'utf-8'
            response_body = response.body
        else:
            # For binary files, maybe just store a placeholder or base64
            response_body = "<<binary data>>"
        entry = {
            "_id": entry_id,
            "startedDateTime": datetime.utcnow().isoformat() + "Z",
            "time": duration_ms,
            "expected_code": expected_code,
            "is_expected_status": str(response.status_code)[0] == expected_code[0],
            "request": {
                "_uuid": ruuid,
                "path_template": base_path,
                "method": method,
                "url": url,
                "headers": [
                    {"name": k, "value": v} for k, v in prepared_headers.items()
                ],
                "bodySize": len(post_data_text),
                "postData": {"text": post_data_text},
                "path_params": path_parameters,
                "queryString": query_string,
            },
            "response": {
                "status": response.status_code,
                "statusText": getattr(response, "reason", ""),
                "headers": [
                    {"name": k, "value": v} for k, v in response.headers.items()
                ],
                "content": {
                    "mimeType": response.headers.get("Content-Type", ""),
                    "size": len(response.body),
                    "text": response_body,
                },
            },
        }

        # Keep critical section minimal: report uses lock
        with self._report_lock:
            self.report.add(ruuid, response.status_code)

        with self._entries_lock:
            self.entries.append(entry)
            self._dirty = True

    def flush(self):
        """Persist aggregated report and HAR once after request batch completes."""
        with self._entries_lock:
            if not self._dirty:
                self.logger.debug("flush: nothing dirty, skipping")
                return
            self.logger.debug(f"flush: {len(self.entries)} total entries to save")
        with self._report_lock:
            self.report.save()
        self._save_har()
        with self._entries_lock:
            self._dirty = False
        
    def _save_har(self):
        """Write all recorded HAR entries to disk (append mode)."""
        data = {
            "log": {
                "version": self.VERSION,
                "creator": {
                    "name": self.CREATOR_NAME,
                    "version": self.CREATOR_VERSION
                },
                "sessionId": session_id,
                "entries": entries,
            }
        }
        with open(self.cache_file, "w", encoding="utf-8") as file:
            # Compact JSON reduces write volume and serialization overhead on large runs.
            json.dump(data, file, ensure_ascii=False, default=to_placeholder, separators=(",", ":"))
