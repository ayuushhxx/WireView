"""
Tests for HTTP/1.1 Request Parser.
Verifies RFC 7230 request line parsing, headers, body framing, limits, and injection defenses.
"""

import socket
import unittest
from server.buffer import StreamBuffer
from server.config import ServerConfig
from server.errors import (
    BadRequest,
    HTTPVersionNotSupported,
    HeaderFieldsTooLarge,
    NotImplementedHTTP,
    PayloadTooLarge,
    URITooLong,
)
from server.parser import HTTPParser


class TestHTTPParser(unittest.TestCase):

    def setUp(self):
        self.server_sock, self.client_sock = socket.socketpair()
        self.config = ServerConfig()
        self.parser = HTTPParser(self.config)

    def tearDown(self):
        self.server_sock.close()
        self.client_sock.close()

    def parse_raw(self, raw_data: bytes):
        self.client_sock.sendall(raw_data)
        buf = StreamBuffer(self.server_sock)
        return self.parser.parse_request(buf)

    def test_valid_get_request(self):
        raw = (
            b"GET /api/info?filter=all&page=1 HTTP/1.1\r\n"
            b"Host: 127.0.0.1:8080\r\n"
            b"User-Agent: TestClient/1.0\r\n"
            b"Accept: application/json\r\n"
            b"\r\n"
        )
        req = self.parse_raw(raw)
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.path, "/api/info")
        self.assertEqual(req.target, "/api/info?filter=all&page=1")
        self.assertEqual(req.version, "HTTP/1.1")
        self.assertEqual(req.query_params["filter"], "all")
        self.assertEqual(req.query_params["page"], "1")
        self.assertEqual(req.headers["Host"], "127.0.0.1:8080")
        self.assertEqual(req.headers["accept"], "application/json")  # case-insensitive
        self.assertEqual(req.body, b"")

    def test_post_with_content_length(self):
        body = b'{"name": "WireView", "active": true}'
        raw = (
            b"POST /api/echo HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: " + str(len(body)).encode() + b"\r\n"
            b"\r\n" + body
        )
        req = self.parse_raw(raw)
        self.assertEqual(req.method, "POST")
        self.assertEqual(req.body, body)
        self.assertEqual(req.json()["name"], "WireView")

    def test_url_normalization_and_path_traversal(self):
        raw = b"GET /static/../api/items HTTP/1.1\r\nHost: localhost\r\n\r\n"
        req = self.parse_raw(raw)
        self.assertEqual(req.path, "/api/items")

    def test_malformed_request_line_spaces(self):
        raw = b"GET /path\r\nHost: localhost\r\n\r\n"
        with self.assertRaises(BadRequest):
            self.parse_raw(raw)

    def test_invalid_http_version(self):
        raw = b"GET / HTTP/2.0\r\nHost: localhost\r\n\r\n"
        with self.assertRaises(HTTPVersionNotSupported):
            self.parse_raw(raw)

    def test_whitespace_before_colon_rejected(self):
        # RFC 7230 3.2.4: whitespace before colon MUST be rejected with 400
        raw = b"GET / HTTP/1.1\r\nHost : localhost\r\n\r\n"
        with self.assertRaises(BadRequest):
            self.parse_raw(raw)

    def test_conflicting_transfer_encoding_and_content_length(self):
        # RFC 7230 3.3.3 smuggling defense
        raw = (
            b"POST /upload HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: 10\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
        )
        with self.assertRaises(BadRequest):
            self.parse_raw(raw)

    def test_unsupported_transfer_encoding(self):
        raw = (
            b"POST /upload HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Transfer-Encoding: gzip\r\n\r\n"
        )
        with self.assertRaises(NotImplementedHTTP):
            self.parse_raw(raw)

    def test_payload_exceeding_max_body_size(self):
        custom_config = ServerConfig(max_body_size=50)
        parser = HTTPParser(custom_config)
        raw = (
            b"POST /api/echo HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Content-Length: 100\r\n\r\n"
        )
        self.client_sock.sendall(raw)
        buf = StreamBuffer(self.server_sock)
        with self.assertRaises(PayloadTooLarge):
            parser.parse_request(buf)


if __name__ == "__main__":
    unittest.main()
