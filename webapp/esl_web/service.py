"""Validated ESL Manager domain use-cases."""

from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any

from .storage import Storage
from .vendor import live_writes_authorized


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


class ServiceError(Exception):
    code = "service_error"
    status = 400

    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(ServiceError):
    code = "validation_error"
    status = 400


class NotFoundError(ServiceError):
    code = "not_found"
    status = 404


class ConflictError(ServiceError):
    code = "conflict"
    status = 409


class IntegrationError(ServiceError):
    code = "vendor_error"
    status = 502


class ForbiddenError(ServiceError):
    code = "live_writes_forbidden"
    status = 403


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _identifier(value: Any, field: str = "id") -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError(f"Invalid {field}", details={"field": field})
    return value


def _text(value: Any, field: str, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 200:
        raise ValidationError(f"Invalid {field}", details={"field": field})
    return value.strip()


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class Service:
    """Domain service; all mutations are local SQLite operations."""

    PRODUCT_FIELDS = {"sku", "ean", "name", "price", "currency", "template_id"}

    def __init__(self, storage: Storage):
        self.storage = storage

    @staticmethod
    def _audit(connection: sqlite3.Connection, action: str, entity_type: str,
               entity_id: str, details: dict[str, Any] | None = None) -> None:
        connection.execute(
            "INSERT INTO audit_events(action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?)",
            (action, entity_type, entity_id, json.dumps(details or {}, sort_keys=True), _now()),
        )

    def create_product(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValidationError("JSON body must be an object")
        product_id = _identifier(data.get("id") or f"prod-{uuid.uuid4().hex[:12]}")
        unknown = set(data) - self.PRODUCT_FIELDS - {"id"}
        if unknown:
            raise ValidationError("Unknown product fields", details={"fields": sorted(unknown)})
        sku = _text(data.get("sku"), "sku")
        name = _text(data.get("name"), "name")
        ean = _text(data.get("ean"), "ean", required=False)
        currency = _text(data.get("currency", "EUR"), "currency")
        template_id = data.get("template_id")
        if template_id is not None:
            template_id = _identifier(template_id, "template_id")
        price = self._price(data.get("price"))
        now = _now()
        try:
            with self.storage.connection() as connection:
                connection.execute(
                    "INSERT INTO products(id, sku, ean, name, price, currency, template_id, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (product_id, sku, ean, name, price, currency, template_id, now, now),
                )
                self._audit(connection, "product.created", "product", product_id, data)
        except sqlite3.IntegrityError as error:
            raise ConflictError("Product conflicts with an existing record") from error
        return self.get_product(product_id)

    @staticmethod
    def _price(value: Any) -> float:
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            raise ValidationError("Invalid price", details={"field": "price"})
        return round(float(value), 2)

    def get_product(self, product_id: str) -> dict[str, Any]:
        product_id = _identifier(product_id)
        with self.storage.connection() as connection:
            result = _row(connection.execute(
                "SELECT p.*, pt.tag_id FROM products p LEFT JOIN product_tags pt ON pt.product_id = p.id "
                "WHERE p.id = ?", (product_id,)
            ).fetchone())
        if result is None:
            raise NotFoundError("Product not found")
        return result

    def list_products(self, *, search: str | None = None, tag_id: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if search is not None:
            if not isinstance(search, str) or len(search) > 200:
                raise ValidationError("Invalid search", details={"field": "search"})
            clauses.append("(LOWER(p.name) LIKE ? OR LOWER(p.sku) LIKE ? OR LOWER(COALESCE(p.ean, '')) LIKE ?)")
            term = f"%{search.lower()}%"
            values.extend((term, term, term))
        if tag_id is not None:
            clauses.append("pt.tag_id = ?")
            values.append(_identifier(tag_id, "tag_id"))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.storage.connection() as connection:
            rows = connection.execute(
                "SELECT p.*, pt.tag_id FROM products p LEFT JOIN product_tags pt ON pt.product_id = p.id"
                + where + " ORDER BY p.name, p.id", values
            ).fetchall()
        return [dict(row) for row in rows]

    def update_product(self, product_id: str, data: Any) -> dict[str, Any]:
        product_id = _identifier(product_id)
        self.get_product(product_id)
        if not isinstance(data, dict) or not data:
            raise ValidationError("JSON body must be a non-empty object")
        unknown = set(data) - self.PRODUCT_FIELDS
        if unknown:
            raise ValidationError("Unknown product fields", details={"fields": sorted(unknown)})
        values: dict[str, Any] = {}
        for field, value in data.items():
            if field == "price":
                values[field] = self._price(value)
            elif field == "template_id":
                values[field] = None if value is None else _identifier(value, field)
            elif field == "ean":
                values[field] = _text(value, field, required=False)
            else:
                values[field] = _text(value, field)
        values["updated_at"] = _now()
        assignments = ", ".join(f"{field} = ?" for field in values)
        try:
            with self.storage.connection() as connection:
                connection.execute(
                    f"UPDATE products SET {assignments} WHERE id = ?",
                    (*values.values(), product_id),
                )
                self._audit(connection, "product.updated", "product", product_id, data)
        except sqlite3.IntegrityError as error:
            raise ConflictError("Product conflicts with an existing record") from error
        return self.get_product(product_id)

    def delete_product(self, product_id: str) -> None:
        product_id = _identifier(product_id)
        self.get_product(product_id)
        with self.storage.connection() as connection:
            connection.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self._audit(connection, "product.deleted", "product", product_id)

    def get_tag(self, tag_id: str) -> dict[str, Any]:
        tag_id = _identifier(tag_id)
        with self.storage.connection() as connection:
            result = _row(connection.execute(
                "SELECT t.*, pt.product_id FROM tags t LEFT JOIN product_tags pt ON pt.tag_id = t.id WHERE t.id = ?",
                (tag_id,),
            ).fetchone())
        if result is None:
            raise NotFoundError("Tag not found")
        return result

    def list_tags(self, *, search: str | None = None, status: str | None = None,
                  router_id: str | None = None, bound: bool | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if search is not None:
            if not isinstance(search, str) or len(search) > 200:
                raise ValidationError("Invalid search", details={"field": "search"})
            clauses.append("(LOWER(t.mac) LIKE ? OR LOWER(COALESCE(t.label, '')) LIKE ?)")
            term = f"%{search.lower()}%"
            values.extend((term, term))
        if status is not None:
            if status not in {"ready", "updating", "failed", "success"}:
                raise ValidationError("Invalid status", details={"field": "status"})
            clauses.append("t.status = ?")
            values.append(status)
        if router_id is not None:
            clauses.append("t.router_id = ?")
            values.append(_identifier(router_id, "router_id"))
        if bound is not None:
            clauses.append("pt.product_id IS NOT NULL" if bound else "pt.product_id IS NULL")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.storage.connection() as connection:
            rows = connection.execute(
                "SELECT t.*, pt.product_id FROM tags t LEFT JOIN product_tags pt ON pt.tag_id = t.id"
                + where + " ORDER BY t.mac, t.id", values
            ).fetchall()
        return [dict(row) for row in rows]

    def list_routers(self, *, status: str | None = None) -> list[dict[str, Any]]:
        if status is not None and status not in {"online", "offline"}:
            raise ValidationError("Invalid status", details={"field": "status"})
        clause = " WHERE status = ?" if status else ""
        values = (status,) if status else ()
        with self.storage.connection() as connection:
            rows = connection.execute("SELECT * FROM routers" + clause + " ORDER BY name, id", values).fetchall()
        return [dict(row) for row in rows]

    def list_templates(self, *, search: str | None = None) -> list[dict[str, Any]]:
        if search is not None and (not isinstance(search, str) or len(search) > 200):
            raise ValidationError("Invalid search", details={"field": "search"})
        clause = " WHERE LOWER(name) LIKE ?" if search is not None else ""
        values = (f"%{search.lower()}%",) if search is not None else ()
        with self.storage.connection() as connection:
            rows = connection.execute("SELECT * FROM templates" + clause + " ORDER BY name, id", values).fetchall()
        return [dict(row) for row in rows]

    def bind_tag(self, product_id: str, tag_id: str) -> dict[str, str]:
        product_id = _identifier(product_id, "product_id")
        tag_id = _identifier(tag_id, "tag_id")
        self.get_product(product_id)
        self.get_tag(tag_id)
        try:
            with self.storage.connection() as connection:
                connection.execute(
                    "INSERT INTO product_tags(product_id, tag_id, bound_at) VALUES (?, ?, ?)",
                    (product_id, tag_id, _now()),
                )
                self._audit(connection, "tag.bound", "tag", tag_id, {"product_id": product_id})
        except sqlite3.IntegrityError as error:
            raise ConflictError("Tag is already bound") from error
        return {"product_id": product_id, "tag_id": tag_id}

    def unbind_tag(self, product_id: str, tag_id: str) -> None:
        product_id = _identifier(product_id, "product_id")
        tag_id = _identifier(tag_id, "tag_id")
        with self.storage.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM product_tags WHERE product_id = ? AND tag_id = ?", (product_id, tag_id)
            )
            if cursor.rowcount == 0:
                raise NotFoundError("Binding not found")
            self._audit(connection, "tag.unbound", "tag", tag_id, {"product_id": product_id})

    def list_alerts(self, *, active: bool | None = None, severity: str | None = None,
                    kind: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if active is not None:
            if not isinstance(active, bool):
                raise ValidationError("Invalid active", details={"field": "active"})
            clauses.append("active = ?")
            values.append(int(active))
        if severity is not None:
            if severity not in {"info", "warning", "critical"}:
                raise ValidationError("Invalid severity", details={"field": "severity"})
            clauses.append("severity = ?")
            values.append(severity)
        if kind is not None:
            clauses.append("kind = ?")
            values.append(_identifier(kind, "kind"))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.storage.connection() as connection:
            rows = connection.execute("SELECT * FROM alerts" + where + " ORDER BY created_at DESC, id", values).fetchall()
        results = [dict(row) for row in rows]
        for item in results:
            item["active"] = bool(item["active"])
        return results

    def dashboard(self) -> dict[str, int]:
        with self.storage.connection() as connection:
            scalar = lambda sql: connection.execute(sql).fetchone()[0]
            return {
                "products": scalar("SELECT COUNT(*) FROM products"),
                "tags": scalar("SELECT COUNT(*) FROM tags"),
                "bound_tags": scalar("SELECT COUNT(*) FROM product_tags"),
                "routers": scalar("SELECT COUNT(*) FROM routers"),
                "offline_routers": scalar("SELECT COUNT(*) FROM routers WHERE status = 'offline'"),
                "active_alerts": scalar("SELECT COUNT(*) FROM alerts WHERE active = 1"),
                "queued_jobs": scalar("SELECT COUNT(*) FROM jobs WHERE status IN ('queued', 'processing')"),
                "failed_tags": scalar("SELECT COUNT(*) FROM tags WHERE status = 'failed'"),
            }

    def queue_bulk_update(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict) or set(data) != {"product_ids"}:
            raise ValidationError("JSON body must contain only product_ids")
        product_ids = data["product_ids"]
        if not isinstance(product_ids, list) or not product_ids or len(product_ids) > 500:
            raise ValidationError("product_ids must be a non-empty list", details={"field": "product_ids"})
        normalized: list[str] = []
        for value in product_ids:
            product_id = _identifier(value, "product_ids")
            if product_id not in normalized:
                normalized.append(product_id)
        placeholders = ",".join("?" for _ in normalized)
        with self.storage.connection() as connection:
            existing = {row[0] for row in connection.execute(
                f"SELECT id FROM products WHERE id IN ({placeholders})", normalized
            )}
            missing = [value for value in normalized if value not in existing]
            if missing:
                raise NotFoundError("Product not found", details={"product_ids": missing})
            rows = connection.execute(
                f"SELECT product_id, tag_id FROM product_tags WHERE product_id IN ({placeholders}) ORDER BY product_id, tag_id",
                normalized,
            ).fetchall()
            if not rows:
                raise ValidationError("No bound tags for selected products")
            job_id = f"job-{uuid.uuid4().hex[:12]}"
            now = _now()
            connection.execute(
                "INSERT INTO jobs(id, status, requested_at, total_items) VALUES (?, 'queued', ?, ?)",
                (job_id, now, len(rows)),
            )
            for row in rows:
                connection.execute(
                    "INSERT INTO job_items(id, job_id, product_id, tag_id, status, updated_at) "
                    "VALUES (?, ?, ?, ?, 'queued', ?)",
                    (f"item-{uuid.uuid4().hex[:12]}", job_id, row["product_id"], row["tag_id"], now),
                )
            self._audit(connection, "job.queued", "job", job_id, {"product_ids": normalized})
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> dict[str, Any]:
        job_id = _identifier(job_id)
        items: list[sqlite3.Row] = []
        with self.storage.connection() as connection:
            job = _row(connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())
            if job is not None:
                items = connection.execute(
                    "SELECT * FROM job_items WHERE job_id = ? ORDER BY id", (job_id,)
                ).fetchall()
        if job is None:
            raise NotFoundError("Job not found")
        job["items"] = [dict(item) for item in items]
        return job

    def list_jobs(self, *, status: str | None = None) -> list[dict[str, Any]]:
        statuses = {"queued", "processing", "completed", "partial", "failed"}
        if status is not None and status not in statuses:
            raise ValidationError("Invalid status", details={"field": "status"})
        clause = " WHERE status = ?" if status else ""
        values = (status,) if status else ()
        with self.storage.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM jobs" + clause + " ORDER BY requested_at DESC, id", values
            ).fetchall()
        return [dict(row) for row in rows]

    def simulate_job(self, job_id: str, data: Any) -> dict[str, Any]:
        job_id = _identifier(job_id)
        if not isinstance(data, dict) or set(data) - {"fail_tag_ids"}:
            raise ValidationError("JSON body may contain only fail_tag_ids")
        fail_values = data.get("fail_tag_ids", [])
        if not isinstance(fail_values, list) or len(fail_values) > 500:
            raise ValidationError("fail_tag_ids must be a list", details={"field": "fail_tag_ids"})
        fail_tags = {_identifier(value, "fail_tag_ids") for value in fail_values}
        job = self.get_job(job_id)
        if job["status"] not in {"queued", "partial", "failed"}:
            raise ConflictError("Job has no queued items")
        now = _now()
        with self.storage.connection() as connection:
            queued = connection.execute(
                "SELECT id, tag_id FROM job_items WHERE job_id = ? AND status = 'queued' ORDER BY id", (job_id,)
            ).fetchall()
            if not queued:
                raise ConflictError("Job has no queued items")
            connection.execute(
                "UPDATE jobs SET status = 'processing', started_at = COALESCE(started_at, ?) WHERE id = ?",
                (now, job_id),
            )
            for item in queued:
                failed = item["tag_id"] in fail_tags
                status = "failed" if failed else "succeeded"
                error = "Simulated failure" if failed else None
                connection.execute(
                    "UPDATE job_items SET status = ?, attempts = attempts + 1, error = ?, updated_at = ? WHERE id = ?",
                    (status, error, now, item["id"]),
                )
                connection.execute(
                    "UPDATE tags SET status = ? WHERE id = ?", ("failed" if failed else "success", item["tag_id"])
                )
                if failed:
                    alert_id = f"alert-{uuid.uuid4().hex[:12]}"
                    connection.execute(
                        "INSERT INTO alerts(id, kind, severity, entity_type, entity_id, message, active, created_at) "
                        "VALUES (?, 'failed_update', 'critical', 'tag', ?, 'Simulated update failed', 1, ?)",
                        (alert_id, item["tag_id"], now),
                    )
            succeeded, failed = connection.execute(
                "SELECT SUM(status = 'succeeded'), SUM(status = 'failed') FROM job_items WHERE job_id = ?", (job_id,)
            ).fetchone()
            total = job["total_items"]
            final_status = "completed" if succeeded == total else ("failed" if failed == total else "partial")
            connection.execute(
                "UPDATE jobs SET status = ?, completed_at = ?, succeeded_items = ?, failed_items = ? WHERE id = ?",
                (final_status, now, succeeded or 0, failed or 0, job_id),
            )
            self._audit(connection, "job.simulated", "job", job_id, {"failed_items": failed or 0})
        return self.get_job(job_id)

    def retry_failed_items(self, job_id: str) -> dict[str, Any]:
        job_id = _identifier(job_id)
        self.get_job(job_id)
        with self.storage.connection() as connection:
            cursor = connection.execute(
                "UPDATE job_items SET status = 'queued', error = NULL, updated_at = ? "
                "WHERE job_id = ? AND status = 'failed'", (_now(), job_id)
            )
            if cursor.rowcount == 0:
                raise ConflictError("Job has no failed items")
            connection.execute(
                "UPDATE jobs SET status = 'queued', completed_at = NULL, failed_items = 0 WHERE id = ?", (job_id,)
            )
            self._audit(connection, "job.retried", "job", job_id, {"items": cursor.rowcount})
        return self.get_job(job_id)

    def list_audit(self, *, action: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise ValidationError("Invalid limit", details={"field": "limit"})
        clause = " WHERE action = ?" if action else ""
        values: tuple[Any, ...] = (action, limit) if action else (limit,)
        with self.storage.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events" + clause + " ORDER BY id DESC LIMIT ?", values
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item["details"])
            results.append(item)
        return results

    @staticmethod
    def _vendor_integer(item: dict[str, Any], field: str, *, minimum: int | None = None,
                        maximum: int | None = None) -> int:
        return Service._vendor_integer_value(
            item.get(field), field, minimum=minimum, maximum=maximum
        )

    @staticmethod
    def _vendor_integer_value(value: Any, field: str, *, minimum: int | None = None,
                              maximum: int | None = None) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise IntegrationError(f"Invalid vendor field: {field}")
        if isinstance(value, float) and not math.isfinite(value):
            raise IntegrationError(f"Invalid vendor field: {field}")
        if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()) is None:
            raise IntegrationError(f"Invalid vendor field: {field}")
        try:
            number = int(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise IntegrationError(f"Invalid vendor field: {field}") from error
        if isinstance(value, float) and not value.is_integer():
            raise IntegrationError(f"Invalid vendor field: {field}")
        if (number < -(2**63) or number > 2**63 - 1
                or (minimum is not None and number < minimum)
                or (maximum is not None and number > maximum)):
            raise IntegrationError(f"Invalid vendor field: {field}")
        return number

    @staticmethod
    def _vendor_id(value: Any, field: str) -> str:
        if value is None or isinstance(value, bool):
            raise IntegrationError(f"Invalid vendor field: {field}")
        try:
            return _identifier(str(value), field)
        except ValidationError as error:
            raise IntegrationError(f"Invalid vendor field: {field}") from error

    def upsert_vendor_router(self, connection: sqlite3.Connection, item: dict[str, Any]) -> None:
        router_value = item.get("routerID")
        if router_value is None:
            router_value = item.get("mac") or item.get("id")
        router_id = self._vendor_id(router_value, "routerID")
        address = _text(item.get("routerIP") or item.get("ip"), "routerIP")
        heartbeat = item.get("lastHeartbeatTime")
        last_seen = None
        if heartbeat is not None:
            milliseconds = self._vendor_integer(item, "lastHeartbeatTime", minimum=0)
            try:
                last_seen = datetime.fromtimestamp(milliseconds / 1000, UTC).isoformat(
                    timespec="seconds"
                ).replace("+00:00", "Z")
            except (OverflowError, OSError, ValueError) as error:
                raise IntegrationError("Invalid vendor field: lastHeartbeatTime") from error
        state = item.get("state")
        online = state is True or str(state).lower() in {"1", "true", "online"}
        description = item.get("description")
        if description in (None, "", "null"):
            description = item.get("shopName")
        self.storage.upsert_router(connection, {
            "id": router_id,
            "name": _text(description, "description", required=False) or f"Router {router_id}",
            "address": address,
            "status": "online" if online else "offline",
            "last_seen_at": last_seen,
        })

    def upsert_vendor_template(self, connection: sqlite3.Connection, item: dict[str, Any]) -> None:
        template_id = self._vendor_id(item.get("id"), "id")
        name = _text(item.get("name") or item.get("descriptor"), "name")
        occupied_names = {
            row["name"] for row in connection.execute(
                "SELECT name FROM templates WHERE id <> ?", (template_id,)
            ).fetchall()
        }
        if name in occupied_names:
            candidate = f"{name} ({template_id})"
            suffix = 2
            while candidate in occupied_names:
                candidate = f"{name} ({template_id}-{suffix})"
                suffix += 1
            name = candidate
        width = item.get("width")
        height = item.get("height")
        if width is None or height is None:
            dimensions = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", str(item.get("styleLen") or ""))
            if dimensions is None:
                raise IntegrationError("Invalid vendor field: styleLen")
            width, height = dimensions.groups()
        self.storage.upsert_template(connection, {
            "id": template_id,
            "name": name,
            "width": self._vendor_integer_value(width, "width", minimum=1),
            "height": self._vendor_integer_value(height, "height", minimum=1),
            "mapping_type": self._vendor_integer_value(
                item.get("mappingtype", 0), "mappingtype", minimum=0
            ),
        })

    def upsert_vendor_tag(self, connection: sqlite3.Connection, item: dict[str, Any],
                          router_ids: set[str], template_ids: set[str],
                          template_names: dict[str, str]) -> None:
        mac = _text(item.get("mac"), "mac")
        tag_id = self._vendor_id(mac, "mac")
        router_value = item.get("routerid")
        if router_value is None:
            router_value = item.get("routerMac")
        router_id = None if router_value in (None, "", 0, "0") else self._vendor_id(router_value, "routerid")
        if router_id not in router_ids:
            router_id = None
        template_value = item.get("styleId")
        if template_value in (None, "", 0, "0"):
            template_value = template_names.get(str(item.get("styleName") or ""))
        template_id = None if template_value in (None, "", 0, "0") else self._vendor_id(template_value, "styleId")
        if template_id not in template_ids:
            template_id = None
        if "updateProgress" in item:
            status_field = "updateProgress"
        elif "status" in item:
            status_field = "status"
        else:
            status_field = "updateProgress"
            item = {**item, "updateProgress": 1}
        status_number = self._vendor_integer(item, status_field)
        statuses = {0: "ready", 1: "ready", 2: "updating", 3: "failed", 4: "success", 5: "ready"}
        if status_number not in statuses:
            raise IntegrationError(f"Invalid vendor field: {status_field}")
        status_value = statuses[status_number]
        label_value = item.get("showStyle") or item.get("name") or item.get("styleName")
        label = _text(label_value, "showStyle", required=False) if label_value else None
        self.storage.upsert_tag(connection, {
            "id": tag_id,
            "mac": mac,
            "label": label,
            "width": self._vendor_integer_value(item.get("width", 1), "width", minimum=1),
            "height": self._vendor_integer_value(item.get("height", 1), "height", minimum=1),
            "battery": self._vendor_integer(item, "power", minimum=0, maximum=100),
            "rssi": self._vendor_integer_value(item.get("rssi", -100), "rssi"),
            "status": status_value,
            "router_id": router_id,
            "template_id": template_id,
            "last_seen_at": _now(),
        })

    def sync_read_only(self, client: Any) -> dict[str, dict[str, int]]:
        """Fetch approved read-only collections and atomically upsert local inventory."""
        try:
            routers = client.get_routers()
            templates = client.get_templates()
            tags = client.get_tags()
        except Exception as error:
            raise IntegrationError("Vendor read-only sync failed") from error
        if any(not isinstance(collection, list) for collection in (routers, templates, tags)):
            raise IntegrationError("Vendor read-only sync returned invalid data")
        with self.storage.connection() as connection:
            for item in routers:
                self.upsert_vendor_router(connection, item)
            for item in templates:
                self.upsert_vendor_template(connection, item)
            router_ids = {
                str(item.get("routerID") if item.get("routerID") is not None else item.get("mac") or item.get("id"))
                for item in routers
            }
            template_ids = {str(item.get("id")) for item in templates}
            template_names: dict[str, str] = {}
            for item in templates:
                template_names.setdefault(
                    str(item.get("name") or item.get("descriptor")), str(item.get("id"))
                )
            for item in tags:
                self.upsert_vendor_tag(connection, item, router_ids, template_ids, template_names)
            counts = {"routers": len(routers), "templates": len(templates), "tags": len(tags)}
            self._audit(connection, "vendor.sync.read_only", "system", "vendor", counts)
        return {"synced": counts}

    def dispatch_live(self, client: Any, data: Any) -> dict[str, Any]:
        """Validate, double-gate and read-back a physical updateScreen dispatch."""
        confirmation = data.get("confirmation") if isinstance(data, dict) else None
        if not live_writes_authorized(confirmation):
            raise ForbiddenError("Live ESL writes are disabled or not explicitly confirmed")
        if not isinstance(data, dict) or set(data) != {"confirmation", "updates"}:
            raise ValidationError("JSON body must contain only confirmation and updates")
        updates = data["updates"]
        if not isinstance(updates, list) or not updates or len(updates) > 500:
            raise ValidationError("updates must be a non-empty list", details={"field": "updates"})
        macs: set[str] = set()
        for update in updates:
            if not isinstance(update, dict):
                raise ValidationError("Each update must be an object", details={"field": "updates"})
            required = {"mac", "styleid", "mappingtype", "ABDisplayFlag"}
            if not required.issubset(update):
                raise ValidationError("Each update requires mac, styleid, mappingtype and ABDisplayFlag")
            if any(not isinstance(key, str) or len(key) > 200 for key in update):
                raise ValidationError("Invalid update field name")
            mac = _text(update["mac"], "mac")
            assert mac is not None
            if mac in macs:
                raise ValidationError("Duplicate update mac", details={"field": "mac"})
            macs.add(mac)
            try:
                self._vendor_integer(update, "styleid", minimum=0)
                self._vendor_integer(update, "mappingtype", minimum=0)
                display_flag = self._vendor_integer(update, "ABDisplayFlag")
            except IntegrationError as error:
                raise ValidationError(error.message) from error
            if display_flag not in {161, 162, 163}:
                raise ValidationError("Invalid ABDisplayFlag", details={"field": "ABDisplayFlag"})
        try:
            verified = client.update_screen(updates, confirmation)
        except Exception as error:
            raise IntegrationError("Vendor display update failed or could not be verified") from error
        verified_tags = [
            {"mac": item["mac"], "status": item["_verified_status"]}
            for item in verified
        ]
        with self.storage.connection() as connection:
            for item in verified_tags:
                connection.execute("UPDATE tags SET status = ? WHERE mac = ?", (item["status"], item["mac"]))
            self._audit(connection, "vendor.update_screen", "tag", ",".join(sorted(macs)), {
                "count": len(updates), "verified_tags": verified_tags,
            })
        return {"dispatched": len(updates), "verified_tags": verified_tags}
