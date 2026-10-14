"""
WireView HTTP - Response Serializer
Constructs and serializes RFC-compliant HTTP/1.1 response frames.
Handles CRLF injection prevention, byte-accurate Content-Length calculations,
bodyless responses (HEAD, 204, 304), and robust socket writes.
"""

from email.utils import formatdate
import socket
import time
from typing import Optional, Tuple
from .config import ServerConfig
from .errors import InternalServerError
from .models import Response, get_standard_reason_phrase


class ResponseSerializer:
    """
    Serializes Response dataclass instances into raw byte streams
    and sends them completely over a TCP socket.
    """

    def __init__(self, config: Optional[ServerConfig] = None):
        self.config = config or ServerConfig()

    def serialize_headers_and_body(
        self,
        response: Response,
        keep_alive: bool = False,
        is_head_request: bool = False,
    ) -> Tuple[bytes, bytes]:
        """
        Builds status line and headers bytes, plus the body bytes to be transmitted.
        Returns (header_bytes, body_bytes_to_send).
        """
        status_line = f"HTTP/1.1 {response.status_code} {response.reason_phrase}\r\n"

        # Headers copy
        headers = dict(response.headers)

        # RFC 7231 Date header: IMF-fixdate
        if "Date" not in headers:
            headers["Date"] = formatdate(timeval=None, localtime=False, usegmt=True)

        # Server identifier
        if "Server" not in headers:
            headers["Server"] = self.config.server_name

        # Connection persistence
        headers["Connection"] = "keep-alive" if keep_alive else "close"

        # Body handling per RFC 7230 / RFC 7231
        body_bytes = response.body or b""
        actual_content_length = len(body_bytes)

        # Responses that MUST NOT contain a message body:
        # 1xx, 204 (No Content), 304 (Not Modified)
        status = response.status_code
        must_not_have_body = (100 <= status < 200) or status == 204 or status == 304

        if must_not_have_body:
            body_to_send = b""
            # For 204, Content-Length should generally be omitted or 0
            if "Content-Length" in headers and status == 204:
                del headers["Content-Length"]
        elif is_head_request:
            # HEAD must calculate Content-Length as if sending GET, but transmit no body
            headers["Content-Length"] = str(actual_content_length)
            body_to_send = b""
        else:
            headers["Content-Length"] = str(actual_content_length)
            body_to_send = body_bytes

        # Serialize headers with CRLF injection validation
        header_lines = [status_line]
        for name, value in headers.items():
            s_name = str(name).strip()
            s_value = str(value).strip()

            # Prevent CRLF / header injection
            if "\r" in s_name or "\n" in s_name or "\r" in s_value or "\n" in s_value:
                raise InternalServerError("CRLF detected in response header")

            header_lines.append(f"{s_name}: {s_value}\r\n")

        header_lines.append("\r\n")
        header_bytes = "".join(header_lines).encode("latin1")

        return header_bytes, body_to_send

    def send_response(
        self,
        sock: socket.socket,
        response: Response,
        keep_alive: bool = False,
        is_head_request: bool = False,
    ) -> int:
        """
        Serializes and transmits the response over the socket.
        Uses sendall() / partial-write loop to ensure complete delivery.
        Returns total bytes written.
        """
        header_bytes, body_bytes = self.serialize_headers_and_body(
            response, keep_alive=keep_alive, is_head_request=is_head_request
        )

        full_frame = header_bytes + body_bytes
        total_sent = 0
        total_len = len(full_frame)

        # Full-send loop to handle partial TCP writes
        while total_sent < total_len:
            try:
                sent = sock.send(full_frame[total_sent:])
                if sent == 0:
                    raise ConnectionResetError("Socket connection broken during send")
                total_sent += sent
            except (BlockingIOError, InterruptedError):
                continue
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                raise ConnectionResetError(f"Client disconnected during write: {e}")

        return total_sent
