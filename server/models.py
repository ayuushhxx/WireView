"""
WireView HTTP - Models
Structured data models for HTTP requests, responses, headers, and connections.
"""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Union


class CaseInsensitiveDict:
    """
    A dictionary for HTTP headers where keys are case-insensitive.
    Preserves original casing for serialization while supporting RFC lookup.
    """

    def __init__(self, data: Optional[Dict[str, str]] = None):
        self._data: Dict[str, Tuple[str, str]] = {}  # lower_key -> (original_key, value)
        if data:
            for k, v in data.items():
                self[k] = v

    def __setitem__(self, key: str, value: str):
        self._data[key.lower()] = (key, value)

    def __getitem__(self, key: str) -> str:
        return self._data[key.lower()][1]

    def __delitem__(self, key: str):
        del self._data[key.lower()]

    def __contains__(self, key: str) -> bool:
        return key.lower() in self._data

    def __len__(self) -> int:
        return len(self._data)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        val = self._data.get(key.lower())
        return val[1] if val else default

    def items(self):
        return [(orig_k, v) for orig_k, v in self._data.values()]

    def keys(self):
        return [orig_k for orig_k, _ in self._data.values()]

    def values(self):
        return [v for _, v in self._data.values()]

    def to_dict(self) -> Dict[str, str]:
        return {orig_k: v for orig_k, v in self._data.values()}

    def __repr__(self) -> str:
        return f"CaseInsensitiveDict({self.to_dict()})"


@dataclass
class Request:
    """Structured representation of an incoming HTTP/1.1 request."""
    method: str
    target: str
    path: str
    version: str
    headers: CaseInsensitiveDict
    query_params: Dict[str, Union[str, List[str]]] = field(default_factory=dict)
    path_params: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    raw_header_bytes: bytes = b""
    client_address: Tuple[str, int] = ("127.0.0.1", 0)
    request_id: str = ""
    connection_id: str = ""
    start_time: float = field(default_factory=time.perf_counter)
    stage_timings: Dict[str, float] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Decode body as UTF-8 string, with safe fallback."""
        try:
            return self.body.decode("utf-8")
        except UnicodeDecodeError:
            return self.body.decode("latin1", errors="replace")

    def json(self) -> Any:
        """Parse request body as JSON."""
        if not self.body:
            return None
        return json.loads(self.text)

    @property
    def is_keep_alive(self) -> bool:
        """Evaluate HTTP/1.1 keep-alive semantics."""
        conn_header = self.headers.get("Connection", "").strip().lower()
        if self.version.upper() == "HTTP/1.1":
            return conn_header != "close"
        elif self.version.upper() == "HTTP/1.0":
            return conn_header == "keep-alive"
        return False

    @property
    def content_length(self) -> int:
        cl = self.headers.get("Content-Length")
        if cl and cl.isdigit():
            return int(cl)
        return 0


@dataclass
class Response:
    """Structured representation of an HTTP response."""
    status_code: int = 200
    reason_phrase: str = "OK"
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    is_head_response: bool = False

    @classmethod
    def json(cls, data: Any, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> "Response":
        payload = json.dumps(data, indent=2).encode("utf-8")
        res_headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if headers:
            res_headers.update(headers)
        return cls(
            status_code=status_code,
            reason_phrase=get_standard_reason_phrase(status_code),
            headers=res_headers,
            body=payload
        )

    @classmethod
    def text(cls, text: str, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> "Response":
        payload = text.encode("utf-8")
        res_headers = {
            "Content-Type": "text/plain; charset=utf-8",
        }
        if headers:
            res_headers.update(headers)
        return cls(
            status_code=status_code,
            reason_phrase=get_standard_reason_phrase(status_code),
            headers=res_headers,
            body=payload
        )

    @classmethod
    def html(cls, html_content: str, status_code: int = 200, headers: Optional[Dict[str, str]] = None) -> "Response":
        payload = html_content.encode("utf-8")
        res_headers = {
            "Content-Type": "text/html; charset=utf-8",
        }
        if headers:
            res_headers.update(headers)
        return cls(
            status_code=status_code,
            reason_phrase=get_standard_reason_phrase(status_code),
            headers=res_headers,
            body=payload
        )

    @classmethod
    def no_content(cls, headers: Optional[Dict[str, str]] = None) -> "Response":
        return cls(
            status_code=204,
            reason_phrase="No Content",
            headers=headers or {},
            body=b""
        )

    @classmethod
    def error(cls, status_code: int, message: str, headers: Optional[Dict[str, str]] = None) -> "Response":
        err_dict = {
            "error": True,
            "status_code": status_code,
            "reason": get_standard_reason_phrase(status_code),
            "message": message,
            "timestamp": time.time()
        }
        payload = json.dumps(err_dict, indent=2).encode("utf-8")
        res_headers = {
            "Content-Type": "application/json; charset=utf-8",
        }
        if headers:
            res_headers.update(headers)
        return cls(
            status_code=status_code,
            reason_phrase=get_standard_reason_phrase(status_code),
            headers=res_headers,
            body=payload
        )


def get_standard_reason_phrase(status_code: int) -> str:
    phrases = {
        200: "OK",
        201: "Created",
        202: "Accepted",
        204: "No Content",
        301: "Moved Permanently",
        302: "Found",
        304: "Not Modified",
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        408: "Request Timeout",
        413: "Content Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
    }
    return phrases.get(status_code, "Unknown Status")


@dataclass
class ConnectionInfo:
    """Tracks state and statistics for an active or closed client connection."""
    connection_id: str
    client_ip: str
    client_port: int
    opened_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None
    requests_served: int = 0
    bytes_read: int = 0
    bytes_written: int = 0
    is_active: bool = True
