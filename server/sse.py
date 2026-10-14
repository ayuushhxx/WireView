"""
WireView HTTP - Server-Sent Events (SSE) Stream Handler
Manages persistent one-way event streaming over raw TCP sockets.
Transmits live structured telemetry, event replays, and periodic heartbeat comments.
"""

import queue
import socket
import threading
import time
from typing import Optional

from .events import EventEmitter, ServerEvent


def handle_sse_stream(
    sock: socket.socket,
    emitter: EventEmitter,
    shutdown_event: threading.Event,
    request_id: str = "",
    connection_id: str = "",
):
    """
    Handles a long-lived Server-Sent Events stream on an accepted raw socket.
    Streams recent and real-time events until client disconnects or server shuts down.
    """
    sub_queue = emitter.subscribe(replay_last=50)

    # Initial HTTP/1.1 200 response with SSE headers
    initial_response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: text/event-stream; charset=utf-8\r\n"
        b"Cache-Control: no-cache, no-transform\r\n"
        b"Connection: keep-alive\r\n"
        b"Access-Control-Allow-Origin: *\r\n"
        b"X-Accel-Buffering: no\r\n"
        b"\r\n"
    )

    try:
        sock.sendall(initial_response)

        # Emit connected event
        emitter.emit(
            event_type="sse_connected",
            stage="sse",
            message=f"Dashboard SSE client connected on connection {connection_id}",
            severity="info",
            request_id=request_id,
            connection_id=connection_id,
        )

        last_heartbeat = time.time()

        while not shutdown_event.is_set():
            try:
                # Wait for up to 1 second for a new event
                event: Optional[ServerEvent] = sub_queue.get(timeout=1.0)
            except queue.Empty:
                event = None

            now = time.time()

            if event is not None:
                sse_data = event.to_sse().encode("utf-8")
                try:
                    sock.sendall(sse_data)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break

            # Send heartbeat comment every 5 seconds to prevent network idle drops
            if now - last_heartbeat >= 5.0:
                heartbeat = b": keep-alive heartbeat\n\n"
                try:
                    sock.sendall(heartbeat)
                    last_heartbeat = now
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break

    finally:
        emitter.unsubscribe(sub_queue)
        emitter.emit(
            event_type="sse_disconnected",
            stage="sse",
            message=f"Dashboard SSE client disconnected on connection {connection_id}",
            severity="info",
            request_id=request_id,
            connection_id=connection_id,
        )
