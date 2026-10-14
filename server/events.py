"""
WireView HTTP - Observability Engine & Event System
Thread-safe event streaming, ring buffering, and real-time metric tracking.
Powers the live WireView Studio dashboard and SSE telemetry.
"""

from collections import deque
from dataclasses import asdict, dataclass, field
import json
import queue
import threading
import time
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class ServerEvent:
    """Structured telemetry event emitted during request/connection lifecycles."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    event_type: str = "general"
    stage: str = "server"
    message: str = ""
    severity: str = "info"  # info, success, warning, error
    request_id: Optional[str] = None
    connection_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def to_sse(self) -> str:
        """Format as standard Server-Sent Event."""
        return f"id: {self.event_id}\nevent: {self.event_type}\ndata: {self.to_json()}\n\n"


class MetricsCollector:
    """Thread-safe accumulator of real server networking and performance measurements."""

    def __init__(self, latency_window_size: int = 500):
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.total_requests = 0
        self.active_connections = 0
        self.peak_connections = 0
        self.total_connections = 0
        self.total_bytes_read = 0
        self.total_bytes_written = 0

        # Status code counters
        self.status_counts: Dict[int, int] = {}
        self.status_categories: Dict[str, int] = {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0}

        # Latency tracking (in milliseconds)
        self.latency_window: deque[float] = deque(maxlen=latency_window_size)

        # Sliding window for req/sec rate (timestamps of requests)
        self.request_timestamps: deque[float] = deque(maxlen=2000)

        # Stage timings aggregate (stage -> deque of durations in ms)
        self.stage_timings: Dict[str, deque[float]] = {
            "parse": deque(maxlen=200),
            "validate": deque(maxlen=200),
            "route": deque(maxlen=200),
            "handler": deque(maxlen=200),
            "serialize": deque(maxlen=200),
            "transmit": deque(maxlen=200),
        }

    def connection_opened(self):
        with self._lock:
            self.active_connections += 1
            self.total_connections += 1
            if self.active_connections > self.peak_connections:
                self.peak_connections = self.active_connections

    def connection_closed(self, bytes_read: int = 0, bytes_written: int = 0):
        with self._lock:
            self.active_connections = max(0, self.active_connections - 1)
            self.total_bytes_read += bytes_read
            self.total_bytes_written += bytes_written

    def record_request(
        self,
        status_code: int,
        latency_ms: float,
        stage_timings: Optional[Dict[str, float]] = None,
        bytes_in: int = 0,
        bytes_out: int = 0,
    ):
        with self._lock:
            now = time.time()
            self.total_requests += 1
            self.request_timestamps.append(now)

            # NOTE: bytes_read/written are accumulated in connection_closed() per-connection,
            # NOT here, to avoid double-counting.

            # Status code
            self.status_counts[status_code] = self.status_counts.get(status_code, 0) + 1
            cat = f"{status_code // 100}xx"
            if cat in self.status_categories:
                self.status_categories[cat] += 1

            # Latency
            self.latency_window.append(latency_ms)

            # Stage timings
            if stage_timings:
                for stage, duration in stage_timings.items():
                    if stage in self.stage_timings:
                        self.stage_timings[stage].append(duration)

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            now = time.time()
            uptime_seconds = now - self.start_time

            # Compute req/sec in last 5 seconds
            five_sec_ago = now - 5.0
            recent_reqs = sum(1 for t in self.request_timestamps if t >= five_sec_ago)
            req_per_sec = round(recent_reqs / 5.0, 2) if uptime_seconds >= 1 else round(float(self.total_requests), 2)

            # Latency statistics
            latencies = list(self.latency_window)
            if latencies:
                sorted_lats = sorted(latencies)
                count = len(sorted_lats)
                p50 = sorted_lats[int(count * 0.50)]
                p95 = sorted_lats[min(int(count * 0.95), count - 1)]
                p99 = sorted_lats[min(int(count * 0.99), count - 1)]
                avg_lat = sum(sorted_lats) / count
                min_lat = sorted_lats[0]
                max_lat = sorted_lats[-1]
            else:
                p50 = p95 = p99 = avg_lat = min_lat = max_lat = 0.0

            # Average stage timings
            avg_stages = {}
            for stage, deq in self.stage_timings.items():
                if deq:
                    avg_stages[stage] = round(sum(deq) / len(deq), 3)
                else:
                    avg_stages[stage] = 0.0

            return {
                "server_uptime_seconds": round(uptime_seconds, 2),
                "total_requests": self.total_requests,
                "requests_per_second": req_per_sec,
                "active_connections": self.active_connections,
                "peak_connections": self.peak_connections,
                "total_connections": self.total_connections,
                "total_bytes_read": self.total_bytes_read,
                "total_bytes_written": self.total_bytes_written,
                "status_categories": dict(self.status_categories),
                "status_counts": dict(self.status_counts),
                "latency_ms": {
                    "avg": round(avg_lat, 2),
                    "min": round(min_lat, 2),
                    "max": round(max_lat, 2),
                    "p50": round(p50, 2),
                    "p95": round(p95, 2),
                    "p99": round(p99, 2),
                },
                "stage_timings_ms": avg_stages,
            }


class EventEmitter:
    """
    Observability engine:
    - Maintains a bounded ring-buffer of recent events.
    - Dispatches live events to SSE subscriber queues safely without blocking HTTP handlers.
    - Tracks dropped telemetry counters.
    """

    def __init__(self, max_buffer_size: int = 1000):
        self.max_buffer_size = max_buffer_size
        self._lock = threading.Lock()
        self._ring_buffer: deque[ServerEvent] = deque(maxlen=max_buffer_size)
        self._subscribers: List[queue.Queue[ServerEvent]] = []
        self.metrics = MetricsCollector()
        self.dropped_telemetry_count = 0

    def emit(
        self,
        event_type: str,
        stage: str,
        message: str,
        severity: str = "info",
        request_id: Optional[str] = None,
        connection_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServerEvent:
        """Constructs and publishes an event."""
        event = ServerEvent(
            event_type=event_type,
            stage=stage,
            message=message,
            severity=severity,
            request_id=request_id,
            connection_id=connection_id,
            metadata=metadata or {},
        )

        with self._lock:
            self._ring_buffer.append(event)
            dead_subscribers = []

            for sub_queue in self._subscribers:
                try:
                    # Non-blocking put with bounded capacity
                    sub_queue.put_nowait(event)
                except queue.Full:
                    # Subscriber fell behind, drop event to protect server latency
                    self.dropped_telemetry_count += 1
                except Exception:
                    dead_subscribers.append(sub_queue)

            for dead in dead_subscribers:
                if dead in self._subscribers:
                    self._subscribers.remove(dead)

        return event

    def subscribe(self, replay_last: int = 100, max_queue_size: int = 250) -> queue.Queue[ServerEvent]:
        """Registers a new SSE listener queue and optionally seeds it with recent events."""
        sub_queue: queue.Queue[ServerEvent] = queue.Queue(maxsize=max_queue_size)
        with self._lock:
            # Seed replay buffer
            if replay_last > 0:
                recent = list(self._ring_buffer)[-replay_last:]
                for ev in recent:
                    try:
                        sub_queue.put_nowait(ev)
                    except queue.Full:
                        break
            self._subscribers.append(sub_queue)
        return sub_queue

    def unsubscribe(self, sub_queue: queue.Queue[ServerEvent]):
        """Deregisters an SSE listener queue."""
        with self._lock:
            if sub_queue in self._subscribers:
                self._subscribers.remove(sub_queue)

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Returns the most recent events as serializable dictionaries."""
        with self._lock:
            events = list(self._ring_buffer)[-limit:]
            return [e.to_dict() for e in events]


# Global observability singleton
_global_event_emitter: Optional[EventEmitter] = None


def get_event_emitter() -> EventEmitter:
    global _global_event_emitter
    if _global_event_emitter is None:
        _global_event_emitter = EventEmitter()
    return _global_event_emitter
