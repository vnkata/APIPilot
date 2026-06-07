import base64
from datetime import datetime
from enum import Enum
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, Optional, Union
import uuid

import requests

from api_testing.generators.status_code_peport import StatusCodeReport
from api_testing.models.http_data import RequestData, ResponseData
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
    
    if not isinstance(flat_dict, dict):
        return flat_dict
    
    nested: Dict[str, Any] = {}
    
    for path, value in flat_dict.items():
        parts = path.split(sep)
        current = nested
        
        for key in parts[:-1]:
            is_array = key.endswith(RequestConfig.ARRAY_SUFFIX)
            clean_key = key[:-len(RequestConfig.ARRAY_SUFFIX)] if is_array else key
            
            if is_array:
                if clean_key not in current:
                    current[clean_key] = [{}]
                current = current[clean_key][0]
            else:
                if clean_key not in current:
                    current[clean_key] = {}
                current = current[clean_key]
        
        current[parts[-1]] = value
    
    return nested


# ==================== Payload Builder ====================

class PayloadBuilder:
    """Handles preparing request payloads based on MIME type."""
    
    @staticmethod
    def build(body: Any, mime_type: str) -> Dict[str, Any]:
        """Prepare request payload based on MIME type."""
        if body is None or body == {}:
            return {}
        
        if isinstance(body, dict) and "__body__" in body:
            body = body.get("__body__")
        
        mime_handlers = {
            MimeType.JSON: PayloadBuilder._handle_json,
            MimeType.JSON_LD: PayloadBuilder._handle_json_ld,
            MimeType.GRAPHQL: PayloadBuilder._handle_graphql,
            MimeType.FORM_DATA: PayloadBuilder._handle_form_data,
            MimeType.FORM_URLENCODED: PayloadBuilder._handle_form_urlencoded,
            MimeType.OCTET_STREAM: PayloadBuilder._handle_octet_stream,
            MimeType.TEXT_PLAIN: PayloadBuilder._handle_text_plain,
            MimeType.PDF: PayloadBuilder._handle_binary,
            MimeType.PROTOBUF: PayloadBuilder._handle_binary,
            MimeType.IMAGE_JPEG: PayloadBuilder._handle_binary,
            MimeType.IMAGE_PNG: PayloadBuilder._handle_binary,
            MimeType.IMAGE_SVG: PayloadBuilder._handle_text,
            MimeType.VIDEO_MP4: PayloadBuilder._handle_binary,
            MimeType.AUDIO_MPEG: PayloadBuilder._handle_binary,
        }
        
        for mime_key, handler in mime_handlers.items():
            if mime_key in mime_type:
                return handler(body)
        
        if "xml" in mime_type:
            return {"data": body if isinstance(body, str) else str(body)}
        
        if "image" in mime_type or "video" in mime_type or "audio" in mime_type:
            return PayloadBuilder._handle_binary(body)
        
        return {"data": body}
    
    @staticmethod
    def _handle_json(body: Any) -> Dict[str, Any]:
        """Handle application/json payload."""
        return {"json": unflatten_dict(body)}
    
    @staticmethod
    def _handle_json_ld(body: Any) -> Dict[str, Any]:
        """Handle application/ld+json (JSON-LD) payload."""
        if isinstance(body, str):
            return {"data": body}
        return {"json": body}
    
    @staticmethod
    def _handle_graphql(body: Any) -> Dict[str, Any]:
        """Handle application/graphql payload."""
        if isinstance(body, dict):
            return {"data": json.dumps(body)}
        return {"data": body if isinstance(body, str) else str(body)}
    
    @staticmethod
    def _handle_form_data(body: Any) -> Dict[str, Any]:
        """Handle multipart/form-data payload."""
        return PayloadBuilder._handle_form(body)
    
    @staticmethod
    def _handle_form_urlencoded(body: Any) -> Dict[str, Any]:
        """Handle application/x-www-form-urlencoded payload."""
        return PayloadBuilder._handle_form(body)
    
    @staticmethod
    def _handle_form(body: Any) -> Dict[str, Any]:
        """Common handler for form payloads."""
        if not isinstance(body, dict):
            return {}
        
        data = {}
        files = {}
        
        for k, v in body.items():
            if isinstance(v, tuple) and len(v) == 3:
                _, file_content, _ = v
                files[k] = file_content
            elif isinstance(v, tuple):
                files[k] = v
            elif hasattr(v, "read"):
                files[k] = v
            else:
                data[k] = v
        
        result = {}
        if data:
            result["data"] = unflatten_dict(data)
        if files:
            result["files"] = files
        
        return result
    
    @staticmethod
    def _handle_octet_stream(body: Any) -> Dict[str, Any]:
        """Handle application/octet-stream payload."""
        return PayloadBuilder._handle_binary(body)
    
    @staticmethod
    def _extract_binary_content(raw_binary: Any) -> bytes:
        """Extract binary content from various formats."""
        if raw_binary is None:
            return b""
        
        if isinstance(raw_binary, tuple) and len(raw_binary) == 3:
            _, content, _ = raw_binary
            return content if isinstance(content, bytes) else str(content).encode()
        
        if isinstance(raw_binary, str):
            try:
                return base64.b64decode(raw_binary)
            except Exception:
                return raw_binary.encode('utf-8')
        
        if isinstance(raw_binary, (bytes, bytearray)):
            return bytes(raw_binary)
        
        return b""
    
    @staticmethod
    def _handle_text_plain(body: Any) -> Dict[str, Any]:
        """Handle text/plain payload."""
        return {"data": body if isinstance(body, (str, bytes)) else str(body)}
    
    @staticmethod
    def _handle_text(body: Any) -> Dict[str, Any]:
        """Handle text-based payloads (SVG, etc.)."""
        return {"data": body if isinstance(body, str) else str(body)}
    
    @staticmethod
    def _handle_binary(body: Any) -> Dict[str, Any]:
        """Handle binary payloads (PDF, images, video, audio, etc.)."""
        if isinstance(body, dict) and "__raw_binary__" in body:
            body = PayloadBuilder._extract_binary_content(body["__raw_binary__"])
        
        if hasattr(body, "read"):
            return {"data": body}
        
        if isinstance(body, (bytes, bytearray)):
            return {"data": body}
        
        if isinstance(body, str):
            try:
                return {"data": open(body, "rb")}
            except Exception:
                try:
                    return {"data": base64.b64decode(body)}
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
         
        post_data_text = HAREntryBuilder._extract_post_data(request_kwargs)
        response_body = HAREntryBuilder._extract_response_body(response)
        
        return {
            "_id": str(uuid.uuid4()),
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
    
    @staticmethod
    def _extract_post_data(request_kwargs: Dict[str, Any]) -> str:
        """Extract and serialize POST data from request kwargs."""
        if "json" in request_kwargs:
            return json.dumps(request_kwargs["json"], default=to_placeholder)
        elif "data" in request_kwargs:
            data = request_kwargs["data"]
            if isinstance(data, dict):
                return json.dumps(data, default=to_placeholder)
            return str(data)
        elif "files" in request_kwargs:
            files_repr = {k: repr(v) for k, v in request_kwargs["files"].items()}
            return json.dumps(files_repr, default=to_placeholder)
        
        return ""
    
    @staticmethod
    def _extract_response_body(response: ResponseData) -> str:
        """Extract response body, handling text vs binary content."""
        mime_type = response.headers.get("Content-Type", "")
        
        if ("json" in mime_type or "text" in mime_type or mime_type == ""):
            if not response.encoding:
                response.encoding = 'utf-8'
            return response.body
        
        return "<<binary data>>"


# ==================== HAR File Manager ====================

class HARFileManager:
    """Manages HAR file storage and serialization."""
    
    VERSION = "1.2"
    CREATOR_NAME = "APITester"
    CREATOR_VERSION = "1.0"
    
    def __init__(self, cache_file: Path):
        """Initialize with HAR cache file path."""
        self.cache_file = cache_file
    
    def save_entries(self, entries: list[Dict[str, Any]], session_id: str) -> None:
        """Save HAR entries to file."""
        har_data = {
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
        
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(har_data, f, indent=2, ensure_ascii=False, default=to_placeholder)

class TestCaseManager:
    """Manages test case results and integration with HAR entries.
    """
    def __init__(self, cache_file: str):
        """Initialize with status code report instance."""
        self.cache_file = cache_file
        self.file_handle = open(self.cache_file, "a", encoding="utf-8", buffering=1)
        
    def save(self, request_data: "RequestData") -> None:
        line = json.dumps(request_data.to_dict(), ensure_ascii=False)
        self.file_handle.write(line + "\n")

    def close(self):
        if hasattr(self, 'file_handle') and not self.file_handle.closed:
            self.file_handle.close()
            
    def __del__(self):
        self.close()
class Requestor:
    """
    Executes HTTP requests with comprehensive HAR logging and status tracking.
    
    Supports MIME types:
      - application/json
      - application/x-www-form-urlencoded
      - multipart/form-data
      - text/plain
      - application/xml / text/xml
      - application/octet-stream
      
    Attributes:
        api_url: Base API URL
        session_id: Unique session identifier
        entries: List of recorded HAR entries
    """
    
    def __init__(self, api_url: str, cache_dir: str = "."):
        """
        Initialize Requestor instance.
        
        Args:
            api_url: Base URL for the API
            cache_dir: Directory for caching HAR and report files
        """
        self.api_url = api_url
        self.session_id = str(uuid.uuid4())
        self.entries: list[Dict[str, Any]] = []
        self.logger = getLogger(__name__)
        
        # Initialize cache directory structure
        self._cache_dir = self._initialize_cache_dir(cache_dir)
        
        # Initialize components
        self._url_builder = URLBuilder(api_url)
        self._payload_builder = PayloadBuilder()
        self._har_manager = HARFileManager(self._cache_dir / f"{self.session_id}.har")
        self._test_case_manager = TestCaseManager(self._cache_dir / "testcases.jsonl")
        self._report = StatusCodeReport(
            report_file=str(self._cache_dir.parent / RequestConfig.REPORTS_FILE)
        )
    
    def _initialize_cache_dir(self, cache_dir: str) -> Path:
        """Initialize and create cache directory structure."""
        cache_path = Path(cache_dir) / RequestConfig.CACHE_SUBDIR
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path
    
    def exec(self, request_data: "RequestData") -> Optional[ResponseData]:
        """
        Execute HTTP request with full error handling and HAR recording.
        
        Args:
            request_data: Prepared request data object
            
        Returns:
            ResponseData object or None on failure
        """
        try:
            # Build URL and extract parameters
            url, path_params, query_params = self._url_builder.build(
                request_data.endpoint_path,
                request_data.parameters
            )
            
            # Prepare request
            method = request_data.http_method.upper()
            headers = request_data.resolve_headers()
            cookies = request_data.resolve_cookies()
            request_kwargs = self._payload_builder.build(
                request_data.body,
                request_data.mime_type
            )
            request_kwargs.update({
                "headers": headers,
                "cookies": cookies,
                "params": query_params,
            })
            
            # Execute request
            duration_ms, response_data = self._execute_request(method, url, request_kwargs)
            # Record to HAR
            self._record_har_entry(
                ruuid=request_data.uuid,
                method=method,
                url=url,
                base_path=request_data.endpoint_path,
                path_parameters=path_params,
                request_kwargs=request_kwargs,
                response=response_data,
                duration_ms=duration_ms,
                expected_code=request_data.expected_code,
                request_data=request_data
            )
            
            return response_data
        
        except requests.exceptions.Timeout:
            self.logger.error(
                f"Request timeout after {RequestConfig.DEFAULT_TIMEOUT_READ}s"
            )
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            self.logger.exception(f"Unexpected error during request: {e}")
            return None
    
    def _execute_request(
        self,
        method: str,
        url: str,
        request_kwargs: Dict[str, Any]
    ) -> tuple[float, ResponseData]:
        """Execute HTTP request and measure duration."""
        start_time = time.perf_counter()
        
        response = requests.request(
            method=method,
            url=url,
            timeout=RequestConfig.TIMEOUT,
            **request_kwargs
        )
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        response_data = ResponseData.from_requests(response)
        
        return duration_ms, response_data
    
    def _record_har_entry(
        self,
        ruuid: str,
        method: str,
        url: str,
        base_path: str,
        path_parameters: Dict[str, Any],
        request_kwargs: Dict[str, Any],
        response: ResponseData,
        duration_ms: float,
        expected_code: str,
        request_data: "RequestData"
    ) -> None:
        """Record request/response as HAR entry and update status report."""
        entry = HAREntryBuilder.build(
            ruuid=ruuid,
            method=method,
            url=url,
            base_path=base_path,
            path_parameters=path_parameters,
            request_kwargs=request_kwargs,
            response=response,
            duration_ms=duration_ms,
            expected_code=expected_code,
        )
        
        self.entries.append(entry)
        
        # Update status report
        self._report.add(ruuid, response.status_code)
        self._report.save()
        
        # Save HAR
        self._har_manager.save_entries(self.entries, self.session_id)
        # save testcase result
        if entry.get("is_expected_status"): # only save test case if it matches expected status
            self._test_case_manager.save(request_data)
