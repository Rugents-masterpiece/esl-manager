"""HTTP contracts for local designs: persistence, revision checks and auth."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from esl_web.server import create_server


def document():
    return {"schema_version": 1, "name": "Testovací návrh", "model_id": "2.13EPD-BWR",
            "elements": [], "sample_data": {}}


class DraftApiTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.vendor = Mock()
        self.server = create_server("127.0.0.1", 0,
                                    database_path=Path(self.temporary.name) / "draft-api.db",
                                    seed=True, vendor_client=self.vendor, api_token="A" * 64)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.cookie = None

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, method, path, body=None, origin=None):
        headers = {"Content-Type": "application/json"}
        if self.cookie:
            headers["Cookie"] = self.cookie
        if origin:
            headers["Origin"] = origin
        request = Request(self.base + path, method=method, headers=headers,
                          data=json.dumps(body).encode() if body is not None else None)
        try:
            response = urlopen(request, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, response.headers, json.loads(raw) if raw else None

    def login(self):
        status, headers, _ = self.request("POST", "/api/session", {"token": "A" * 64})
        self.assertEqual(status, 200)
        self.cookie = headers["Set-Cookie"].split(";", 1)[0]

    def test_create_is_read_back_as_identical_document_and_listed(self):
        self.login()
        status, _, created = self.request("POST", "/api/template-drafts", document())
        self.assertEqual(status, 201)
        self.assertEqual(created["revision"], 1)
        status, _, loaded = self.request("GET", "/api/template-drafts/" + created["id"])
        self.assertEqual(status, 200)
        self.assertEqual(loaded, created)
        status, _, listed = self.request("GET", "/api/template-drafts")
        self.assertEqual(status, 200)
        self.assertEqual(listed["items"], [created])
        self.assertEqual(created["document"], document())
        self.vendor.assert_not_called()
        self.assertEqual(self.vendor.mock_calls, [])

    def test_update_revision_conflict_preserves_latest_and_delete_requires_revision(self):
        self.login()
        status, _, created = self.request("POST", "/api/template-drafts", document())
        self.assertEqual(status, 201)
        path = "/api/template-drafts/" + created["id"]
        edited = {**document(), "name": "Upravené"}
        status, _, updated = self.request("PUT", path, {"revision": 1, "document": edited})
        self.assertEqual(status, 200)
        self.assertEqual(updated["revision"], 2)
        status, _, _ = self.request("PUT", path, {"revision": 1, "document": document()})
        self.assertEqual(status, 409)
        self.assertEqual(self.request("GET", path)[2]["document"], edited)
        self.assertEqual(self.request("DELETE", path, {"revision": 1})[0], 409)
        self.assertEqual(self.request("DELETE", path, {"revision": 2})[0], 204)
        self.assertEqual(self.request("GET", path)[0], 404)
        actions = [item["action"] for item in self.request("GET", "/api/audit")[2]["items"]]
        for action in ("template_draft.created", "template_draft.updated", "template_draft.deleted"):
            self.assertIn(action, actions)

    def test_mutations_require_session_and_same_origin(self):
        self.assertEqual(self.request("POST", "/api/template-drafts", document())[0], 401)
        self.login()
        self.assertEqual(self.request("POST", "/api/template-drafts", document(),
                                      origin="http://example.invalid")[0], 403)
        self.assertEqual(self.request("GET", "/api/template-drafts")[2], {"items": []})

    def test_invalid_documents_and_nested_routes_are_rejected(self):
        self.login()
        self.assertEqual(self.request("POST", "/api/template-drafts",
                                     {**document(), "model_id": "arbitrary"})[0], 400)
        self.assertEqual(self.request("POST", "/api/template-drafts",
                                     {**document(), "schema_version": True})[0], 400)
        self.assertEqual(self.request("GET", "/api/template-drafts/x/y")[0], 404)
        self.assertEqual(self.request("GET", "/api/template-drafts?controller_id=x")[0], 400)


if __name__ == "__main__":
    unittest.main()
