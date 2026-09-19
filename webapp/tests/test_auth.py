import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from esl_web.server import create_server


class MutationAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.token = "A" * 64
        self.server = create_server(
            "127.0.0.1", 0,
            database_path=Path(self.temporary.name) / "auth.db",
            seed=False,
            api_token=self.token,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, path, body, *, cookie=None, origin=None):
        request = Request(
            self.base + path,
            data=json.dumps(body).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        if cookie:
            request.add_header("Cookie", cookie)
        if origin:
            request.add_header("Origin", origin)
        return urlopen(request, timeout=2)

    def test_mutation_requires_authenticated_session(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/products", {"id": "p1", "sku": "S1", "name": "Test", "price": 1})
        self.assertEqual(caught.exception.code, 401)
        self.assertEqual(json.loads(caught.exception.read())["error"]["code"], "unauthorized")
        caught.exception.close()

    def test_server_rejects_noncanonical_api_token(self):
        with self.assertRaises(ValueError):
            weak_server = create_server(
                "127.0.0.1", 0,
                database_path=Path(self.temporary.name) / "weak.db",
                seed=False,
                api_token="A" * 32,
            )
            weak_server.server_close()

    def test_token_login_issues_hardened_cookie_and_allows_mutation(self):
        with self.assertRaises(HTTPError) as caught:
            self.request("/api/session", {"token": "wrong"})
        self.assertEqual(caught.exception.code, 401)
        caught.exception.close()

        with self.request("/api/session", {"token": self.token}) as response:
            self.assertEqual(response.status, 200)
            cookie = response.headers["Set-Cookie"]
            self.assertIn("HttpOnly", cookie)
            self.assertIn("SameSite=Strict", cookie)
            self.assertIn("Path=/", cookie)
            session_cookie = cookie.split(";", 1)[0]
            self.assertNotIn(self.token, session_cookie)

        with self.request(
            "/api/products",
            {"id": "p1", "sku": "S1", "name": "Test", "price": 1},
            cookie=session_cookie,
            origin=self.base,
        ) as response:
            self.assertEqual(response.status, 201)
            self.assertEqual(json.loads(response.read())["id"], "p1")

    def test_authenticated_mutation_rejects_cross_origin_request(self):
        with self.request("/api/session", {"token": self.token}) as response:
            session_cookie = response.headers["Set-Cookie"].split(";", 1)[0]
        with self.assertRaises(HTTPError) as caught:
            self.request(
                "/api/products",
                {"id": "p2", "sku": "S2", "name": "Test", "price": 1},
                cookie=session_cookie,
                origin="http://evil.invalid",
            )
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()

    def test_authenticated_use_does_not_extend_absolute_session_expiry(self):
        with self.request("/api/session", {"token": self.token}) as response:
            session_cookie = response.headers["Set-Cookie"].split(";", 1)[0]
        session_id = session_cookie.split("=", 1)[1]
        original_expiry = self.server.sessions[session_id]
        with self.request(
            "/api/products",
            {"id": "p-expiry", "sku": "EXP", "name": "Expiry", "price": 1},
            cookie=session_cookie,
            origin=self.base,
        ) as response:
            self.assertEqual(response.status, 201)
        self.assertEqual(self.server.sessions[session_id], original_expiry)

    def test_authenticated_live_dispatch_still_requires_exact_confirmation(self):
        with self.request("/api/session", {"token": self.token}) as response:
            session_cookie = response.headers["Set-Cookie"].split(";", 1)[0]
        previous = os.environ.get("ESL_LIVE_WRITES")
        os.environ["ESL_LIVE_WRITES"] = "1"
        try:
            with self.assertRaises(HTTPError) as caught:
                self.request(
                    "/api/dispatch/live",
                    {"confirmation": "NEPOTVRDENE-TEST"},
                    cookie=session_cookie,
                    origin=self.base,
                )
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
        finally:
            if previous is None:
                os.environ.pop("ESL_LIVE_WRITES", None)
            else:
                os.environ["ESL_LIVE_WRITES"] = previous


if __name__ == "__main__":
    unittest.main()
