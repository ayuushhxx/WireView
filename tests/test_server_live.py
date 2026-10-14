"""
Live integration tests for TCPServer.
Spawns the real server on a local TCP port and issues real network requests over raw sockets.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import socket
import threading
import time
import unittest

from server.config import ServerConfig
from server.events import EventEmitter
from server.handlers import ItemDatabase, create_app_router
from server.tcp_server import TCPServer


def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestServerLiveIntegration(unittest.TestCase):
    server: TCPServer
    server_thread: threading.Thread
    port: int

    @classmethod
    def setUpClass(cls):
        cls.port = get_free_port()
        config = ServerConfig(
            host="127.0.0.1",
            port=cls.port,
            max_workers=16,
            keep_alive_timeout=2.0,
            connection_timeout=5.0,
        )
        cls.emitter = EventEmitter()
        cls.router = create_app_router(config, cls.emitter, ItemDatabase())
        cls.server = TCPServer(config=config, router=cls.router, emitter=cls.emitter)

        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()

        # Wait for server to bind and start listening
        for _ in range(50):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(("127.0.0.1", cls.port))
                s.close()
                break
            except ConnectionRefusedError:
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.server_thread.join(timeout=2.0)

    def _send_raw_http(self, request_bytes: bytes, sock: socket.socket = None) -> bytes:
        close_sock = False
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("127.0.0.1", self.port))
            close_sock = True

        sock.sendall(request_bytes)

        # Read response
        response_bytes = bytearray()
        sock.settimeout(3.0)
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_bytes.extend(chunk)
                # Check if we have complete headers
                if b"\r\n\r\n" in response_bytes:
                    hdr, body = response_bytes.split(b"\r\n\r\n", 1)
                    # Check Content-Length
                    for line in hdr.split(b"\r\n"):
                        if line.lower().startswith(b"content-length:"):
                            cl = int(line.split(b":")[1].strip())
                            if len(body) >= cl:
                                if close_sock:
                                    sock.close()
                                return bytes(response_bytes)
            except socket.timeout:
                break

        if close_sock:
            sock.close()
        return bytes(response_bytes)

    def test_live_get_health(self):
        req = b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
        res = self._send_raw_http(req)
        self.assertIn(b"HTTP/1.1 200 OK", res)
        self.assertIn(b'"status": "healthy"', res)

    def test_live_post_echo(self):
        payload = json.dumps({"engine": "WireView", "test": "live_socket"}).encode("utf-8")
        req = (
            b"POST /api/echo HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(payload)).encode() + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n" + payload
        )
        res = self._send_raw_http(req)
        self.assertIn(b"HTTP/1.1 200 OK", res)
        self.assertIn(b'"engine": "WireView"', res)

    def test_live_items_crud_cycle(self):
        # 1. Create item
        item_payload = json.dumps({"title": "Test Socket Protocol", "category": "Testing"}).encode("utf-8")
        post_req = (
            b"POST /api/items HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(item_payload)).encode() + b"\r\n"
            b"Connection: close\r\n"
            b"\r\n" + item_payload
        )
        res = self._send_raw_http(post_req)
        self.assertIn(b"HTTP/1.1 201 Created", res)

        # Parse ID from response
        body_json = json.loads(res.split(b"\r\n\r\n")[1].decode("utf-8"))
        item_id = body_json["id"]

        # 2. Get item
        get_req = f"GET /api/items/{item_id} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode()
        res_get = self._send_raw_http(get_req)
        self.assertIn(b"HTTP/1.1 200 OK", res_get)
        self.assertIn(b"Test Socket Protocol", res_get)

        # 3. Delete item
        del_req = f"DELETE /api/items/{item_id} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode()
        res_del = self._send_raw_http(del_req)
        self.assertIn(b"HTTP/1.1 200 OK", res_del)

    def test_live_keep_alive_multiple_requests_one_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", self.port))
        sock.settimeout(3.0)

        try:
            # Request 1 (Keep-Alive)
            req1 = b"GET /api/time HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n"
            res1 = self._send_raw_http(req1, sock=sock)
            self.assertIn(b"HTTP/1.1 200 OK", res1)
            self.assertIn(b"Connection: keep-alive", res1)

            # Request 2 on the SAME socket
            req2 = b"GET /api/info HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
            res2 = self._send_raw_http(req2, sock=sock)
            self.assertIn(b"HTTP/1.1 200 OK", res2)
            self.assertIn(b"WireView HTTP", res2)
        finally:
            sock.close()

    def test_live_concurrency_stress(self):
        # Fire 20 parallel requests to test bounded thread pool and socket handling
        def make_req(i: int):
            req = f"GET /api/echo?worker={i} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n".encode()
            res = self._send_raw_http(req)
            return b"HTTP/1.1 200 OK" in res

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(make_req, range(20)))

        self.assertTrue(all(results))
        self.assertEqual(len(results), 20)

    def test_live_malformed_protocol_line(self):
        # Send raw invalid bytes over TCP
        req = b"CORRUPTED_REQUEST_WITHOUT_SPACES\r\n\r\n"
        res = self._send_raw_http(req)
        self.assertIn(b"HTTP/1.1 400 Bad Request", res)

    def test_live_metrics_endpoint_reflects_actual_traffic(self):
        req = b"GET /api/metrics HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
        res = self._send_raw_http(req)
        self.assertIn(b"HTTP/1.1 200 OK", res)
        metrics = json.loads(res.split(b"\r\n\r\n")[1].decode("utf-8"))
        self.assertGreater(metrics["total_requests"], 0)
        self.assertGreater(metrics["total_bytes_written"], 0)


if __name__ == "__main__":
    unittest.main()
