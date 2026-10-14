"""
WireView HTTP - Server Configuration
Defines default settings and limits for the raw socket HTTP server.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ServerConfig:
    # Network binding
    host: str = "127.0.0.1"
    port: int = 8080
    backlog: int = 128

    # Worker pool & concurrency limits
    max_workers: int = 32
    max_queue_size: int = 128
    connection_timeout: float = 30.0  # seconds for socket inactivity
    keep_alive_timeout: float = 15.0  # seconds between persistent requests
    max_requests_per_connection: int = 100

    # Socket I/O
    socket_recv_buffer_size: int = 8192
    socket_send_timeout: float = 10.0

    # HTTP Protocol limits (RFC protection & DoS mitigation)
    max_request_line_length: int = 4096       # bytes (RFC 7230: 414 URI Too Long)
    max_header_size: int = 8192               # total header bytes (431 Request Header Fields Too Large)
    max_header_count: int = 100               # max number of headers (431)
    max_body_size: int = 10 * 1024 * 1024     # 10 MB limit (413 Content Too Large)

    # Static file serving
    static_dir: Optional[Path] = field(default_factory=lambda: Path(__file__).resolve().parent.parent / "static")

    # Observability
    event_buffer_size: int = 1000
    metrics_window_seconds: int = 60

    # Server identification
    server_name: str = "WireView-HTTP/1.0 (Scratch-Built Low-Level Python Engine)"
