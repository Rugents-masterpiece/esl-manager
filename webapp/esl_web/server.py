"""Threaded stdlib REST server for the ESL Manager backend."""

from __future__ import annotations

import csv
import ipaddress
import io
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, unquote, urlsplit

from .service import (
    ForbiddenError,
    IntegrationError,
    NotFoundError,
    Service,
    ServiceError,
    ValidationError,
)
from .storage import Storage
from .vendor import VendorClient, VendorConfig, VendorConfigurationError, live_writes_authorized


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
                 static_root: Path | None = None):
        super().__init__(address, handler)
        self.service = service
        self.vendor_client = vendor_client
        self.static_root = (static_root or Path(__file__).resolve().parent.parent / "static").resolve()


class ApiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, status: int, payload: Any) -> None:
        content = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
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
            path = urlsplit(self.path).path.rstrip("/") or "/"
            service = cast(EslHTTPServer, self.server).service
            server = cast(EslHTTPServer, self.server)
            if not _is_loopback_address(self.client_address[0]):
                self.close_connection = True
                raise ForbiddenError("API mutations are restricted to the local host")
            if method == "POST" and path == "/api/sync/read-only":
                if self._body() != {}:
                    raise ValidationError("Read-only sync body must be an empty object")
                client = server.vendor_client
                if client is None:
                    try:
                        client = VendorClient(VendorConfig.from_env())
                    except VendorConfigurationError as error:
                        raise IntegrationError("Vendor integration is not configured") from error
                self._json(HTTPStatus.OK, service.sync_read_only(client))
            elif method == "POST" and path == "/api/dispatch/live":
                if not _is_loopback_address(self.client_address[0]):
                    self.close_connection = True
                    raise ForbiddenError("Live ESL writes are restricted to the local host")
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
                client = server.vendor_client
                confirmation = data.get("confirmation") if isinstance(data, dict) else None
                if client is None and live_writes_authorized(confirmation):
                    try:
                        client = VendorClient(VendorConfig.from_env())
                    except VendorConfigurationError as error:
                        raise IntegrationError("Vendor integration is not configured") from error
                self._json(HTTPStatus.OK, service.dispatch_live(client, data))
            elif method == "POST" and path == "/api/products":
                self._json(HTTPStatus.CREATED, service.create_product(self._body()))
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
            elif path == "/api/routers":
                self._json(HTTPStatus.OK, {"items": service.list_routers(status=self._single(query, "status"))})
            elif path == "/api/templates":
                self._json(HTTPStatus.OK, {"items": service.list_templates(search=self._single(query, "search"))})
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
                  static_root: str | Path | None = None) -> EslHTTPServer:
    """Create, but do not start, a threaded API server."""
    if service is None:
        if database_path is None:
            database_path = Path(__file__).resolve().parent.parent / "data" / "esl.db"
        storage = Storage(database_path)
        storage.initialize()
        if seed:
            storage.seed_demo()
        service = Service(storage)
    root = Path(static_root) if static_root is not None else None
    return EslHTTPServer((host, port), ApiHandler, service, vendor_client, root)
