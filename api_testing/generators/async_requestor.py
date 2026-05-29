import asyncio
import base64
from datetime import datetime
import json
import os
import re
import time
from typing import Any, Dict, Optional
import uuid

import httpx

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
    if isinstance(obj, (bytes, bytearray)):
        return "<BINARY>"
    if obj.__class__.__name__ == "BytesValue":
        return "<BINARY>"
    return str(obj)


def _get_header(headers: Dict[str, Any], name: str, default: str = "") -> str:
    """Return a header value using case-insensitive lookup."""
    if not headers:
        return default

    value = headers.get(name)
    if value is not None:
        return value

    wanted = name.lower()
    for key, value in headers.items():
        if str(key).lower() == wanted:
            return value

    return default


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
                    if clean_key not in current:
                        current[clean_key] = [{}]
                    current = current[clean_key][0]
                else:
                    if clean_key not in current:
                        current[clean_key] = {}
                    current = current[clean_key]

            current[parts[-1]] = value

        return nested
    return flat_dict


class AsyncResponseData:
    """Wrapper to create ResponseData from httpx.Response."""

    @classmethod
    def from_httpx(cls, response: Optional[httpx.Response]) -> "ResponseData":
        if response is None:
            return ResponseData(
                status_code=0,
                headers={},
                cookies={},
                mime_type="",
                body="",
                parsed=None,
                encoding=None,
            )

        content_type = response.headers.get("Content-Type", "")
        mime_type = content_type.split(";")[0].strip().lower()
        body = response.text if response.text is not None else response.content

        parsed = None
        if "application/json" in mime_type:
            try:
                parsed = response.json()
            except ValueError:
                parsed = body
        elif mime_type.startswith("text/") or mime_type in ("application/xml", "text/xml"):
            parsed = response.text

        cookies_dict = {}
        for name, value in response.cookies.items():
            cookies_dict[name] = value

        headers = dict(response.headers)
        if content_type and not _get_header(headers, "Content-Type"):
            headers["Content-Type"] = content_type

        return ResponseData(
            status_code=response.status_code,
            headers=headers,
            cookies=cookies_dict,
            mime_type=mime_type,
            body=body,
            parsed=parsed,
            encoding=response.encoding or "utf-8",
        )


