"""
WireView HTTP - Route Handlers
Implements standard application routes, educational pages, REST CRUD APIs,
metrics, and secure static file serving.
"""

from datetime import datetime, timezone
import json
import mimetypes
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

from .config import ServerConfig
from .errors import BadRequest, InternalServerError, NotFound
from .events import EventEmitter
from .models import Request, Response
from .router import Router

# In-memory demo items database (Networking RFCs & Concepts)
INITIAL_ITEMS = [
    {
        "id": "1",
        "title": "RFC 7230: HTTP/1.1 Message Syntax & Routing",
        "category": "Protocol Specification",
        "description": "Defines the low-level framing, request lines, headers, and connection management of HTTP/1.1.",
        "layer": "Application",
        "year": 2014,
    },
    {
        "id": "2",
        "title": "RFC 793: Transmission Control Protocol (TCP)",
        "category": "Transport Protocol",
        "description": "Specifies connection-oriented, reliable, ordered, byte-stream communication over IP.",
        "layer": "Transport",
        "year": 1981,
    },
    {
        "id": "3",
        "title": "Berkeley Sockets API",
        "category": "Systems Networking",
        "description": "Standard abstraction for endpoint communication, socket binding, listening, accepting, and I/O buffers.",
        "layer": "Operating System",
        "year": 1983,
    },
    {
        "id": "4",
        "title": "Server-Sent Events (SSE)",
        "category": "Streaming Web",
        "description": "W3C standard for unidirectional real-time event streaming over standard HTTP connections.",
        "layer": "Application",
        "year": 2011,
    },
]


