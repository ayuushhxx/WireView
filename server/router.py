"""
WireView HTTP - Pattern-Based Request Router
Handles URL routing, path parameter extraction, query parameter integration,
404 Not Found, 405 Method Not Allowed with RFC Allow headers, and automatic OPTIONS/HEAD dispatch.
"""

from dataclasses import dataclass
import re
from typing import Callable, Dict, List, Optional, Pattern, Set, Tuple

from .errors import MethodNotAllowed, NotFound
from .models import Request, Response

RouteHandler = Callable[[Request], Response]


@dataclass
class Route:
    path_pattern: str
    methods: Set[str]
    handler: RouteHandler
    regex: Pattern
    param_names: List[str]


class Router:
    """
    Pattern-matching HTTP Router supporting static and parametrized paths ({param}).
    """

    def __init__(self):
        self.routes: List[Route] = []

    def add_route(self, path: str, methods: List[str], handler: RouteHandler):
        """Register a new route with supported methods."""
        # Normalize methods to uppercase
        norm_methods = {m.upper() for m in methods}

        # Convert path pattern with {param} into regex
        # e.g. /api/items/{id} -> ^/api/items/(?P<id>[^/]+)$
        param_names: List[str] = []

        def repl(match: re.Match) -> str:
            p_name = match.group(1)
            param_names.append(p_name)
            return f"(?P<{p_name}>[^/]+)"

        regex_pattern = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", repl, path)
        if not regex_pattern.startswith("/"):
            regex_pattern = "/" + regex_pattern
        compiled_regex = re.compile(f"^{regex_pattern}$")

        self.routes.append(
            Route(
                path_pattern=path,
                methods=norm_methods,
                handler=handler,
                regex=compiled_regex,
                param_names=param_names,
            )
        )

    def get(self, path: str):
        def decorator(handler: RouteHandler):
            self.add_route(path, ["GET"], handler)
            return handler
        return decorator

    def post(self, path: str):
        def decorator(handler: RouteHandler):
            self.add_route(path, ["POST"], handler)
            return handler
        return decorator

    def put(self, path: str):
        def decorator(handler: RouteHandler):
            self.add_route(path, ["PUT"], handler)
            return handler
        return decorator

    def delete(self, path: str):
        def decorator(handler: RouteHandler):
            self.add_route(path, ["DELETE"], handler)
            return handler
        return decorator

    def options(self, path: str):
        def decorator(handler: RouteHandler):
            self.add_route(path, ["OPTIONS"], handler)
            return handler
        return decorator

    def match(self, request: Request) -> Tuple[RouteHandler, Dict[str, str], bool]:
        """
        Matches request method and path against registered routes.
        Returns (handler, path_params, is_auto_head).

        Raises:
          - MethodNotAllowed (405) with Allow header if path matches another method
          - NotFound (404) if no path matches
        """
        matching_path_methods: Set[str] = set()
        matched_handler: Optional[RouteHandler] = None
        extracted_params: Dict[str, str] = {}
        is_auto_head = False

        for route in self.routes:
            m = route.regex.match(request.path)
            if m:
                # Path matches! Collect all allowed methods for this path
                matching_path_methods.update(route.methods)

                if request.method in route.methods:
                    matched_handler = route.handler
                    extracted_params = m.groupdict()
                elif request.method == "HEAD" and "GET" in route.methods and matched_handler is None:
                    # RFC 7231: HEAD can be automatically satisfied by GET handler
                    matched_handler = route.handler
                    extracted_params = m.groupdict()
                    is_auto_head = True

        if matched_handler:
            return matched_handler, extracted_params, is_auto_head

        # Path was matched for other methods -> 405 Method Not Allowed
        if matching_path_methods:
            # Automatic OPTIONS response if OPTIONS wasn't explicitly registered
            if request.method == "OPTIONS":
                allowed = sorted(list(matching_path_methods | {"OPTIONS", "HEAD"}))
                def auto_options_handler(req: Request) -> Response:
                    headers = {
                        "Allow": ", ".join(allowed),
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": ", ".join(allowed),
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                    }
                    return Response.no_content(headers=headers)
                return auto_options_handler, {}, False

            allowed = sorted(list(matching_path_methods))
            if "GET" in allowed and "HEAD" not in allowed:
                allowed.append("HEAD")
                allowed.sort()
            raise MethodNotAllowed(
                message=f"Method {request.method} is not allowed for path {request.path}",
                allowed_methods=allowed,
            )

        # No route matched this path -> 404
        raise NotFound(f"No route found for path: {request.path}")
