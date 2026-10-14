"""
WireView HTTP - HTTP Error Definitions
Defines structured protocol exceptions with appropriate RFC status codes.
"""

from typing import Optional, Dict


class HTTPError(Exception):
    """Base class for HTTP protocol and routing exceptions."""

    status_code: int = 500
    reason_phrase: str = "Internal Server Error"

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        reason_phrase: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        stage: str = "parse"
    ):
        if status_code is not None:
            self.status_code = status_code
        if reason_phrase is not None:
            self.reason_phrase = reason_phrase
        self.message = message or self.reason_phrase
        self.headers = headers or {}
        self.stage = stage
        super().__init__(self.message)


class BadRequest(HTTPError):
    status_code = 400
    reason_phrase = "Bad Request"


class NotFound(HTTPError):
    status_code = 404
    reason_phrase = "Not Found"


class MethodNotAllowed(HTTPError):
    status_code = 405
    reason_phrase = "Method Not Allowed"

    def __init__(self, message: Optional[str] = None, allowed_methods: Optional[list] = None):
        headers = {}
        if allowed_methods:
            headers["Allow"] = ", ".join(sorted(allowed_methods))
        super().__init__(
            message=message or "Method Not Allowed",
            headers=headers,
            stage="route"
        )


class PayloadTooLarge(HTTPError):
    status_code = 413
    reason_phrase = "Content Too Large"


class URITooLong(HTTPError):
    status_code = 414
    reason_phrase = "URI Too Long"


class HeaderFieldsTooLarge(HTTPError):
    status_code = 431
    reason_phrase = "Request Header Fields Too Large"


class InternalServerError(HTTPError):
    status_code = 500
    reason_phrase = "Internal Server Error"


class NotImplementedHTTP(HTTPError):
    status_code = 501
    reason_phrase = "Not Implemented"


class ServiceUnavailable(HTTPError):
    status_code = 503
    reason_phrase = "Service Unavailable"


class HTTPVersionNotSupported(HTTPError):
    status_code = 505
    reason_phrase = "HTTP Version Not Supported"


class ConnectionClosedEarly(Exception):
    """Raised when client disconnects before sending complete frame."""
    pass


class ReadTimeout(Exception):
    """Raised when socket read times out."""
    pass