class AsyncRequestor:
    """
    Async HTTP request executor using httpx.AsyncClient.

    Supports:
      - application/json
      - application/x-www-form-urlencoded
      - multipart/form-data
      - text/plain
      - application/xml / text/xml
      - application/octet-stream
    """

    def __init__(
        self,
        api_url: str,
        cache_dir: str = ".",
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        timeout_seconds: float = 300.0,
    ):
        self.api_url = api_url.rstrip("/")
        self.session_id = str(uuid.uuid4())
        self.entries: list[Dict[str, Any]] = []
        self._entries_lock = asyncio.Lock()
        self._dirty = False
        self._dirty_lock = asyncio.Lock()
        self.timeout_seconds = float(timeout_seconds)

        _cache_dir = os.path.join(cache_dir, "history")
        if not os.path.exists(_cache_dir):
            os.makedirs(_cache_dir)

        self.report = StatusCodeReport.make_shared(os.path.join(cache_dir, "reports.json"))
        self.cache_file = os.path.join(_cache_dir, self.session_id + ".har")
        self.logger = getLogger(__name__)

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds, connect=5.0),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections
            ),
            follow_redirects=True,
        )

    async def close(self):
        """Close the async client and all connections."""
        await self._client.aclose()

    def _prepare_payload(self, body: Any, mime_type: str) -> Dict[str, Any]:
        """Prepare request payload based on MIME type."""
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

        elif "application/octet-stream" in mime_type:
            if "__raw_binary__" in body:
                if body["__raw_binary__"] is not None and isinstance(body["__raw_binary__"], tuple) and len(body["__raw_binary__"]) == 3:
                    _, body, __ = body["__raw_binary__"]
                elif body["__raw_binary__"] is not None and isinstance(body["__raw_binary__"], str):
                    raw_data = body["__raw_binary__"]
                    try:
                        binary_content = base64.b64decode(raw_data)
                        binary_content = raw_data.encode('utf-8')
                    except Exception:
                        binary_content = b""
                    body = binary_content
                else:
                    return {"data": None}

            if hasattr(body, "read"):
                return {"data": body}
            if isinstance(body, (bytes, bytearray)):
                return {"data": body}
            if isinstance(body, str):
                try:
                    return {"data": open(body, "rb")}
                except Exception:
                    return {"data": body.encode()}
            return {"data": bytes(body)}

        elif "text/plain" in mime_type:
            return {"data": body if isinstance(body, (str, bytes)) else str(body)}

        elif "application/xml" in mime_type or "text/xml" in mime_type:
            return {"data": body if isinstance(body, str) else str(body)}

        return {"data": body}

    async def exec(self, request_data: "RequestData") -> "ResponseData":
        """
        Send an async HTTP request with MIME-type aware handling.

        Args:
            request_data: The prepared request data.

        Returns:
            ResponseData: Wrapped HTTP response.
        """
        parameters = (request_data.parameters or {}).copy()
        endpoint_path = request_data.endpoint_path

        path_param_names = re.findall(r"{([^}]+)}", endpoint_path)
        path_parameters = {}

        for key in path_param_names:
            path_parameters[key] = None
            if key in parameters:
                endpoint_path = endpoint_path.replace(f"{{{key}}}", str(parameters[key]))
                path_parameters[key] = parameters[key]
                parameters.pop(key, None)
            else:
                self.logger.warning(f"Missing path parameter '{key}' in parameters; keeping as placeholder.")

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
            "params": parameters,
        })

        start_time = time.perf_counter()

        try:
            response = await self._client.request(method=method, url=url, **request_kwargs)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response_data = AsyncResponseData.from_httpx(response)

            await self._record_har_entry(
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
                base_path=request_data.endpoint_path,
            )

            return response_data

        except httpx.TimeoutException:
            response_data = AsyncResponseData.from_httpx(None)
            duration_ms = (time.perf_counter() - start_time) * 1000
            await self._record_har_entry(
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
                base_path=request_data.endpoint_path,
            )
            self.logger.error("Request timed out after %s seconds", self.timeout_seconds)
            return response_data

        except httpx.RequestError as e:
            response_data = AsyncResponseData.from_httpx(None)
            duration_ms = (time.perf_counter() - start_time) * 1000
            await self._record_har_entry(
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
                base_path=request_data.endpoint_path,
            )
            self.logger.error(f"Request error: {e}")
            return response_data

    async def _record_har_entry(
        self,
        method: str,
        url: str,
        headers: Dict[str, Any],
        path_parameters: Dict[str, Any],
        params: Dict[str, Any],
        body: Any,
        response: ResponseData,
        duration_ms: float,
        expected_code: str,
        base_path: str,
        ruuid: str,
    ):
        """Record a request/response pair with a unique UUID."""
        entry_id = str(uuid.uuid4())

        query_string = [
            {"name": str(k), "value": str(v)} for k, v in (params or {}).items()
        ]

        mime_type = _get_header(response.headers, "Content-Type")
        normalized_mime_type = mime_type.lower()

        if "json" in normalized_mime_type or "text" in normalized_mime_type or mime_type == "":
            if not response.encoding:
                response.encoding = 'utf-8'
            response_body = response.body
        else:
            response_body = "<<binary data>>"

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
                    "text": json.dumps(body, default=to_placeholder) if body else "",
                },
                "path_params": path_parameters,
                "queryString": query_string,
            },
            "response": {
                "status": response.status_code,
                "statusText": body,
                "headers": [
                    {"name": k, "value": v} for k, v in response.headers.items()
                ],
                "content": {
                    "mimeType": mime_type,
                    "size": len(response.body) if response.body else 0,
                    "text": response_body,
                },
            },
        }

        self.report.add(ruuid, response.status_code)

        async with self._entries_lock:
            self.entries.append(entry)

        async with self._dirty_lock:
            self._dirty = True

    async def flush(self):
        """Persist aggregated report and HAR once after request batch completes."""
        async with self._dirty_lock:
            if not self._dirty:
                return

            self.report.save()

            await self._save_har()
            self._dirty = False

    async def _save_har(self):
        """Write all recorded HAR entries to disk."""
        entries_copy = self.entries.copy()

        data = {
            "log": {
                "version": "1.2",
                "creator": {"name": "AsyncExecutor", "version": "1.0"},
                "sessionId": self.session_id,
                "entries": entries_copy,
            }
        }

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_har_file,
            data
        )

    def _write_har_file(self, data: Dict[str, Any]):
        """Write HAR data to file (runs in thread pool)."""
        with open(self.cache_file, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, default=to_placeholder, separators=(",", ":"))


class AsyncRequestBatch:
    """
    Batch executor for running multiple async requests concurrently.
    """

    def __init__(self, async_requestor: AsyncRequestor, max_concurrent: int = 50):
        self.async_requestor = async_requestor
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute(self, requests: list) -> list:
        """
        Execute a list of requests concurrently with semaphore-based concurrency control.

        Args:
            requests: List of RequestData objects.

        Returns:
            List of ResponseData objects in the same order as input.
        """

        async def bounded_exec(request_data):
            async with self.semaphore:
                return await self.async_requestor.exec(request_data)

        tasks = [bounded_exec(req) for req in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for req, result in zip(requests, results):
            if isinstance(result, Exception):
                self.async_requestor.logger.error(
                    f"Request failed for {req.http_method} {req.endpoint_path}: {result}"
                )
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results
