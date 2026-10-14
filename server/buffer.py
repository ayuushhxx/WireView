"""
WireView HTTP - Stream Buffer
Low-level byte buffer abstraction over raw TCP sockets.
Handles chunked TCP reads, CRLF line extraction, and exact body reads without losing read-ahead bytes.
"""

import socket
from typing import Optional
from .errors import ConnectionClosedEarly, ReadTimeout, URITooLong, HeaderFieldsTooLarge, PayloadTooLarge


class StreamBuffer:
    """
    Buffered reader around a TCP socket.
    Maintains an in-memory byte buffer so that data read from the socket
    beyond line boundaries or headers is preserved for the request body
    or subsequent pipelined/keep-alive requests.
    """

    def __init__(self, sock: socket.socket, chunk_size: int = 8192):
        self.sock = sock
        self.chunk_size = chunk_size
        self._buf = bytearray()
        self.total_bytes_read = 0

    @property
    def buffered_bytes_count(self) -> int:
        return len(self._buf)

    def read_line(self, max_length: int, is_request_line: bool = False) -> bytes:
        """
        Reads bytes from socket until CRLF (b'\\r\\n') is encountered.
        Returns the line bytes WITHOUT the trailing CRLF.

        If max_length is exceeded before CRLF is reached, raises:
          - URITooLong if is_request_line is True
          - HeaderFieldsTooLarge if reading headers
        """
        delimiter = b"\r\n"
        while True:
            idx = self._buf.find(delimiter)
            if idx != -1:
                if idx > max_length:
                    if is_request_line:
                        raise URITooLong(f"Request line length {idx} exceeds limit {max_length}")
                    else:
                        raise HeaderFieldsTooLarge(f"Header line length {idx} exceeds limit {max_length}")

                line = bytes(self._buf[:idx])
                # Remove line + CRLF delimiter from buffer
                del self._buf[: idx + len(delimiter)]
                return line

            # Check if buffer without delimiter already exceeds max_length
            if len(self._buf) > max_length:
                if is_request_line:
                    raise URITooLong(f"Request line length exceeds limit {max_length}")
                else:
                    raise HeaderFieldsTooLarge(f"Header length exceeds limit {max_length}")

            # Need more data from socket
            try:
                chunk = self.sock.recv(self.chunk_size)
            except socket.timeout:
                raise ReadTimeout("Socket read timed out while waiting for CRLF")
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                raise ConnectionClosedEarly(f"Client disconnected during read: {e}")

            if not chunk:
                # Client closed connection (EOF)
                if not self._buf:
                    raise ConnectionClosedEarly("Connection closed by peer (EOF)")
                # End of stream with leftover bytes that never ended in CRLF
                line = bytes(self._buf)
                self._buf.clear()
                return line

            self.total_bytes_read += len(chunk)
            self._buf.extend(chunk)

    def read_exact(self, count: int, max_limit: Optional[int] = None) -> bytes:
        """
        Reads exactly `count` bytes from the buffer and/or underlying socket.
        Raises PayloadTooLarge if count exceeds max_limit.
        Raises ConnectionClosedEarly if EOF is encountered before reading count bytes.
        """
        if count < 0:
            raise ValueError(f"Negative byte count: {count}")
        if count == 0:
            return b""

        if max_limit is not None and count > max_limit:
            raise PayloadTooLarge(f"Body size {count} exceeds configured limit {max_limit}")

        while len(self._buf) < count:
            needed = count - len(self._buf)
            read_size = max(self.chunk_size, needed)
            try:
                chunk = self.sock.recv(read_size)
            except socket.timeout:
                raise ReadTimeout(f"Socket timed out waiting for {needed} more body bytes")
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                raise ConnectionClosedEarly(f"Client disconnected during body read: {e}")

            if not chunk:
                raise ConnectionClosedEarly(
                    f"Unexpected EOF: expected {count} bytes, but only received {len(self._buf)}"
                )

            self.total_bytes_read += len(chunk)
            self._buf.extend(chunk)

        data = bytes(self._buf[:count])
        del self._buf[:count]
        return data

    def peek(self, count: int = 1) -> bytes:
        """Peek at existing buffered bytes without consuming them."""
        return bytes(self._buf[:count])
