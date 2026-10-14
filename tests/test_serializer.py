"""
Tests for HTTP/1.1 Response Serializer.
Verifies status line generation, header injection defenses, byte-length calculations, and bodyless response rules.
"""

import socket
import unittest
from server.errors import InternalServerError
from server.models import Response
from server.serializer import ResponseSerializer


class TestResponseSerializer(unittest.TestCase):

    def setUp(self):
        self.serializer = ResponseSerializer()
        self.server_sock, self.client_sock = socket.socketpair()

    def tearDown(self):
        self.server_sock.close()
        self.client_sock.close()

    def test_serialize_json_response(self):
        resp = Response.json({"status": "ok", "items": [1, 2, 3]})
        hdr_bytes, body_bytes = self.serializer.serialize_headers_and_body(resp, keep_alive=True)

        hdr_text = hdr_bytes.decode("latin1")
        self.assertTrue(hdr_text.startswith("HTTP/1.1 200 OK\r\n"))
        self.assertIn("Connection: keep-alive\r\n", hdr_text)
        self.assertIn("Content-Type: application/json; charset=utf-8\r\n", hdr_text)
        self.assertIn(f"Content-Length: {len(body_bytes)}\r\n", hdr_text)
        self.assertIn("Date: ", hdr_text)

    def test_unicode_content_length_is_in_bytes(self):
        # Multibyte emoji and characters: length in characters != length in bytes
        unicode_str = "🚀 WireView 网络 🌐"
        resp = Response.text(unicode_str)
        hdr_bytes, body_bytes = self.serializer.serialize_headers_and_body(resp)

        hdr_text = hdr_bytes.decode("latin1")
        expected_byte_len = len(unicode_str.encode("utf-8"))
        self.assertIn(f"Content-Length: {expected_byte_len}\r\n", hdr_text)
        self.assertEqual(len(body_bytes), expected_byte_len)

    def test_crlf_header_injection_defense(self):
        resp = Response(
            status_code=200,
            headers={"X-Custom": "SafeValue\r\nInjected-Header: evil"},
            body=b"test",
        )
        with self.assertRaises(InternalServerError):
            self.serializer.serialize_headers_and_body(resp)

    def test_204_no_content_bodyless(self):
        resp = Response.no_content()
        hdr_bytes, body_bytes = self.serializer.serialize_headers_and_body(resp)
        hdr_text = hdr_bytes.decode("latin1")

        self.assertTrue(hdr_text.startswith("HTTP/1.1 204 No Content\r\n"))
        self.assertEqual(body_bytes, b"")
        self.assertNotIn("Content-Length", hdr_text)

    def test_head_request_omits_body_but_retains_length(self):
        body = b"Hello, World!"
        resp = Response(status_code=200, headers={}, body=body)
        hdr_bytes, body_bytes = self.serializer.serialize_headers_and_body(resp, is_head_request=True)
        hdr_text = hdr_bytes.decode("latin1")

        self.assertEqual(body_bytes, b"")
        self.assertIn("Content-Length: 13\r\n", hdr_text)

    def test_send_response_socket_transmission(self):
        resp = Response.json({"ping": "pong"})
        sent_count = self.serializer.send_response(self.server_sock, resp)

        received = self.client_sock.recv(4096)
        self.assertEqual(len(received), sent_count)
        self.assertIn(b"HTTP/1.1 200 OK", received)
        self.assertIn(b'"ping": "pong"', received)


if __name__ == "__main__":
    unittest.main()
