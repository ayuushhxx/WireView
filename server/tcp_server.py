"""
WireView HTTP - Raw TCP Socket Server
Implements low-level TCP connection acceptance, bounded worker thread pool concurrency,
keep-alive connection cycling, protocol lifecycle event emission, and graceful shutdown.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
import socket
import threading
import time
from typing import Optional, Tuple
import uuid

from .buffer import StreamBuffer
from .config import ServerConfig
from .errors import (
    ConnectionClosedEarly,
    HTTPError,
    InternalServerError,
    ReadTimeout,
    ServiceUnavailable,
)
from .events import EventEmitter, get_event_emitter
from .handlers import create_app_router
from .models import Request, Response
from .parser import HTTPParser
from .router import Router
from .serializer import ResponseSerializer
from .sse import handle_sse_stream

logger = logging.getLogger("wireview.tcp")


class TCPServer:
    """
    Low-level HTTP/1.1 Web Server built directly on raw BSD sockets.
    """

    def __init__(
        self,
        config: Optional[ServerConfig] = None,
        router: Optional[Router] = None,
        emitter: Optional[EventEmitter] = None,
    ):
        self.config = config or ServerConfig()
        self.emitter = emitter or get_event_emitter()
        self.router = router or create_app_router(self.config, self.emitter)
        self.parser = HTTPParser(self.config)
        self.serializer = ResponseSerializer(self.config)

        self._shutdown_event = threading.Event()
        self._listening_sock: Optional[socket.socket] = None
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix="WireView-Worker",
        )
        self._conn_counter = 0
        self._counter_lock = threading.Lock()
        self._active_sockets: set[socket.socket] = set()
        self._active_sockets_lock = threading.Lock()

    def _next_connection_id(self) -> str:
        with self._counter_lock:
            self._conn_counter += 1
            return f"conn_{self._conn_counter:04d}"

    def start(self):
        """Binds the listening socket and begins accepting client connections."""
        self._shutdown_event.clear()

        # 1. Create listening socket
        self._listening_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Socket options
        self._listening_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 2. Bind and Listen
        self._listening_sock.bind((self.config.host, self.config.port))
        self._listening_sock.listen(self.config.backlog)
        self._listening_sock.settimeout(1.0)  # Allows checking _shutdown_event periodically

        self.emitter.emit(
            event_type="server_started",
            stage="tcp_accept",
            message=f"Listening on http://{self.config.host}:{self.config.port} (Workers: {self.config.max_workers})",
            severity="info",
            metadata={"host": self.config.host, "port": self.config.port, "workers": self.config.max_workers},
        )
        logger.info(f"Server started on http://{self.config.host}:{self.config.port}")

        # 3. Connection accept loop
        try:
            while not self._shutdown_event.is_set():
                try:
                    client_sock, client_addr = self._listening_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._shutdown_event.is_set():
                        break
                    raise

                # Client accepted! Dispatch to thread pool
                try:
                    self._executor.submit(self._handle_client_connection, client_sock, client_addr)
                except RuntimeError:
                    # Executor shutting down
                    client_sock.close()
                    break

        finally:
            self.stop()

    def stop(self):
        """Gracefully shuts down the listening socket and worker threads."""
        if self._shutdown_event.is_set():
            return
        self._shutdown_event.set()

        self.emitter.emit(
            event_type="server_stopping",
            stage="server",
            message="Server shutdown initiated",
            severity="warning",
        )

        # Close listening socket
        if self._listening_sock:
            try:
                self._listening_sock.close()
            except Exception:
                pass
            self._listening_sock = None

        # Close any active client sockets
        with self._active_sockets_lock:
            for s in list(self._active_sockets):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
                except Exception:
                    pass
            self._active_sockets.clear()

        # Shutdown thread pool
        self._executor.shutdown(wait=False, cancel_futures=True)

        self.emitter.emit(
            event_type="server_stopped",
            stage="server",
            message="Server shutdown complete",
            severity="info",
        )

    def _track_socket(self, sock: socket.socket):
        with self._active_sockets_lock:
            self._active_sockets.add(sock)

    def _untrack_socket(self, sock: socket.socket):
        with self._active_sockets_lock:
            self._active_sockets.discard(sock)

    def _handle_client_connection(self, client_sock: socket.socket, client_addr: Tuple[str, int]):
        """Manages the full lifecycle of a TCP client connection."""
        conn_id = self._next_connection_id()
        self._track_socket(client_sock)
        self.emitter.metrics.connection_opened()

        self.emitter.emit(
            event_type="connection_opened",
            stage="tcp_accept",
            message=f"TCP connection accepted from {client_addr[0]}:{client_addr[1]}",
            severity="info",
            connection_id=conn_id,
            metadata={"client_ip": client_addr[0], "client_port": client_addr[1]},
        )

        stream = StreamBuffer(client_sock, chunk_size=self.config.socket_recv_buffer_size)
        requests_served = 0
        bytes_sent_total = 0

        # Configure initial socket timeout
        client_sock.settimeout(self.config.connection_timeout)

        try:
            while not self._shutdown_event.is_set():
                req_start_time = time.perf_counter()
                request_id = f"req_{uuid.uuid4().hex[:8]}"
                stage_timings: dict[str, float] = {}

                # 1. Parse Request Line & Headers
                try:
                    # Emitted when first byte arrives
                    parse_start = time.perf_counter()
                    req = self.parser.parse_request(
                        stream,
                        client_address=client_addr,
                        request_id=request_id,
                        connection_id=conn_id,
                    )
                    parse_duration = (time.perf_counter() - parse_start) * 1000
                    stage_timings["parse"] = parse_duration

                    is_internal = req.path == "/api/metrics" or req.headers.get("x-internal-poll") == "1"

                    if not is_internal:
                        self.emitter.emit(
                            event_type="request_line_parsed",
                            stage="parse",
                            message=f"{req.method} {req.target} {req.version}",
                            severity="info",
                            request_id=request_id,
                            connection_id=conn_id,
                            metadata={
                                "method": req.method,
                                "path": req.path,
                                "target": req.target,
                                "version": req.version,
                                "headers_count": len(req.headers),
                                "content_length": len(req.body),
                                "parse_duration_ms": round(parse_duration, 2),
                            },
                        )

                except ConnectionClosedEarly:
                    # Client closed connection cleanly between keep-alive requests
                    break
                except ReadTimeout:
                    # Keep-alive socket idle timeout expired
                    break
                except HTTPError as err:
                    # Known protocol error (400, 414, 431, 501, 505)
                    self._handle_protocol_error(client_sock, err, request_id, conn_id, req_start_time)
                    break
                except Exception as ex:
                    # Unexpected parsing failure -> 400 Bad Request
                    err = InternalServerError(f"Request parsing error: {ex}")
                    self._handle_protocol_error(client_sock, err, request_id, conn_id, req_start_time)
                    break

                # 2. Check for SSE Stream Endpoint
                if req.path == "/api/events/stream" and req.method == "GET":
                    # Delegate persistent streaming to SSE loop
                    handle_sse_stream(
                        client_sock,
                        self.emitter,
                        self._shutdown_event,
                        request_id=request_id,
                        connection_id=conn_id,
                    )
                    return

                # 3. Request Validation
                val_start = time.perf_counter()
                if not is_internal:
                    self.emitter.emit(
                        event_type="request_validated",
                        stage="validate",
                        message="Request passed framing & security checks",
                        severity="success",
                        request_id=request_id,
                        connection_id=conn_id,
                    )
                stage_timings["validate"] = (time.perf_counter() - val_start) * 1000

                # 4. Route Matching
                route_start = time.perf_counter()
                try:
                    handler, path_params, is_auto_head = self.router.match(req)
                    req.path_params = path_params
                    route_duration = (time.perf_counter() - route_start) * 1000
                    stage_timings["route"] = route_duration

                    if not is_internal:
                        self.emitter.emit(
                            event_type="route_matched",
                            stage="route",
                            message=f"Matched route for {req.method} {req.path}",
                            severity="info",
                            request_id=request_id,
                            connection_id=conn_id,
                            metadata={"path_params": path_params, "is_auto_head": is_auto_head},
                        )
                except HTTPError as err:
                    self._handle_protocol_error(client_sock, err, request_id, conn_id, req_start_time)
                    break

                # 5. Handler Execution
                handler_start = time.perf_counter()
                try:
                    response = handler(req)
                    if is_auto_head:
                        response.is_head_response = True
                    handler_duration = (time.perf_counter() - handler_start) * 1000
                    stage_timings["handler"] = handler_duration
                except HTTPError as err:
                    self._handle_protocol_error(client_sock, err, request_id, conn_id, req_start_time)
                    break
                except Exception as ex:
                    logger.exception(f"Unhandled exception in handler for {req.path}: {ex}")
                    err = InternalServerError(f"Unhandled server error: {ex}")
                    self._handle_protocol_error(client_sock, err, request_id, conn_id, req_start_time)
                    break

                # 6. Response Serialization & Transmission
                requests_served += 1
                keep_alive = (
                    req.is_keep_alive
                    and requests_served < self.config.max_requests_per_connection
                    and not self._shutdown_event.is_set()
                )

                serialize_start = time.perf_counter()
                if not is_internal:
                    self.emitter.emit(
                        event_type="response_created",
                        stage="serialize",
                        message=f"Serialized response {response.status_code} {response.reason_phrase}",
                        severity="info",
                        request_id=request_id,
                        connection_id=conn_id,
                        metadata={"status_code": response.status_code, "headers": response.headers},
                    )
                stage_timings["serialize"] = (time.perf_counter() - serialize_start) * 1000

                # Send over TCP socket
                tx_start = time.perf_counter()
                try:
                    bytes_sent = self.serializer.send_response(
                        client_sock,
                        response,
                        keep_alive=keep_alive,
                        is_head_request=(req.method == "HEAD" or response.is_head_response),
                    )
                    bytes_sent_total += bytes_sent
                except ConnectionResetError:
                    break

                stage_timings["transmit"] = (time.perf_counter() - tx_start) * 1000
                total_req_latency_ms = (time.perf_counter() - req_start_time) * 1000

                if not is_internal:
                    # Record metrics
                    self.emitter.metrics.record_request(
                        status_code=response.status_code,
                        latency_ms=total_req_latency_ms,
                        stage_timings=stage_timings,
                        bytes_in=len(req.body),
                        bytes_out=bytes_sent,
                    )

                    severity_level = (
                        "success" if response.status_code < 400
                        else "warning" if response.status_code < 500
                        else "error"
                    )
                    self.emitter.emit(
                        event_type="request_completed",
                        stage="tcp_send",
                        message=f"HTTP/1.1 {response.status_code} sent ({bytes_sent} bytes, {total_req_latency_ms:.2f}ms)",
                        severity=severity_level,
                        request_id=request_id,
                        connection_id=conn_id,
                        metadata={
                            "status_code": response.status_code,
                            "bytes_sent": bytes_sent,
                            "latency_ms": round(total_req_latency_ms, 2),
                            "stage_timings": stage_timings,
                            "keep_alive": keep_alive,
                        },
                    )

                if not keep_alive:
                    break

                # Prepare socket for next keep-alive request with idle timeout
                client_sock.settimeout(self.config.keep_alive_timeout)

        finally:
            self._untrack_socket(client_sock)
            try:
                client_sock.close()
            except Exception:
                pass

            self.emitter.metrics.connection_closed(
                bytes_read=stream.total_bytes_read,
                bytes_written=bytes_sent_total,
            )

            self.emitter.emit(
                event_type="connection_closed",
                stage="tcp_close",
                message=f"TCP connection closed (Requests: {requests_served}, In: {stream.total_bytes_read}B, Out: {bytes_sent_total}B)",
                severity="info",
                connection_id=conn_id,
                metadata={
                    "requests_served": requests_served,
                    "bytes_read": stream.total_bytes_read,
                    "bytes_written": bytes_sent_total,
                },
            )

    def _handle_protocol_error(
        self,
        sock: socket.socket,
        err: HTTPError,
        request_id: str,
        connection_id: str,
        start_time: float,
    ):
        """Constructs and sends an RFC error response over the socket, then terminates connection."""
        latency_ms = (time.perf_counter() - start_time) * 1000

        self.emitter.emit(
            event_type="request_rejected",
            stage=err.stage,
            message=f"{err.status_code} {err.reason_phrase}: {err.message}",
            severity="error",
            request_id=request_id,
            connection_id=connection_id,
            metadata={
                "status_code": err.status_code,
                "error_reason": err.reason_phrase,
                "error_message": err.message,
                "latency_ms": round(latency_ms, 2),
            },
        )

        response = Response.error(err.status_code, err.message, headers=err.headers)
        try:
            bytes_sent = self.serializer.send_response(sock, response, keep_alive=False)
            self.emitter.metrics.record_request(
                status_code=err.status_code,
                latency_ms=latency_ms,
                bytes_out=bytes_sent,
            )
        except Exception:
            pass