class ItemDatabase:
    """Thread-safe in-memory CRUD database for demo items."""

    def __init__(self, initial_data: Optional[List[Dict[str, Any]]] = None):
        self._lock = threading.Lock()
        self._items: Dict[str, Dict[str, Any]] = {
            item["id"]: dict(item) for item in (initial_data or INITIAL_ITEMS)
        }
        self._next_id = max([int(i["id"]) for i in self._items.values()], default=0) + 1

    def list_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._items.values())

    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            item = self._items.get(item_id)
            return dict(item) if item else None

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            item_id = str(self._next_id)
            self._next_id += 1
            new_item = {
                "id": item_id,
                "title": data.get("title", f"Custom Protocol Item #{item_id}"),
                "category": data.get("category", "General Networking"),
                "description": data.get("description", "Created via WireView REST API."),
                "layer": data.get("layer", "Application"),
                "year": data.get("year", datetime.now().year),
            }
            self._items[item_id] = new_item
            return dict(new_item)

    def update(self, item_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self._lock:
            if item_id not in self._items:
                return None
            item = self._items[item_id]
            for k in ("title", "category", "description", "layer", "year"):
                if k in data:
                    item[k] = data[k]
            return dict(item)

    def delete(self, item_id: str) -> bool:
        with self._lock:
            if item_id in self._items:
                del self._items[item_id]
                return True
            return False


def create_app_router(
    config: ServerConfig,
    emitter: EventEmitter,
    item_db: Optional[ItemDatabase] = None,
) -> Router:
    """Configures and registers all routes on a new Router instance."""
    router = Router()
    db = item_db or ItemDatabase()

    # 1. Landing Page (GET /)
    @router.get("/")
    def handle_root(req: Request) -> Response:
        metrics = emitter.metrics.get_snapshot()
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WireView HTTP - Built From Scratch</title>
  <style>
    :root {{
      --bg: #090d16;
      --surface: #111827;
      --surface-border: #1f293d;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --accent: #0ea5e9;
      --accent-glow: rgba(14, 165, 233, 0.2);
      --success: #10b981;
      --warning: #f59e0b;
      --font: 'Segoe UI', system-ui, -apple-system, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: var(--font);
      line-height: 1.6;
      padding: 0;
    }}
    header {{
      background: linear-gradient(180deg, #0f172a 0%, var(--bg) 100%);
      border-bottom: 1px solid var(--surface-border);
      padding: 2.5rem 1.5rem;
      text-align: center;
    }}
    .badge {{
      display: inline-block;
      background: rgba(14, 165, 233, 0.15);
      color: var(--accent);
      border: 1px solid rgba(14, 165, 233, 0.3);
      padding: 0.3rem 0.8rem;
      border-radius: 9999px;
      font-size: 0.85rem;
      font-weight: 600;
      letter-spacing: 0.05em;
      margin-bottom: 1rem;
    }}
    h1 {{
      font-size: 2.75rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      margin-bottom: 0.75rem;
      background: linear-gradient(135deg, #fff 30%, #94a3b8 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    p.lead {{
      color: var(--text-muted);
      font-size: 1.15rem;
      max-width: 700px;
      margin: 0 auto 1.5rem auto;
    }}
    .actions {{
      display: flex;
      gap: 1rem;
      justify-content: center;
      margin-top: 1.5rem;
    }}
    .btn {{
      display: inline-block;
      padding: 0.75rem 1.75rem;
      border-radius: 8px;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s ease;
      font-size: 1rem;
    }}
    .btn-primary {{
      background: #0284c7;
      color: #fff;
      box-shadow: 0 4px 14px var(--accent-glow);
    }}
    .btn-primary:hover {{ background: #0369a1; transform: translateY(-2px); }}
    .btn-secondary {{
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--surface-border);
    }}
    .btn-secondary:hover {{ background: #1e293b; transform: translateY(-2px); }}
    .container {{
      max-width: 1100px;
      margin: 2.5rem auto;
      padding: 0 1.5rem;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2.5rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--surface-border);
      border-radius: 12px;
      padding: 1.5rem;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
    }}
    .card h2 {{
      font-size: 1.25rem;
      margin-bottom: 1rem;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .stat-row {{
      display: flex;
      justify-content: space-between;
      padding: 0.6rem 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 0.95rem;
    }}
    .stat-row:last-child {{ border-bottom: none; }}
    .stat-label {{ color: var(--text-muted); }}
    .stat-val {{ font-family: monospace; font-weight: bold; color: var(--text); }}
    .pipeline {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      background: #0b1120;
      border-radius: 8px;
      border: 1px solid var(--surface-border);
      margin-top: 1rem;
    }}
    .stage-node {{
      background: #1e293b;
      border: 1px solid #334155;
      padding: 0.5rem 0.85rem;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      color: #e2e8f0;
      font-family: monospace;
    }}
    .arrow {{ color: var(--accent); font-weight: bold; }}
    pre {{
      background: #030712;
      border: 1px solid #1f2937;
      padding: 1rem;
      border-radius: 8px;
      overflow-x: auto;
      font-size: 0.88rem;
      color: #a5f3fc;
      margin-top: 0.5rem;
    }}
    footer {{
      text-align: center;
      padding: 2.5rem 1rem;
      color: var(--text-muted);
      border-top: 1px solid var(--surface-border);
      font-size: 0.9rem;
    }}
  </style>
</head>
<body>
  <header>
    <div class="badge">RFC 7230 / PYTHON LOW-LEVEL SOCKETS</div>
    <h1>WireView HTTP</h1>
    <p class="lead">A true HTTP/1.1 Web Server engineered completely from scratch in Python using raw TCP sockets, accompanied by the WireView Studio real-time observability suite.</p>
    <div class="actions">
      <a href="/dashboard" class="btn btn-primary" id="open-studio-btn">Launch WireView Studio &rarr;</a>
      <a href="/api/info" class="btn btn-secondary">Server Info API</a>
      <a href="/health" class="btn btn-secondary">Health Check</a>
    </div>
  </header>

  <div class="container">
    <div class="grid">
      <div class="card">
        <h2>Live Server Status</h2>
        <div class="stat-row">
          <span class="stat-label">Server Version:</span>
          <span class="stat-val">{config.server_name}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Listening Interface:</span>
          <span class="stat-val">{config.host}:{config.port}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Total Requests Handled:</span>
          <span class="stat-val">{metrics['total_requests']}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Active TCP Connections:</span>
          <span class="stat-val">{metrics['active_connections']}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">Server Uptime:</span>
          <span class="stat-val">{metrics['server_uptime_seconds']}s</span>
        </div>
      </div>

      <div class="card">
        <h2>Architecture Highlights</h2>
        <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 1rem;">
          No Flask, FastAPI, Uvicorn, or Werkzeug. Every byte is read and written through raw Python <code>socket.recv()</code> and <code>socket.send()</code> calls.
        </p>
        <ul style="padding-left: 1.25rem; color: var(--text-muted); font-size: 0.9rem; line-height: 1.8;">
          <li>Buffered TCP Stream with CRLF boundary detection.</li>
          <li>RFC 7230 header validation &amp; injection defenses.</li>
          <li>Accurate byte-length Content-Length serialization.</li>
          <li>Real-time Server-Sent Events (SSE) telemetry stream.</li>
        </ul>
      </div>
    </div>

    <div class="card" style="margin-bottom: 2.5rem;">
      <h2>HTTP Request Execution Pipeline</h2>
      <p style="color: var(--text-muted); font-size: 0.95rem;">
        Every HTTP interaction flows deterministically through this pipeline. Malformed frames are trapped and rejected at the earliest stage:
      </p>
      <div class="pipeline">
        <div class="stage-node">TCP Socket Accept</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">StreamBuffer Chunking</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">HTTP/1.1 Parser</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">Security Validator</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">URL Router</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">Route Handler</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">Response Serializer</div>
        <span class="arrow">&rarr;</span>
        <div class="stage-node">TCP Socket Transmit</div>
      </div>
    </div>

    <div class="card">
      <h2>Quick Terminal Testing</h2>
      <p style="color: var(--text-muted); font-size: 0.95rem; margin-bottom: 0.75rem;">
        Test the server directly from your terminal using <code>curl</code>:
      </p>
      <pre># GET Request with JSON Response
curl -v http://{config.host}:{config.port}/api/info

# POST Request with Payload Validation
curl -X POST http://{config.host}:{config.port}/api/echo \
     -H "Content-Type: application/json" \
     -d '{{"client": "curl", "message": "Raw socket test"}}'

# Inspect Server-Sent Events Stream
curl -N http://{config.host}:{config.port}/api/events/stream</pre>
    </div>
  </div>

  <footer>
    WireView HTTP &bull; Built with standard-library Python TCP sockets &bull; Educational Computer Networks Capstone
  </footer>
</body>
</html>"""
        return Response.html(html)

    # 2. Health Endpoint (GET /health)
    @router.get("/health")
    def handle_health(req: Request) -> Response:
        metrics = emitter.metrics.get_snapshot()
        return Response.json({
            "status": "healthy",
            "uptime_seconds": metrics["server_uptime_seconds"],
            "server_version": config.server_name,
            "active_connections": metrics["active_connections"],
            "timestamp": time.time(),
        })

    # 3. Server Info API (GET /api/info)
    @router.get("/api/info")
    def handle_info(req: Request) -> Response:
        metrics = emitter.metrics.get_snapshot()
        return Response.json({
            "project_name": "WireView HTTP",
            "version": "1.0.0",
            "engine": "Low-level Python TCP socket HTTP/1.1 server",
            "supported_http_methods": ["GET", "HEAD", "POST", "PUT", "DELETE", "OPTIONS"],
            "supported_http_versions": ["HTTP/1.1", "HTTP/1.0"],
            "connection_policy": f"keep-alive up to {config.max_requests_per_connection} requests or {config.keep_alive_timeout}s timeout",
            "concurrency_model": f"ThreadPoolExecutor (max_workers={config.max_workers})",
            "limits": {
                "max_request_line_length": config.max_request_line_length,
                "max_header_size": config.max_header_size,
                "max_header_count": config.max_header_count,
                "max_body_size": config.max_body_size,
            },
            "server_uptime_seconds": metrics["server_uptime_seconds"],
        })

    # 4. Echo API (GET /api/echo)
    @router.get("/api/echo")
    def handle_echo_get(req: Request) -> Response:
        return Response.json({
            "method": req.method,
            "path": req.path,
            "target": req.target,
            "query_params": req.query_params,
            "headers": req.headers.to_dict(),
            "client_address": {"ip": req.client_address[0], "port": req.client_address[1]},
            "request_id": req.request_id,
            "connection_id": req.connection_id,
        })

    # 5. Echo API (POST /api/echo)
    @router.post("/api/echo")
    def handle_echo_post(req: Request) -> Response:
        try:
            body_json = req.json()
        except Exception as e:
            raise BadRequest(f"Invalid JSON payload: {e}")

        return Response.json({
            "message": "Payload successfully received and parsed",
            "received_json": body_json,
            "body_byte_length": len(req.body),
            "content_type": req.headers.get("Content-Type", "not specified"),
            "request_id": req.request_id,
            "timestamp": time.time(),
        })

    # 6. REST Items CRUD API
    @router.get("/api/items")
    def handle_items_list(req: Request) -> Response:
        items = db.list_all()
        return Response.json({"count": len(items), "items": items})

    @router.get("/api/items/{id}")
    def handle_item_get(req: Request) -> Response:
        item_id = req.path_params.get("id")
        item = db.get(item_id)
        if not item:
            raise NotFound(f"Item with ID '{item_id}' not found")
        return Response.json(item)

    @router.post("/api/items")
    def handle_item_create(req: Request) -> Response:
        try:
            data = req.json()
        except Exception:
            raise BadRequest("Invalid or missing JSON payload")

        if not isinstance(data, dict):
            raise BadRequest("JSON body must be an object")

        if "title" not in data or not str(data["title"]).strip():
            raise BadRequest("Field 'title' is required")

        created = db.create(data)
        return Response.json(created, status_code=201)

    @router.put("/api/items/{id}")
    def handle_item_update(req: Request) -> Response:
        item_id = req.path_params.get("id")
        try:
            data = req.json()
        except Exception:
            raise BadRequest("Invalid or missing JSON payload")

        if not isinstance(data, dict):
            raise BadRequest("JSON body must be an object")

        updated = db.update(item_id, data)
        if not updated:
            raise NotFound(f"Item with ID '{item_id}' not found")
        return Response.json(updated)

    @router.delete("/api/items/{id}")
    def handle_item_delete(req: Request) -> Response:
        item_id = req.path_params.get("id")
        deleted = db.delete(item_id)
        if not deleted:
            raise NotFound(f"Item with ID '{item_id}' not found")
        return Response.json({"deleted": True, "id": item_id})

    # 7. Server Time API (GET /api/time)
    @router.get("/api/time")
    def handle_time(req: Request) -> Response:
        now_utc = datetime.now(timezone.utc)
        return Response.json({
            "iso8601": now_utc.isoformat(),
            "epoch_timestamp": now_utc.timestamp(),
            "formatted": now_utc.strftime("%A, %d %B %Y %H:%M:%S UTC"),
            "request_id": req.request_id,
        })

    # 8. Real Server Metrics (GET /api/metrics)
    @router.get("/api/metrics")
    def handle_metrics(req: Request) -> Response:
        snapshot = emitter.metrics.get_snapshot()
        return Response.json(snapshot)

    # 9. Recent Events History (GET /api/events)
    @router.get("/api/events")
    def handle_events_list(req: Request) -> Response:
        limit = 100
        if "limit" in req.query_params:
            try:
                limit = int(req.query_params["limit"])
            except ValueError:
                pass
        events = emitter.get_recent_events(limit=min(limit, 500))
        return Response.json({
            "count": len(events),
            "events": events,
            "dropped_telemetry_count": emitter.dropped_telemetry_count,
        })

    # 10. Dashboard Route (GET /dashboard)
    @router.get("/dashboard")
    def handle_dashboard(req: Request) -> Response:
        # Check if production build of studio exists in static_dir/dist or static_dir
        if config.static_dir:
            dist_index = config.static_dir / "dist" / "index.html"
            if dist_index.is_file():
                content = dist_index.read_text(encoding="utf-8")
                return Response.html(content)
            
            static_index = config.static_dir / "index.html"
            if static_index.is_file():
                content = static_index.read_text(encoding="utf-8")
                return Response.html(content)

        # Fallback interactive dashboard page if Vite frontend is not yet built
        fallback_html = get_dashboard_fallback_html(config)
        return Response.html(fallback_html)

    # 11. Error Testing routes
    @router.get("/api/test/error")
    def handle_test_error(req: Request) -> Response:
        raise InternalServerError("Simulated 500 Internal Server Error for pipeline testing")

    @router.get("/api/test/slow")
    def handle_test_slow(req: Request) -> Response:
        delay = 0.5
        if "delay" in req.query_params:
            try:
                delay = float(req.query_params["delay"])
            except ValueError:
                pass
        time.sleep(min(delay, 5.0))
        return Response.json({"message": f"Simulated slow response after {delay}s delay"})

    # 12. Static Assets Serving (/assets/{filename} or /static/{filename})
    def serve_static_file(req: Request) -> Response:
        if not config.static_dir:
            raise NotFound("Static directory not configured")

        # Strip prefix
        relative_path_str = req.path
        if relative_path_str.startswith("/static/"):
            relative_path_str = relative_path_str[len("/static/"):]
        elif relative_path_str.startswith("/dashboard/assets/"):
            relative_path_str = "dist/assets/" + relative_path_str[len("/dashboard/assets/"):]
        elif relative_path_str.startswith("/assets/"):
            relative_path_str = "dist/assets/" + relative_path_str[len("/assets/"):]
        else:
            relative_path_str = relative_path_str.lstrip("/")

        target_file = (config.static_dir / relative_path_str).resolve()

        # Security check: Prevent path traversal outside static_dir
        try:
            target_file.relative_to(config.static_dir.resolve())
        except ValueError:
            raise BadRequest("Path traversal attempt detected")

        if not target_file.is_file():
            raise NotFound(f"Static file not found: {req.path}")

        mime_type, _ = mimetypes.guess_type(str(target_file))
        if not mime_type:
            if str(target_file).endswith(".js"):
                mime_type = "application/javascript"
            elif str(target_file).endswith(".css"):
                mime_type = "text/css"
            else:
                mime_type = "application/octet-stream"

        try:
            content_bytes = target_file.read_bytes()
        except OSError as e:
            raise InternalServerError(f"Unable to read file: {e}")

        headers = {
            "Content-Type": mime_type,
            "Cache-Control": "public, max-age=3600",
        }
        return Response(status_code=200, headers=headers, body=content_bytes)

    # Register static asset routes
    router.add_route("/dashboard", ["GET", "HEAD"], handle_dashboard)
    router.add_route("/dashboard/", ["GET", "HEAD"], handle_dashboard)
    router.add_route("/static/{file}", ["GET", "HEAD"], serve_static_file)
    router.add_route("/assets/{file}", ["GET", "HEAD"], serve_static_file)
    router.add_route("/dashboard/assets/{file}", ["GET", "HEAD"], serve_static_file)

    return router


def get_dashboard_fallback_html(config: ServerConfig) -> str:
    """Provides a standalone interactive WireView Studio dashboard if Vite is compiling."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>WireView Studio - Low-Level Network Inspector</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {{
      --bg: #090d16;
      --surface: #111827;
      --border: #1f2937;
      --accent: #0ea5e9;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: system-ui, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }}
    header {{ background: #0f172a; border-bottom: 1px solid var(--border); padding: 0.75rem 1.5rem; display: flex; justify-content: space-between; align-items: center; }}
    .logo {{ font-weight: 800; font-size: 1.25rem; color: #38bdf8; display: flex; align-items: center; gap: 0.5rem; }}
    .status-badge {{ background: rgba(16, 185, 129, 0.2); color: var(--success); border: 1px solid var(--success); padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; gap: 0.4rem; }}
    .status-dot {{ width: 8px; height: 8px; background: var(--success); border-radius: 50%; display: inline-block; }}
    main {{ display: grid; grid-template-columns: 320px 1fr 360px; flex: 1; overflow: hidden; }}
    .panel {{ background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }}
    .panel:last-child {{ border-right: none; }}
    .panel-header {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.9rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; display: flex; justify-content: space-between; align-items: center; }}
    .panel-body {{ padding: 1rem; flex: 1; overflow-y: auto; }}
    .btn {{ background: #0284c7; color: white; border: none; padding: 0.6rem 1rem; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.85rem; width: 100%; margin-bottom: 0.5rem; }}
    .btn:hover {{ background: #0369a1; }}
    .btn-outline {{ background: transparent; border: 1px solid var(--border); color: var(--text); }}
    .btn-outline:hover {{ background: #1e293b; }}
    .event-item {{ background: #0b1120; border-left: 3px solid var(--accent); padding: 0.5rem 0.75rem; margin-bottom: 0.5rem; border-radius: 4px; font-size: 0.8rem; font-family: monospace; }}
    .event-item.error {{ border-left-color: var(--danger); }}
    .event-item.success {{ border-left-color: var(--success); }}
    .event-item.warning {{ border-left-color: var(--warning); }}
    .metric-box {{ background: #0b1120; border: 1px solid var(--border); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.75rem; }}
    .metric-val {{ font-size: 1.5rem; font-weight: bold; color: #38bdf8; }}
    .metric-lbl {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }}
  </style>
</head>
<body>
  <header>
    <div class="logo"><span>⚡</span> WireView Studio</div>
    <div class="status-badge" id="conn-status"><span class="status-dot"></span> CONNECTED (SSE LIVE)</div>
  </header>
  <main>
    <section class="panel">
      <div class="panel-header">Request Generator</div>
      <div class="panel-body">
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1rem;">Send real HTTP requests through the scratch-built TCP engine:</p>
        <button class="btn" onclick="sendReq('GET', '/health')">GET /health</button>
        <button class="btn" onclick="sendReq('GET', '/api/info')">GET /api/info</button>
        <button class="btn" onclick="sendReq('POST', '/api/items', {{title: 'RFC 9110 HTTP Semantics', category: 'Standards'}})">POST /api/items</button>
        <button class="btn btn-outline" onclick="sendReq('GET', '/api/nonexistent')">Test 404 Not Found</button>
        <button class="btn btn-outline" onclick="sendReq('POST', '/api/time')">Test 405 Method Not Allowed</button>
        <button class="btn btn-outline" onclick="sendReq('GET', '/api/test/error')">Test 500 Server Error</button>
      </div>
    </section>
    <section class="panel" style="background: #090d16;">
      <div class="panel-header">Real-Time Networking Pipeline</div>
      <div class="panel-body" style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
        <svg width="600" height="350" viewBox="0 0 600 350" style="max-width: 100%;">
          <rect x="20" y="150" width="100" height="50" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
          <text x="70" y="180" fill="#fff" font-size="12" font-family="sans-serif" text-anchor="middle">TCP Client</text>
          
          <line x1="120" y1="175" x2="180" y2="175" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4"/>
          
          <rect x="180" y="150" width="100" height="50" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
          <text x="230" y="180" fill="#fff" font-size="12" font-family="sans-serif" text-anchor="middle">HTTP Parser</text>
          
          <line x1="280" y1="175" x2="340" y2="175" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4"/>
          
          <rect x="340" y="150" width="100" height="50" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
          <text x="390" y="180" fill="#fff" font-size="12" font-family="sans-serif" text-anchor="middle">Router</text>
          
          <line x1="440" y1="175" x2="500" y2="175" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4"/>
          
          <rect x="500" y="150" width="90" height="50" rx="8" fill="#1e293b" stroke="#10b981" stroke-width="2"/>
          <text x="545" y="180" fill="#fff" font-size="12" font-family="sans-serif" text-anchor="middle">Response</text>
        </svg>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 1rem;">Live request flow animations update synchronously with server telemetry.</p>
      </div>
    </section>
    <section class="panel">
      <div class="panel-header">Live Server Telemetry</div>
      <div class="panel-body" id="event-log">
        <div class="metric-box">
          <div class="metric-lbl">Total Requests</div>
          <div class="metric-val" id="metric-total">0</div>
        </div>
        <div class="metric-box">
          <div class="metric-lbl">Active TCP Sockets</div>
          <div class="metric-val" id="metric-active">0</div>
        </div>
        <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); margin: 1rem 0 0.5rem 0;">EVENT LOG STREAM</div>
        <div id="events-list"></div>
      </div>
    </section>
  </main>
  <script>
    const evtList = document.getElementById('events-list');
    const metricTotal = document.getElementById('metric-total');
    const metricActive = document.getElementById('metric-active');
    
    const evtSource = new EventSource('/api/events/stream');
    evtSource.onmessage = (e) => {{
      try {{
        const ev = JSON.parse(e.data);
        const div = document.createElement('div');
        div.className = 'event-item ' + (ev.severity || 'info');
        div.textContent = `[${{ev.stage}}] ${{ev.message}}`;
        evtList.insertBefore(div, evtList.firstChild);
        if (evtList.childNodes.length > 50) evtList.removeChild(evtList.lastChild);
      }} catch(err) {{}}
    }};
    
    function refreshMetrics() {{
      fetch('/api/metrics').then(r=>r.json()).then(d=>{{
        metricTotal.textContent = d.total_requests;
        metricActive.textContent = d.active_connections;
      }}).catch(()=>{{}});
    }}
    setInterval(refreshMetrics, 1000);
    refreshMetrics();

    function sendReq(method, url, data) {{
      const opts = {{ method }};
      if (data) {{
        opts.headers = {{ 'Content-Type': 'application/json' }};
        opts.body = JSON.stringify(data);
      }}
      fetch(url, opts).then(r=>r.text()).then(t=>console.log(t)).catch(console.error);
    }}
  </script>
</body>
</html>"""
