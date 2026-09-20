"""Threaded stdlib REST server for the ESL Manager backend."""

from __future__ import annotations

import csv
import hashlib
import hmac
import ipaddress
import io
import json
import mimetypes
import os
import re
import secrets
import threading
import time
from http.cookies import SimpleCookie
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, unquote, urlsplit

from .controllers import CONTROLLER_ID_PATTERN, ControllerRegistry
from .service import (
    ForbiddenError,
    IntegrationError,
    NotFoundError,
    Service,
    ServiceError,
    UnauthorizedError,
    ValidationError,
)
from .storage import LEGACY_CONTROLLER_ID, Storage
from .vendor import VendorClient, VendorConfig, VendorConfigurationError, live_writes_authorized


API_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{64}")


def is_valid_api_token(value: Any) -> bool:
    """Accept the canonical 64-character encoding produced from 48 random bytes."""
    return isinstance(value, str) and API_TOKEN_PATTERN.fullmatch(value) is not None


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-standard JSON number")


def _is_loopback_address(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


class EslHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], handler, service: Service,
                 vendor_client: VendorClient | None = None,
                 controller_registry: ControllerRegistry | None = None,
                 static_root: Path | None = None,
                 api_token: str | None = None):
        if api_token is not None and not is_valid_api_token(api_token):
            raise ValueError("API token must be a 64-character URL-safe token")
        if vendor_client is not None and controller_registry is not None:
            raise ValueError("vendor_client and controller_registry are mutually exclusive")
        super().__init__(address, handler)
        self.service = service
        self.controller_registry = controller_registry
        self.controller_id = (
            controller_registry.default_id
            if controller_registry is not None else LEGACY_CONTROLLER_ID
        )
        self.vendor_client = (
            controller_registry.get() if controller_registry is not None else vendor_client
        )
        self.api_token_digest = (
            hashlib.sha256(api_token.encode("utf-8")).digest() if api_token is not None else None
        )
        self.sessions: dict[str, float] = {}
        self.session_lock = threading.Lock()
        self.static_root = (static_root or Path(__file__).resolve().parent.parent / "static").resolve()


class ApiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: Any, *, headers: dict[str, str] | None = None) -> None:
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def _error(self, error: ServiceError) -> None:
        self._json(error.status, {
            "error": {"code": error.code, "details": error.details, "message": error.message}
        })

    def _product_csv(self, products: list[dict[str, Any]]) -> None:
        output = io.StringIO(newline="")
        fields = ("id", "sku", "ean", "name", "price", "currency", "template_id", "tag_id")
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for product in products:
            writer.writerow({field: product.get(field) for field in fields})
        content = output.getvalue().encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", "attachment; filename=products.csv")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    @staticmethod
    def _single(query: dict[str, list[str]], name: str) -> str | None:
        values = query.get(name)
        if not values:
            return None
        if len(values) != 1:
            raise ValidationError(f"Query parameter {name} must occur once", details={"field": name})
        return values[0]

    @classmethod
    def _boolean(cls, query: dict[str, list[str]], name: str) -> bool | None:
        value = cls._single(query, name)
        if value is None:
            return None
        if value == "true":
            return True
        if value == "false":
            return False
        raise ValidationError(f"Invalid {name}", details={"field": name})

    def _body(self) -> Any:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValidationError("Content-Type must be application/json")
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length or "")
        except ValueError as error:
            raise ValidationError("Invalid Content-Length") from error
        if length < 0 or length > 1_000_000:
            raise ValidationError("Invalid Content-Length")
        try:
            return json.loads(
                self.rfile.read(length).decode("utf-8"), parse_constant=_reject_json_constant
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValidationError("Malformed JSON") from error

    def _no_content(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _binary_image(self, data: bytes, media_type: str) -> None:
        allowed = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}
        if not isinstance(data, bytes) or not data or media_type not in allowed:
            raise IntegrationError("Vendor image returned invalid data")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; sandbox")
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def _vendor_target(server: EslHTTPServer,
                       query: dict[str, list[str]]) -> tuple[VendorClient | None, str]:
        if set(query) - {"controller_id"}:
            raise ValidationError("Vendor route accepts only controller_id query parameter")
        values = query.get("controller_id")
        if values is None:
            return server.vendor_client, server.controller_id
        if len(values) != 1 or CONTROLLER_ID_PATTERN.fullmatch(values[0]) is None:
            raise ValidationError("Invalid controller_id", details={"field": "controller_id"})
        if server.controller_registry is None:
            raise ValidationError("Explicit controller selection is not configured",
                                  details={"field": "controller_id"})
        controller_id = values[0]
        try:
            return server.controller_registry.get(controller_id), controller_id
        except KeyError as error:
            raise ValidationError("Unknown controller_id",
                                  details={"field": "controller_id"}) from error

    @classmethod
    def _required_vendor_target(cls, server: EslHTTPServer,
                                query: dict[str, list[str]]) -> tuple[VendorClient, str]:
        client, controller_id = cls._vendor_target(server, query)
        if client is None:
            raise IntegrationError("Vendor integration is not configured")
        return client, controller_id

    @staticmethod
    def _clone_targets(server: EslHTTPServer, data: Any,
                       query: dict[str, list[str]]) -> tuple[VendorClient, VendorClient, str, str]:
        required = {
            "source_controller_id", "target_controller_id",
            "source_template_id", "target_name",
        }
        if query or not isinstance(data, dict) or set(data) != required:
            raise ValidationError(
                "JSON body must contain only source_controller_id, target_controller_id, "
                "source_template_id and target_name"
            )
        source_id = data["source_controller_id"]
        target_id = data["target_controller_id"]
        if any(not isinstance(value, str) or CONTROLLER_ID_PATTERN.fullmatch(value) is None
               for value in (source_id, target_id)):
            raise ValidationError("Invalid controller_id", details={"field": "controller_id"})
        if server.controller_registry is None:
            if source_id != LEGACY_CONTROLLER_ID or target_id != LEGACY_CONTROLLER_ID:
                raise ValidationError("Unknown controller_id", details={"field": "controller_id"})
            if server.vendor_client is None:
                raise IntegrationError("Vendor integration is not configured")
            return server.vendor_client, server.vendor_client, source_id, target_id
        try:
            return (
                server.controller_registry.get(source_id),
                server.controller_registry.get(target_id),
                source_id,
                target_id,
            )
        except KeyError as error:
            raise ValidationError("Unknown controller_id",
                                  details={"field": "controller_id"}) from error

    def _session_id(self) -> str | None:
        raw_cookie = self.headers.get("Cookie")
        if not raw_cookie:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(raw_cookie)
        except Exception:
            return None
        morsel = cookie.get("esl_session")
        return morsel.value if morsel is not None else None

    def _require_authenticated_session(self, server: EslHTTPServer) -> None:
        session_id = self._session_id()
        now = time.monotonic()
        with server.session_lock:
            expired = [key for key, expiry in server.sessions.items() if expiry <= now]
            for key in expired:
                server.sessions.pop(key, None)
            expiry = server.sessions.get(session_id or "")
            if expiry is None:
                raise UnauthorizedError("Authentication required")
        origin = self.headers.get("Origin")
        host = self.headers.get("Host")
        if origin and origin not in {f"http://{host}", f"https://{host}"}:
            raise ForbiddenError("Cross-origin API mutation is forbidden")

    def _create_session(self, server: EslHTTPServer) -> None:
        if server.api_token_digest is None:
            raise NotFoundError("Route not found")
        data = self._body()
        token = data.get("token") if isinstance(data, dict) else None
        supplied = hashlib.sha256(token.encode("utf-8")).digest() if isinstance(token, str) else b""
        if not hmac.compare_digest(supplied, server.api_token_digest):
            raise UnauthorizedError("Invalid authentication token")
        session_id = secrets.token_urlsafe(32)
        with server.session_lock:
            expired = [key for key, expiry in server.sessions.items() if expiry <= time.monotonic()]
            for key in expired:
                server.sessions.pop(key, None)
            while len(server.sessions) >= 128:
                server.sessions.pop(next(iter(server.sessions)))
            server.sessions[session_id] = time.monotonic() + 28_800
        self._json(HTTPStatus.OK, {"authenticated": True}, headers={
            "Set-Cookie": (
                f"esl_session={session_id}; Path=/; Max-Age=28800; "
                "HttpOnly; SameSite=Strict"
            )
        })

    def _static_file(self, request_path: str) -> bool:
        """Serve only files contained by the configured static directory."""
        server = cast(EslHTTPServer, self.server)
        relative = "index.html" if request_path == "/" else unquote(request_path).removeprefix("/static/")
        if request_path != "/" and not request_path.startswith("/static/"):
            return False
        candidate = (server.static_root / relative).resolve()
        try:
            candidate.relative_to(server.static_root)
        except ValueError:
            return False
        if not candidate.is_file():
            return False
        content = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if candidate.suffix == ".js":
            content_type = "text/javascript"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)
        return True

    def _mutation(self, method: str) -> None:
        try:
            split = urlsplit(self.path)
            path = split.path.rstrip("/") or "/"
            query = parse_qs(split.query, keep_blank_values=True)
            service = cast(EslHTTPServer, self.server).service
            server = cast(EslHTTPServer, self.server)
            if method == "POST" and path == "/api/session":
                self._create_session(server)
                return
            if server.api_token_digest is not None:
                self._require_authenticated_session(server)
            elif not _is_loopback_address(self.client_address[0]):
                self.close_connection = True
                raise ForbiddenError("API mutations are restricted to the local host")
            if method == "POST" and path == "/api/sync/read-only":
                if self._body() != {}:
                    raise ValidationError("Read-only sync body must be an empty object")
                client, controller_id = self._vendor_target(server, query)
                if client is None:
                    try:
                        client = VendorClient(VendorConfig.from_env())
                    except VendorConfigurationError as error:
                        raise IntegrationError("Vendor integration is not configured") from error
                self._json(HTTPStatus.OK, service.sync_read_only(
                    client, controller_id=controller_id
                ))
            elif method == "POST" and path == "/api/vendor/templates/clone":
                data = self._body()
                source_client, target_client, source_controller_id, target_controller_id = (
                    self._clone_targets(server, data, query)
                )
                self._json(
                    HTTPStatus.CREATED,
                    service.clone_vendor_template(
                        source_client, target_client, data,
                        source_controller_id=source_controller_id,
                        target_controller_id=target_controller_id,
                    ),
                )
            elif method == "POST" and path == "/api/dispatch/live":
                if os.environ.get("ESL_LIVE_WRITES") != "1":
                    self.close_connection = True
                    raise ForbiddenError("Live ESL writes are disabled or not explicitly confirmed")
                try:
                    data = self._body()
                except ValidationError as error:
                    self.close_connection = True
                    raise ForbiddenError(
                        "Live ESL writes are disabled or not explicitly confirmed"
                    ) from error
                client, controller_id = self._vendor_target(server, query)
                confirmation = data.get("confirmation") if isinstance(data, dict) else None
                if client is None and live_writes_authorized(confirmation):
                    try:
                        client = VendorClient(VendorConfig.from_env())
                    except VendorConfigurationError as error:
                        raise IntegrationError("Vendor integration is not configured") from error
                self._json(HTTPStatus.OK, service.dispatch_live(
                    client, data, controller_id=controller_id
                ))
            elif method == "POST" and path == "/api/products":
                self._json(HTTPStatus.CREATED, service.create_product(self._body()))
            elif method == "POST" and path == "/api/tags/staged":
                self._json(HTTPStatus.CREATED, service.create_staged_tag(self._body()))
            elif (method == "PUT" and path.startswith("/api/tags/")
                  and path.endswith("/configuration")):
                tag_id = unquote(
                    path.removeprefix("/api/tags/").removesuffix("/configuration")
                )
                if not tag_id or "/" in tag_id:
                    raise NotFoundError("Route not found")
                self._json(
                    HTTPStatus.OK, service.update_tag_configuration(tag_id, self._body())
                )
            elif method in {"PUT", "PATCH"} and path.startswith("/api/products/"):
                product_id = unquote(path.removeprefix("/api/products/"))
                self._json(HTTPStatus.OK, service.update_product(product_id, self._body()))
            elif method == "DELETE" and path.startswith("/api/products/"):
                service.delete_product(unquote(path.removeprefix("/api/products/")))
                self._no_content()
            elif method == "POST" and path == "/api/bindings":
                data = self._body()
                if not isinstance(data, dict) or set(data) != {"product_id", "tag_id"}:
                    raise ValidationError("JSON body must contain product_id and tag_id")
                self._json(HTTPStatus.CREATED, service.bind_tag(data["product_id"], data["tag_id"]))
            elif method == "DELETE" and path.startswith("/api/bindings/"):
                parts = path.removeprefix("/api/bindings/").split("/")
                if len(parts) != 2:
                    raise NotFoundError("Route not found")
                service.unbind_tag(unquote(parts[0]), unquote(parts[1]))
                self._no_content()
            elif method == "POST" and path == "/api/jobs":
                self._json(HTTPStatus.ACCEPTED, service.queue_bulk_update(self._body()))
            elif method == "POST" and path.startswith("/api/jobs/"):
                parts = path.removeprefix("/api/jobs/").split("/")
                if len(parts) != 2:
                    raise NotFoundError("Route not found")
                job_id, operation = map(unquote, parts)
                if operation == "simulate":
                    self._json(HTTPStatus.OK, service.simulate_job(job_id, self._body()))
                elif operation == "retry":
                    data = self._body()
                    if data != {}:
                        raise ValidationError("Retry body must be an empty object")
                    self._json(HTTPStatus.OK, service.retry_failed_items(job_id))
                else:
                    raise NotFoundError("Route not found")
            else:
                raise NotFoundError("Route not found")
        except ServiceError as error:
            self._error(error)
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": {"code": "internal_error", "details": {}, "message": "Internal server error"}
            })

    def do_POST(self) -> None:  # noqa: N802
        self._mutation("POST")

    def do_PUT(self) -> None:  # noqa: N802
        self._mutation("PUT")

    def do_PATCH(self) -> None:  # noqa: N802
        self._mutation("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._mutation("DELETE")

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        try:
            split = urlsplit(self.path)
            path = split.path.rstrip("/") or "/"
            query = parse_qs(split.query, keep_blank_values=True)
            server = cast(EslHTTPServer, self.server)
            service = server.service
            if path == "/" or path.startswith("/static/"):
                if not self._static_file(split.path):
                    raise NotFoundError("Route not found")
            elif path == "/api/health":
                if os.environ.get("ESL_LIVE_WRITES") == "1":
                    mode = "live"
                else:
                    mode = "read_only" if server.vendor_client is not None else "simulation"
                self._json(HTTPStatus.OK, {"mode": mode, "status": "ok"})
            elif path == "/api/dashboard":
                self._json(HTTPStatus.OK, service.dashboard())
            elif path == "/api/products":
                items = service.list_products(
                    search=self._single(query, "search"), tag_id=self._single(query, "tag_id")
                )
                self._json(HTTPStatus.OK, {"items": items})
            elif path == "/api/products/export.csv":
                self._product_csv(service.list_products(
                    search=self._single(query, "search"), tag_id=self._single(query, "tag_id")
                ))
            elif path.startswith("/api/products/"):
                self._json(HTTPStatus.OK, service.get_product(unquote(path.removeprefix("/api/products/"))))
            elif path == "/api/tags":
                items = service.list_tags(
                    search=self._single(query, "search"),
                    status=self._single(query, "status"),
                    router_id=self._single(query, "router_id"),
                    bound=self._boolean(query, "bound"),
                )
                self._json(HTTPStatus.OK, {"items": items})
            elif path.startswith("/api/tags/"):
                tag_id = unquote(path.removeprefix("/api/tags/"))
                if not tag_id or "/" in tag_id:
                    raise NotFoundError("Route not found")
                self._json(HTTPStatus.OK, service.get_tag(tag_id))
            elif path == "/api/routers":
                self._json(HTTPStatus.OK, {"items": service.list_routers(status=self._single(query, "status"))})
            elif path == "/api/templates":
                self._json(HTTPStatus.OK, {"items": service.list_templates(search=self._single(query, "search"))})
            elif path == "/api/vendor/templates":
                client, _controller_id = self._required_vendor_target(server, query)
                self._json(HTTPStatus.OK, {
                    "items": service.vendor_style_catalog(
                        client, controller_id=_controller_id
                    )
                })
            elif path.startswith("/api/vendor/templates/"):
                parts = path.removeprefix("/api/vendor/templates/").split("/")
                raw_id = unquote(parts[0]) if parts else ""
                if re.fullmatch(r"\d{1,10}", raw_id) is None:
                    raise ValidationError("Invalid style id", details={"field": "style_id"})
                style_id = int(raw_id)
                if style_id > 2_147_483_647:
                    raise ValidationError("Invalid style id", details={"field": "style_id"})
                client, controller_id = self._required_vendor_target(server, query)
                if len(parts) == 1:
                    self._json(HTTPStatus.OK, service.vendor_style_detail(
                        client, style_id, controller_id=controller_id
                    ))
                elif parts == [raw_id, "preview"]:
                    self._binary_image(*service.vendor_template_preview(client, style_id))
                else:
                    raise NotFoundError("Route not found")
            elif path == "/api/vendor/photos":
                client, controller_id = self._required_vendor_target(server, query)
                self._json(HTTPStatus.OK, {
                    "items": service.vendor_photos(
                        client, controller_id=controller_id
                    )
                })
            elif path.startswith("/api/vendor/photos/"):
                parts = path.removeprefix("/api/vendor/photos/").split("/")
                if len(parts) != 2 or parts[1] != "data":
                    raise NotFoundError("Route not found")
                photo_name = unquote(parts[0])
                client, _controller_id = self._required_vendor_target(server, query)
                self._binary_image(*service.vendor_photo_data(
                    client, photo_name
                ))
            elif path == "/api/jobs":
                self._json(HTTPStatus.OK, {"items": service.list_jobs(status=self._single(query, "status"))})
            elif path.startswith("/api/jobs/"):
                self._json(HTTPStatus.OK, service.get_job(unquote(path.removeprefix("/api/jobs/"))))
            elif path == "/api/alerts":
                self._json(HTTPStatus.OK, {"items": service.list_alerts(
                    active=self._boolean(query, "active"),
                    severity=self._single(query, "severity"),
                    kind=self._single(query, "kind"),
                )})
            elif path == "/api/audit":
                raw_limit = self._single(query, "limit")
                try:
                    limit = 100 if raw_limit is None else int(raw_limit)
                except ValueError as error:
                    raise ValidationError("Invalid limit", details={"field": "limit"}) from error
                self._json(HTTPStatus.OK, {"items": service.list_audit(
                    action=self._single(query, "action"), limit=limit
                )})
            else:
                raise NotFoundError("Route not found")
        except ServiceError as error:
            self._error(error)
        except Exception:
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": {"code": "internal_error", "details": {}, "message": "Internal server error"}
            })


def create_server(host: str = "127.0.0.1", port: int = 0, *,
                  database_path: str | Path | None = None, seed: bool = True,
                  service: Service | None = None,
                  vendor_client: VendorClient | None = None,
                  controller_registry: ControllerRegistry | None = None,
                  static_root: str | Path | None = None,
                  api_token: str | None = None) -> EslHTTPServer:
    """Create, but do not start, a threaded API server."""
    if service is None:
        if database_path is None:
            database_path = Path(__file__).resolve().parent.parent / "data" / "esl.db"
        storage = Storage(database_path)
        storage.initialize()
        if seed:
            storage.seed_demo()
        service = Service(storage)
    if controller_registry is not None:
        service.storage.configure_controllers(controller_registry.metadata())
    root = Path(static_root) if static_root is not None else None
    return EslHTTPServer(
        (host, port), ApiHandler, service, vendor_client, controller_registry, root, api_token
    )
