"""
Tests for URL Router.
Verifies pattern matching, path parameters, 404 Not Found, and 405 Method Not Allowed with Allow headers.
"""

import unittest
from server.errors import MethodNotAllowed, NotFound
from server.models import CaseInsensitiveDict, Request, Response
from server.router import Router


class TestRouter(unittest.TestCase):

    def setUp(self):
        self.router = Router()

        @self.router.get("/api/items")
        def get_items(req: Request) -> Response:
            return Response.json(["item1", "item2"])

        @self.router.post("/api/items")
        def create_item(req: Request) -> Response:
            return Response.json({"created": True}, status_code=201)

        @self.router.get("/api/items/{id}")
        def get_item(req: Request) -> Response:
            return Response.json({"id": req.path_params.get("id")})

    def make_req(self, method: str, path: str) -> Request:
        return Request(
            method=method,
            target=path,
            path=path,
            version="HTTP/1.1",
            headers=CaseInsensitiveDict(),
        )

    def test_exact_route_match(self):
        req = self.make_req("GET", "/api/items")
        handler, params, is_auto_head = self.router.match(req)
        self.assertIsNotNone(handler)
        self.assertEqual(params, {})
        res = handler(req)
        self.assertEqual(res.status_code, 200)

    def test_path_parameter_extraction(self):
        req = self.make_req("GET", "/api/items/42")
        handler, params, is_auto_head = self.router.match(req)
        self.assertEqual(params, {"id": "42"})
        req.path_params = params
        res = handler(req)
        self.assertEqual(res.status_code, 200)

    def test_404_not_found(self):
        req = self.make_req("GET", "/nonexistent/endpoint")
        with self.assertRaises(NotFound):
            self.router.match(req)

    def test_405_method_not_allowed_with_allow_header(self):
        req = self.make_req("DELETE", "/api/items")
        with self.assertRaises(MethodNotAllowed) as ctx:
            self.router.match(req)
        err = ctx.exception
        self.assertEqual(err.status_code, 405)
        self.assertIn("Allow", err.headers)
        self.assertIn("GET", err.headers["Allow"])
        self.assertIn("POST", err.headers["Allow"])

    def test_automatic_options_response(self):
        req = self.make_req("OPTIONS", "/api/items")
        handler, params, is_auto_head = self.router.match(req)
        res = handler(req)
        self.assertEqual(res.status_code, 204)
        self.assertIn("Allow", res.headers)
        self.assertIn("GET", res.headers["Allow"])
        self.assertIn("Access-Control-Allow-Origin", res.headers)


if __name__ == "__main__":
    unittest.main()
