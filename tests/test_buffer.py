"""
Tests for StreamBuffer chunking and boundary detection.
"""

import socket
import unittest
from server.buffer import StreamBuffer
from server.errors import ConnectionClosedEarly, URITooLong, HeaderFieldsTooLarge, PayloadTooLarge


class TestStreamBuffer(unittest.TestCase):

    def setUp(self):
        # Create an interconnected pair of sockets
        self.server_sock, self.client_sock = socket.socketpair()

    def tearDown(self):
        self.server_sock.close()
        self.client_sock.close()

    def test_read_line_single_chunk(self):
        buf = StreamBuffer(self.server_sock)
        self.client_sock.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n")

        line1 = buf.read_line(max_length=1024, is_request_line=True)
        self.assertEqual(line1, b"GET /health HTTP/1.1")

        line2 = buf.read_line(max_length=1024, is_request_line=False)
        self.assertEqual(line2, b"Host: localhost")

        line3 = buf.read_line(max_length=1024, is_request_line=False)
        self.assertEqual(line3, b"")

    def test_read_line_fragmented_byte_by_byte(self):
        buf = StreamBuffer(self.server_sock, chunk_size=1)
        data = b"POST /api/items HTTP/1.1\r\n"

        # Send 1 byte at a time
        for b in data:
            self.client_sock.sendall(bytes([b]))

        line = buf.read_line(max_length=1024, is_request_line=True)
        self.assertEqual(line, b"POST /api/items HTTP/1.1")

    def test_request_line_length_limit(self):
        buf = StreamBuffer(self.server_sock)
        long_line = b"GET /" + (b"a" * 100) + b" HTTP/1.1\r\n"
        self.client_sock.sendall(long_line)

        with self.assertRaises(URITooLong):
            buf.read_line(max_length=50, is_request_line=True)

    def test_read_exact_body(self):
        buf = StreamBuffer(self.server_sock)
        payload = b'{"hello": "world", "number": 42}'
        self.client_sock.sendall(payload)

        read_data = buf.read_exact(len(payload))
        self.assertEqual(read_data, payload)

    def test_read_exact_payload_too_large(self):
        buf = StreamBuffer(self.server_sock)
        with self.assertRaises(PayloadTooLarge):
            buf.read_exact(500, max_limit=100)

    def test_read_exact_premature_eof(self):
        buf = StreamBuffer(self.server_sock)
        self.client_sock.sendall(b"short")
        self.client_sock.close()

        with self.assertRaises(ConnectionClosedEarly):
            buf.read_exact(20)


if __name__ == "__main__":
    unittest.main()
