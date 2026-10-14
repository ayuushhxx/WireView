"""
WireView HTTP - HTTP/1.1 Request Parser
Implements low-level RFC-compliant HTTP/1.1 request line parsing, header parsing,
security validation, and body framing.
"""

import posixpath
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple, Union

from .buffer import StreamBuffer
from .config import ServerConfig
from .errors import (
    BadRequest,
    HTTPVersionNotSupported,
    HeaderFieldsTooLarge,
    NotImplementedHTTP,
    PayloadTooLarge,
    URITooLong,
)
from .models import CaseInsensitiveDict, Request

# RFC 7230 token characters: 1*tchar
# tchar = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." / "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
TOKEN_REGEX = re.compile(r"^[!#$%&'*+\-.^_`|~0-9a-zA-Z]+$")

# Valid standard HTTP methods recognized by the engine
STANDARD_METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "TRACE", "CONNECT"}


class HTTPParser:
    """
    Parses HTTP/1.1 requests from a StreamBuffer.
    Enforces protocol limits and security constraints.
    """

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()

    def parse_request(
        self,
        stream: StreamBuffer,
        client_address: Tuple[str, int] = ("127.0.0.1", 0),
        request_id: str = "",
        connection_id: str = "",
    ) -> Request:
        """
        Parses a single HTTP request from the StreamBuffer.
        Returns a populated Request model.
        """
        # Step 1: Parse Request Line
        req_line_bytes = stream.read_line(
            max_length=self.config.max_request_line_length,
            is_request_line=True,
        )

        try:
            req_line_str = req_line_bytes.decode("ascii")
        except UnicodeDecodeError:
            raise BadRequest("Request line contains non-ASCII characters")

        # RFC 7230 Section 3.1.1: Request-Line = Method SP Request-Target SP HTTP-Version CRLF
        parts = req_line_str.split(" ")
        if len(parts) != 3:
            raise BadRequest(
                f"Malformed request line: expected 3 tokens (Method SP Target SP Version), got {len(parts)}"
            )

        method, target, version = parts

        # Validate HTTP Method token
        if not TOKEN_REGEX.match(method):
            raise BadRequest(f"Invalid characters in HTTP method: {method!r}")

        # Validate HTTP Version
        version_upper = version.upper()
        if not version_upper.startswith("HTTP/"):
            raise BadRequest(f"Invalid HTTP version string: {version!r}")

        if version_upper not in ("HTTP/1.1", "HTTP/1.0"):
            if version_upper in ("HTTP/2.0", "HTTP/2", "HTTP/3.0", "HTTP/3"):
                raise HTTPVersionNotSupported(f"Version {version} not supported. Use HTTP/1.1")
            raise BadRequest(f"Unrecognized HTTP version: {version}")

        # Parse and sanitize Target (Path & Query)
        parsed_target = urllib.parse.urlsplit(target)
        raw_path = parsed_target.path or "/"

        # Normalize URL path to prevent directory traversal
        # Replace multiple slashes and handle /../ or /./
        normalized_path = posixpath.normpath(urllib.parse.unquote(raw_path))
        if not normalized_path.startswith("/"):
            normalized_path = "/" + normalized_path

        # Parse query string
        query_params: Dict[str, Union[str, List[str]]] = {}
        if parsed_target.query:
            raw_query_dict = urllib.parse.parse_qs(parsed_target.query, keep_blank_values=True)
            for k, v in raw_query_dict.items():
                query_params[k] = v[0] if len(v) == 1 else v

        # Step 2: Parse Headers
        headers = CaseInsensitiveDict()
        header_count = 0
        total_header_bytes = 0
        raw_header_lines: List[bytes] = [req_line_bytes]

        while True:
            line_bytes = stream.read_line(
                max_length=self.config.max_header_size,
                is_request_line=False,
            )
            raw_header_lines.append(line_bytes)
            total_header_bytes += len(line_bytes) + 2  # account for CRLF

            if total_header_bytes > self.config.max_header_size:
                raise HeaderFieldsTooLarge(
                    f"Total header size {total_header_bytes} exceeds limit {self.config.max_header_size}"
                )

            # Empty line signifies end of header section
            if not line_bytes:
                break

            header_count += 1
            if header_count > self.config.max_header_count:
                raise HeaderFieldsTooLarge(
                    f"Header count {header_count} exceeds limit {self.config.max_header_count}"
                )

            try:
                line_str = line_bytes.decode("latin1")
            except UnicodeDecodeError:
                raise BadRequest("Invalid encoding in request headers")

            # Check RFC whitespace before colon rule (RFC 7230 3.2.4)
            colon_idx = line_str.find(":")
            if colon_idx == -1:
                raise BadRequest(f"Malformed header line: missing colon: {line_str!r}")

            header_name = line_str[:colon_idx]
            header_value = line_str[colon_idx + 1:].strip()

            # Whitespace before colon is forbidden
            if header_name.rstrip() != header_name:
                raise BadRequest(f"Whitespace preceding colon in header name: {header_name!r}")

            # Validate header name token
            if not TOKEN_REGEX.match(header_name):
                raise BadRequest(f"Invalid character in header name: {header_name!r}")

            # Reject control characters / NUL bytes in header value
            if any(ord(c) < 32 and c not in "\t" for c in header_value):
                raise BadRequest(f"Control characters detected in header {header_name!r}")

            # Combine duplicate headers if present (RFC 7230)
            existing_value = headers.get(header_name)
            if existing_value is not None:
                headers[header_name] = f"{existing_value}, {header_value}"
            else:
                headers[header_name] = header_value

        # Step 3: Validate Framing and Security
        # RFC 7230 3.3.3: Conflicting Transfer-Encoding and Content-Length is rejected
        has_transfer_encoding = "Transfer-Encoding" in headers
        has_content_length = "Content-Length" in headers

        if has_transfer_encoding and has_content_length:
            raise BadRequest("Conflicting framing: both Transfer-Encoding and Content-Length present")

        if has_transfer_encoding:
            te_val = headers["Transfer-Encoding"].strip().lower()
            raise NotImplementedHTTP(
                f"Transfer-Encoding '{te_val}' is not supported by this server implementation"
            )

        # Step 4: Parse Request Body
        body_bytes = b""
        if has_content_length:
            cl_raw = headers["Content-Length"].strip()
            # Handle multiple duplicate Content-Length headers that were combined
            if "," in cl_raw:
                parts = [p.strip() for p in cl_raw.split(",")]
                if any(p != parts[0] for p in parts):
                    raise BadRequest(f"Conflicting Content-Length values: {cl_raw}")
                cl_raw = parts[0]

            if not cl_raw.isdigit():
                raise BadRequest(f"Invalid Content-Length value: {cl_raw!r}")

            content_length = int(cl_raw)
            if content_length > self.config.max_body_size:
                raise PayloadTooLarge(
                    f"Content-Length {content_length} exceeds limit {self.config.max_body_size}"
                )

            if content_length > 0:
                body_bytes = stream.read_exact(
                    content_length,
                    max_limit=self.config.max_body_size,
                )

        return Request(
            method=method.upper(),
            target=target,
            path=normalized_path,
            version=version_upper,
            headers=headers,
            query_params=query_params,
            body=body_bytes,
            raw_header_bytes=b"\r\n".join(raw_header_lines),
            client_address=client_address,
            request_id=request_id,
            connection_id=connection_id,
        )
