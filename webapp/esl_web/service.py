"""Validated ESL Manager domain use-cases."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from .storage import LEGACY_CONTROLLER_ID, SUPPORTED_DEVICE_MODELS, Storage
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


class UnauthorizedError(ServiceError):
    code = "unauthorized"
    status = 401


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
    """Domain service for validated local and explicitly exposed vendor operations."""

    PRODUCT_FIELDS = {"sku", "ean", "name", "price", "currency", "template_id"}
    CLONE_SOURCES = {145: 9, 147: 8, 149: 2}
    TAG_CONFIGURATION_FIELDS = {
        "controller_id", "mac", "label", "device_model_id", "width", "height",
        "router_id", "template_id", "test_data",
    }
    TAG_DETAIL_SELECT = """
        SELECT t.*, pt.product_id,
               c.name AS controller_name, c.is_default AS controller_is_default,
               r.name AS router_name, r.address AS router_address,
               r.status AS router_status_name, r.last_seen_at AS router_last_seen_at,
               dm.name AS model_name, dm.width AS model_width, dm.height AS model_height,
               dm.alignment_id AS model_alignment_id, dm.screen_type AS model_screen_type,
               tpl.name AS template_name, tpl.width AS template_width,
               tpl.height AS template_height, tpl.mapping_type AS template_mapping_type,
               tpl.style_fields AS template_style_fields,
               tpl.controller_id AS template_controller_id
          FROM tags t
          LEFT JOIN product_tags pt ON pt.tag_id = t.id
          JOIN controllers c ON c.id = t.controller_id
          LEFT JOIN routers r ON r.id = t.router_id
          LEFT JOIN device_models dm ON dm.id = t.device_model_id
          LEFT JOIN templates tpl ON tpl.id = t.template_id
    """

    def __init__(self, storage: Storage):
        self.storage = storage

    @staticmethod
    def _tag_result(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["controller"] = {
            "id": item["controller_id"], "name": item.pop("controller_name"),
            "is_default": bool(item.pop("controller_is_default")),
        }
        item["rf_router"] = None if item["router_id"] is None else {
            "id": item["router_id"], "name": item.pop("router_name"),
            "address": item.pop("router_address"), "status": item.pop("router_status_name"),
            "last_seen_at": item.pop("router_last_seen_at"),
        }
        if item["router_id"] is None:
            for field in ("router_name", "router_address", "router_status_name", "router_last_seen_at"):
                item.pop(field)
        model_fields = {
            "name": item.pop("model_name"), "width": item.pop("model_width"),
            "height": item.pop("model_height"),
            "alignment_id": item.pop("model_alignment_id"),
            "screen_type": item.pop("model_screen_type"),
        }
        expected_dimensions = SUPPORTED_DEVICE_MODELS.get(item["device_model_id"])
        model_supported = (
            expected_dimensions is not None
            and expected_dimensions == (item["width"], item["height"])
            and expected_dimensions == (model_fields["width"], model_fields["height"])
        )
        item["device_model"] = (
            {"id": item["device_model_id"], **model_fields} if model_supported else None
        )
        item["device_model_state"] = "supported" if model_supported else "unsupported"
        item["management_supported"] = model_supported

        template_fields = {
            "name": item.pop("template_name"), "width": item.pop("template_width"),
            "height": item.pop("template_height"),
            "mapping_type": item.pop("template_mapping_type"),
        }
        template_controller_id = item.pop("template_controller_id")
        raw_style_fields = item.pop("template_style_fields")
        template_compatible = (
            item["template_id"] is not None and model_supported
            and template_controller_id == item["controller_id"]
            and (template_fields["width"], template_fields["height"])
            == expected_dimensions
        )
        if template_compatible:
            try:
                style_fields = json.loads(raw_style_fields or "[]")
            except json.JSONDecodeError as error:
                raise IntegrationError("Stored tag configuration is invalid") from error
            if (not isinstance(style_fields, list)
                    or any(not isinstance(field, str) for field in style_fields)):
                raise IntegrationError("Stored tag configuration is invalid")
            item["compatible_template"] = {
                "id": item["template_id"], **template_fields, "style_fields": style_fields,
            }
            item["template_compatibility"] = "compatible"
        else:
            item["compatible_template"] = None
            item["template_compatibility"] = (
                "unassigned" if item["template_id"] is None else "incompatible"
            )
        try:
            test_data = json.loads(item.get("test_data") or "{}")
        except json.JSONDecodeError as error:
            raise IntegrationError("Stored tag configuration is invalid") from error
        if not isinstance(test_data, dict):
            raise IntegrationError("Stored tag configuration is invalid")
        item["test_data"] = test_data
        item["staged"] = item.get("inventory_source") == "local"
        return item

    @staticmethod
    def _normalized_mac(value: Any) -> str:
        if not isinstance(value, str):
            raise ValidationError("Invalid mac", details={"field": "mac"})
        compact = re.sub(r"[:.\-]", "", value.strip())
        if re.fullmatch(r"[0-9A-Fa-f]{12}", compact) is None:
            raise ValidationError("Invalid mac", details={"field": "mac"})
        return ":".join(compact[index:index + 2] for index in range(0, 12, 2)).upper()

    @staticmethod
    def _test_data(value: Any) -> str:
        if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
            raise ValidationError("Invalid test_data", details={"field": "test_data"})
        try:
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValidationError("Invalid test_data", details={"field": "test_data"}) from error
        if len(encoded.encode("utf-8")) > 65_536:
            raise ValidationError("Invalid test_data", details={"field": "test_data"})
        return encoded

    @staticmethod
    def _tag_dependencies(connection: sqlite3.Connection, data: dict[str, Any]) -> tuple[str, int, int, str, str]:
        controller_id = _identifier(data.get("controller_id"), "controller_id")
        if connection.execute(
                "SELECT 1 FROM controllers WHERE id = ?", (controller_id,)
        ).fetchone() is None:
            raise ValidationError("Unknown controller_id", details={"field": "controller_id"})
        model_id = _identifier(data.get("device_model_id"), "device_model_id")
        if model_id not in SUPPORTED_DEVICE_MODELS:
            raise ValidationError("Unsupported device_model_id",
                                  details={"field": "device_model_id"})
        model = connection.execute(
            "SELECT width, height FROM device_models WHERE id = ?", (model_id,)
        ).fetchone()
        if model is None:
            raise ValidationError("Unsupported device_model_id",
                                  details={"field": "device_model_id"})
        width, height = data.get("width"), data.get("height")
        if (isinstance(width, bool) or isinstance(height, bool)
                or not isinstance(width, int) or not isinstance(height, int)
                or (width, height) != SUPPORTED_DEVICE_MODELS[model_id]
                or tuple(model) != SUPPORTED_DEVICE_MODELS[model_id]):
            raise ValidationError("Dimensions do not match device model",
                                  details={"fields": ["width", "height"]})
        router_id = _identifier(data.get("router_id"), "router_id")
        if connection.execute(
                "SELECT 1 FROM routers WHERE id = ? AND controller_id = ?",
                (router_id, controller_id),
        ).fetchone() is None:
            raise ValidationError("Router does not belong to controller",
                                  details={"field": "router_id"})
        template_id = _identifier(data.get("template_id"), "template_id")
        template = connection.execute(
            "SELECT width, height FROM templates WHERE id = ? AND controller_id = ?",
            (template_id, controller_id),
        ).fetchone()
        if template is None:
            raise ValidationError("Template does not belong to controller",
                                  details={"field": "template_id"})
        if tuple(template) != (width, height):
            raise ValidationError("Template dimensions do not match device model",
                                  details={"field": "template_id"})
        return controller_id, width, height, router_id, template_id

    def create_staged_tag(self, data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ValidationError("JSON body must be an object")
        unknown = set(data) - self.TAG_CONFIGURATION_FIELDS - {"id"}
        if unknown:
            raise ValidationError("Unknown tag fields", details={"fields": sorted(unknown)})
        required = self.TAG_CONFIGURATION_FIELDS - {"label", "test_data"}
        missing = sorted(required - set(data))
        if missing:
            raise ValidationError("Missing tag fields", details={"fields": missing})
        tag_id = _identifier(data.get("id") or f"tag-{uuid.uuid4().hex[:12]}")
        mac = self._normalized_mac(data.get("mac"))
        label = _text(data.get("label"), "label", required=False)
        test_data = self._test_data(data.get("test_data", {}))
        try:
            with self.storage.connection() as connection:
                controller_id, width, height, router_id, template_id = self._tag_dependencies(
                    connection, data
                )
                if connection.execute(
                        "SELECT 1 FROM tags WHERE controller_id = ? AND UPPER(mac) = ?",
                        (controller_id, mac),
                ).fetchone() is not None:
                    raise ConflictError("Tag MAC already exists on controller")
                connection.execute(
                    "INSERT INTO tags(id, controller_id, vendor_id, mac, label, width, height, "
                    "battery, rssi, status, router_id, template_id, device_model_id, "
                    "inventory_source, configuration_source, test_data) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 100, 0, 'ready', ?, ?, ?, 'local', 'local', ?)",
                    (tag_id, controller_id, f"local:{tag_id}", mac, label, width, height,
                     router_id, template_id, data["device_model_id"], test_data),
                )
                self._audit(connection, "tag.staged", "tag", tag_id, {
                    "controller_id": controller_id, "mac": mac,
                })
        except sqlite3.IntegrityError as error:
            raise ConflictError("Tag conflicts with an existing record") from error
        return self.get_tag(tag_id)

    def update_tag_configuration(self, tag_id: str, data: Any) -> dict[str, Any]:
        tag_id = _identifier(tag_id, "tag_id")
        if not isinstance(data, dict) or not data:
            raise ValidationError("JSON body must be a non-empty object")
        unknown = set(data) - self.TAG_CONFIGURATION_FIELDS
        if unknown:
            raise ValidationError("Unknown tag fields", details={"fields": sorted(unknown)})
        required = self.TAG_CONFIGURATION_FIELDS - {"label", "test_data"}
        missing = sorted(required - set(data))
        if missing:
            raise ValidationError("Missing tag fields", details={"fields": missing})
        mac = self._normalized_mac(data.get("mac"))
        label = _text(data.get("label"), "label", required=False)
        test_data = self._test_data(data.get("test_data", {}))
        try:
            with self.storage.connection() as connection:
                existing = connection.execute(
                    "SELECT controller_id, inventory_source FROM tags WHERE id = ?", (tag_id,)
                ).fetchone()
                if existing is None:
                    raise NotFoundError("Tag not found")
                controller_id, width, height, router_id, template_id = self._tag_dependencies(
                    connection, data
                )
                if controller_id != existing["controller_id"]:
                    raise ValidationError("Tag controller cannot be changed",
                                          details={"field": "controller_id"})
                if connection.execute(
                        "SELECT 1 FROM tags WHERE controller_id = ? AND UPPER(mac) = ? AND id <> ?",
                        (controller_id, mac, tag_id),
                ).fetchone() is not None:
                    raise ConflictError("Tag MAC already exists on controller")
                connection.execute(
                    "UPDATE tags SET mac = ?, label = ?, width = ?, height = ?, router_id = ?, "
                    "template_id = ?, device_model_id = ?, test_data = ?, "
                    "configuration_source = 'local' WHERE id = ?",
                    (mac, label, width, height, router_id, template_id,
                     data["device_model_id"], test_data, tag_id),
                )
                self._audit(connection, "tag.configuration.updated", "tag", tag_id, {
                    "controller_id": controller_id, "mac": mac,
                    "inventory_source": existing["inventory_source"],
                })
        except sqlite3.IntegrityError as error:
            raise ConflictError("Tag conflicts with an existing record") from error
        return self.get_tag(tag_id)

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
            row = connection.execute(
                self.TAG_DETAIL_SELECT + " WHERE t.id = ?",
                (tag_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError("Tag not found")
        return self._tag_result(row)

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
                self.TAG_DETAIL_SELECT
                + where + " ORDER BY t.mac, t.id", values
            ).fetchall()
        results = [self._tag_result(row) for row in rows]
        return [item for item in results if item["management_supported"]]

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
        results = []
        for row in rows:
            item = dict(row)
            try:
                fields = json.loads(item.get("style_fields") or "[]")
            except json.JSONDecodeError as error:
                raise IntegrationError("Stored template fields are invalid") from error
            if not isinstance(fields, list) or any(not isinstance(field, str) for field in fields):
                raise IntegrationError("Stored template fields are invalid")
            item["style_fields"] = fields
            results.append(item)
        return results

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

    @staticmethod
    def _vendor_text(value: Any, field: str, *, required: bool = True) -> str | None:
        try:
            return _text(value, field, required=required)
        except ValidationError as error:
            raise IntegrationError(f"Invalid vendor field: {field}") from error

    @staticmethod
    def _optional_vendor_integer(value: Any, field: str, *, minimum: int | None = None,
                                 maximum: int | None = None) -> int | None:
        if value is None:
            return None
        return Service._vendor_integer_value(value, field, minimum=minimum, maximum=maximum)

    def _normalize_vendor_style(self, item: Any, *, detail: bool = False,
                                controller_id: str = LEGACY_CONTROLLER_ID) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise IntegrationError("Invalid vendor style response")
        style_id = self._vendor_id(item.get("id"), "id")
        fields_value = item.get("styleFileds", [])
        if (not isinstance(fields_value, list) or len(fields_value) > 100
                or any(not isinstance(field, str) or not field.strip() or len(field.strip()) > 100
                       or any(ord(character) < 32 for character in field)
                       for field in fields_value)):
            raise IntegrationError("Invalid vendor field: styleFileds")
        result = {
            "id": style_id,
            "name": self._vendor_text(item.get("name") or item.get("descriptor"), "name"),
            "descriptor": self._vendor_text(item.get("descriptor"), "descriptor", required=False),
            "width": self._vendor_integer(item, "width", minimum=1),
            "height": self._vendor_integer(item, "height", minimum=1),
            "mapping_type": self._vendor_integer_value(
                item.get("mappingtype", 0), "mappingtype", minimum=0
            ),
            "screen_type": self._optional_vendor_integer(item.get("type"), "type", minimum=0),
            "background_id": self._optional_vendor_integer(
                item.get("backgroundId", item.get("backgroundID")), "backgroundId", minimum=0
            ),
            "vendor_updated_at": self._vendor_text(
                item.get("updatetime", item.get("updateTime")), "updateTime", required=False
            ),
            "style_fields": [field.strip() for field in fields_value],
            "rotate": self._optional_vendor_integer(item.get("rotate"), "rotate"),
            "user_id": self._optional_vendor_integer(item.get("userid"), "userid", minimum=0),
            "preview_url": (
                f"/api/vendor/templates/{style_id}/preview"
                + ("" if controller_id == LEGACY_CONTROLLER_ID
                   else f"?controller_id={quote(controller_id, safe='')}")
            ),
        }
        if not detail:
            result.pop("rotate")
            result.pop("user_id")
        return result

    def _normalize_vendor_photo(self, item: Any,
                                controller_id: str = LEGACY_CONTROLLER_ID) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise IntegrationError("Invalid vendor photo response")
        photo_id = self._vendor_id(item.get("id"), "id")
        name = self._vendor_text(item.get("name"), "name")
        assert name is not None
        if any(character in "/\\?#" or ord(character) < 32 for character in name):
            raise IntegrationError("Invalid vendor field: name")
        return {
            "id": photo_id,
            "name": name,
            "width": self._vendor_integer(item, "width", minimum=1),
            "height": self._vendor_integer(item, "height", minimum=1),
            "data_url": (
                f"/api/vendor/photos/{quote(name, safe='')}/data"
                + ("" if controller_id == LEGACY_CONTROLLER_ID
                   else f"?controller_id={quote(controller_id, safe='')}")
            ),
        }

    def upsert_vendor_router(self, connection: sqlite3.Connection, item: dict[str, Any],
                             controller_id: str = LEGACY_CONTROLLER_ID) -> None:
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
        }, controller_id=controller_id)

    def upsert_vendor_template(self, connection: sqlite3.Connection, item: dict[str, Any],
                               controller_id: str = LEGACY_CONTROLLER_ID) -> None:
        template_id = self._vendor_id(item.get("id"), "id")
        name = self._vendor_text(item.get("name") or item.get("descriptor"), "name")
        local_id = self.storage.local_id(
            connection, "template", controller_id, template_id
        )
        occupied_names = {
            row["name"] for row in connection.execute(
                "SELECT name FROM templates WHERE controller_id = ? AND id <> ?",
                (controller_id, local_id),
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
        style_fields = item.get("styleFileds", [])
        if (not isinstance(style_fields, list) or len(style_fields) > 100
                or any(not isinstance(field, str) or not field.strip() or len(field.strip()) > 100
                       or any(ord(character) < 32 for character in field)
                       for field in style_fields)):
            raise IntegrationError("Invalid vendor field: styleFileds")
        self.storage.upsert_template(connection, {
            "id": template_id,
            "name": name,
            "width": self._vendor_integer_value(width, "width", minimum=1),
            "height": self._vendor_integer_value(height, "height", minimum=1),
            "mapping_type": self._vendor_integer_value(
                item.get("mappingtype", 0), "mappingtype", minimum=0
            ),
            "descriptor": self._vendor_text(item.get("descriptor"), "descriptor", required=False),
            "screen_type": self._optional_vendor_integer(item.get("type"), "type", minimum=0),
            "background_id": self._optional_vendor_integer(
                item.get("backgroundId", item.get("backgroundID")), "backgroundId", minimum=0
            ),
            "vendor_updated_at": self._vendor_text(
                item.get("updatetime", item.get("updateTime")), "updateTime", required=False
            ),
            "style_fields": [field.strip() for field in style_fields],
            "rotate": self._optional_vendor_integer(item.get("rotate"), "rotate"),
            "user_id": self._optional_vendor_integer(item.get("userid"), "userid", minimum=0),
        }, controller_id=controller_id)

    def upsert_vendor_tag(self, connection: sqlite3.Connection, item: dict[str, Any],
                          router_ids: set[str], template_ids: set[str],
                          template_names: dict[str, str],
                          controller_id: str = LEGACY_CONTROLLER_ID) -> None:
        mac = self._vendor_text(item.get("mac"), "mac")
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
        label = self._vendor_text(label_value, "showStyle", required=False) if label_value else None
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
            "show_style": self._vendor_text(
                item.get("showStyle"), "showStyle", required=False
            ),
            "vendor_tag_id": self._optional_vendor_integer(item.get("ido"), "ido", minimum=0),
            "router_status": self._optional_vendor_integer(
                item.get("routerStatus"), "routerStatus"
            ),
            "sub": self._optional_vendor_integer(item.get("sub"), "sub"),
        }, controller_id=controller_id)

    @staticmethod
    def _index_vendor_items(items: list[dict[str, Any]], field: str,
                            resource: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict) or item.get(field) is None:
                raise IntegrationError(f"Invalid vendor {resource} response")
            key = str(item[field])
            if not key or key in result:
                raise IntegrationError(f"Invalid vendor {resource} response")
            result[key] = item
        return result

    def vendor_style_catalog(self, client: Any,
                             controller_id: str = LEGACY_CONTROLLER_ID) -> list[dict[str, Any]]:
        try:
            items = client.get_style_catalog()
        except Exception as error:
            raise IntegrationError("Vendor style catalog failed") from error
        if not isinstance(items, list):
            raise IntegrationError("Vendor style catalog returned invalid data")
        return [self._normalize_vendor_style(item, controller_id=controller_id) for item in items]

    @staticmethod
    def _clone_catalog(client: Any) -> list[dict[str, Any]]:
        items = client.get_style_catalog()
        if (not isinstance(items, list) or len(items) > 10_000
                or any(not isinstance(item, dict) for item in items)):
            raise IntegrationError("Vendor style catalog returned invalid data")
        ids: set[int] = set()
        for item in items:
            style_id = Service._vendor_integer_value(item.get("id"), "id", minimum=1,
                                                     maximum=2_147_483_647)
            if style_id in ids:
                raise IntegrationError("Vendor style catalog returned duplicate ids")
            ids.add(style_id)
        return items

    @staticmethod
    def _catalog_by_id(items: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        return {int(item["id"]): item for item in items}

    @staticmethod
    def _component_identity(component: dict[str, Any]) -> str:
        # `feil` is the component kind in the live layouts (all current text
        # components use the literal value "text"), not a field identity.
        # `mpname` is the mapped vendor field and is what addColumnAndGood
        # receives as mappingText, so prefer it for source/target reconciliation.
        for key in ("mpname", "mappingText", "columnName", "field", "name", "feil"):
            value = component.get(key)
            if isinstance(value, str) and value.strip() and len(value.strip()) <= 200:
                return value.strip()
        raise IntegrationError("Vendor style component has no stable field identity")

    @classmethod
    def _components_by_identity(cls, layout: Any, *,
                                allow_empty: bool = False) -> dict[str, dict[str, Any]]:
        if (not isinstance(layout, list) or (not layout and not allow_empty) or len(layout) > 500
                or any(not isinstance(item, dict) for item in layout)):
            raise IntegrationError("Vendor style layout returned invalid data")
        result: dict[str, dict[str, Any]] = {}
        ids: set[int] = set()
        for component in layout:
            identity = cls._component_identity(component)
            component_id = cls._vendor_integer_value(
                component.get("id"), "component id", minimum=1, maximum=2_147_483_647
            )
            if identity in result or component_id in ids:
                raise IntegrationError("Vendor style layout has ambiguous components")
            result[identity] = component
            ids.add(component_id)
        return result

    @staticmethod
    def _clone_hash(value: Any) -> str:
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _normalized_editor_layout(cls, layout: Any, *,
                                  ignore_mpname: bool = False) -> list[dict[str, Any]]:
        cls._components_by_identity(layout)
        normalized = copy.deepcopy(layout)
        for component in normalized:
            if ignore_mpname:
                component.pop("mpname", None)
            style = component.get("style")
            if isinstance(style, dict) and "font-weight" in style:
                value = style["font-weight"]
                if (not isinstance(value, bool) and isinstance(value, (int, str))
                        and re.fullmatch(r"\d+", str(value))):
                    style["font-weight"] = int(value)
        return sorted(normalized, key=lambda item: str(item.get("name", "")))

    @classmethod
    def _source_snapshot_hash(cls, snapshot: dict[str, Any]) -> str:
        normalized = copy.deepcopy(snapshot)
        normalized["layout"] = cls._normalized_editor_layout(normalized["layout"])
        detail_components = normalized.get("detail", {}).get("dispMs")
        if isinstance(detail_components, list):
            normalized["detail"]["dispMs"] = sorted(
                detail_components, key=lambda item: str(item.get("name", ""))
            )
        for record_name in ("metadata", "detail"):
            record = normalized.get(record_name, {})
            for field_name in ("styleFileds", "styleFields"):
                if isinstance(record.get(field_name), list):
                    record[field_name] = sorted(record[field_name])
        return cls._clone_hash(normalized)

    @staticmethod
    def _difference_paths(expected: Any, actual: Any, prefix: str = "") -> list[str]:
        if type(expected) is not type(actual):
            return [prefix or "root"]
        if isinstance(expected, dict):
            paths: list[str] = []
            for key in sorted(set(expected) | set(actual)):
                path = f"{prefix}.{key}" if prefix else str(key)
                if key not in expected or key not in actual:
                    paths.append(path)
                else:
                    paths.extend(Service._difference_paths(expected[key], actual[key], path))
                if len(paths) >= 20:
                    break
            return paths[:20]
        if isinstance(expected, list):
            if len(expected) != len(actual):
                return [f"{prefix}.length" if prefix else "length"]
            paths = []
            for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
                paths.extend(Service._difference_paths(
                    expected_item, actual_item, f"{prefix}[{index}]"
                ))
                if len(paths) >= 20:
                    break
            return paths[:20]
        return [] if expected == actual else [prefix or "root"]

    @classmethod
    def _source_snapshot(cls, client: Any, source_id: int,
                         catalog_item: dict[str, Any]) -> tuple[dict[str, Any], str]:
        metadata = client.get_style_detail(source_id)
        detail = client.get_style_data(source_id)
        layout = client.get_style_layout(source_id)
        preview = client.get_template_preview(source_id)
        if (not isinstance(metadata, dict) or metadata.get("id") != source_id
                or not isinstance(detail, dict) or detail.get("id") != source_id
                or not isinstance(preview, tuple) or len(preview) != 2
                or not isinstance(preview[0], bytes) or not preview[0]
                or not isinstance(preview[1], str) or not preview[1].startswith("image/")):
            raise IntegrationError("Vendor source template snapshot returned invalid data")
        cls._components_by_identity(layout)
        snapshot = {
            "catalog": catalog_item,
            "metadata": metadata,
            "detail": detail,
            "layout": layout,
            "preview_sha256": hashlib.sha256(preview[0]).hexdigest(),
            "preview_type": preview[1],
        }
        return snapshot, cls._source_snapshot_hash(snapshot)

    @classmethod
    def _bold_target_layout(cls, source_layout: list[dict[str, Any]],
                            target_layout: list[dict[str, Any]]) -> list[dict[str, Any]]:
        target_by_identity = cls._components_by_identity(target_layout)
        source_by_identity = cls._components_by_identity(source_layout)
        source_ids = {int(item["id"]) for item in source_by_identity.values()}
        result: list[dict[str, Any]] = []
        for source in source_layout:
            identity = cls._component_identity(source)
            target_id = cls._vendor_integer_value(
                target_by_identity[identity].get("id"), "component id", minimum=1,
                maximum=2_147_483_647,
            )
            if target_id in source_ids:
                raise IntegrationError("Vendor target reused a source component id")
            component = copy.deepcopy(source)
            component["id"] = target_id
            if str(component.get("type", "")).lower() == "text":
                style = component.get("style")
                if not isinstance(style, dict):
                    raise IntegrationError("Vendor text component has invalid style")
                style["font-weight"] = "700"
            result.append(component)
        return result

    def _rollback_created_style(self, client: Any, created_id: int,
                                preexisting_ids: set[int], allowed_names: set[str]) -> None:
        if created_id in preexisting_ids:
            raise IntegrationError("Refusing to roll back a pre-existing vendor style")
        before = self._catalog_by_id(self._clone_catalog(client))
        if created_id not in before:
            return
        catalog_name = str(before[created_id].get("name", "")).strip()
        detail = client.get_style_data(created_id)
        if (catalog_name not in allowed_names or not isinstance(detail, dict)
                or detail.get("id") != created_id
                or str(detail.get("name", "")).strip() != catalog_name):
            raise IntegrationError("Refusing to roll back an unidentified vendor style")
        try:
            client.delete_style(created_id)
        except Exception:
            # A lost/error response is ambiguous; only the catalog read-back decides.
            pass
        after = self._catalog_by_id(self._clone_catalog(client))
        if created_id in after:
            raise IntegrationError("Vendor clone rollback could not be verified")

    @staticmethod
    def _clone_metadata_value(record: dict[str, Any], aliases: tuple[str, ...],
                              label: str) -> Any:
        values = [record[key] for key in aliases if key in record]
        if not values or any(value != values[0] for value in values[1:]):
            raise IntegrationError(f"Vendor template {label} is missing or inconsistent")
        return values[0]

    @classmethod
    def _verify_detail_components(cls, source_detail: Any, source_layout: Any,
                                  target_detail: Any, target_layout: Any,
                                  source_id: int, target_id: int) -> None:
        """Compare endpoint-native dispMs records without conflating their schema with orderJson."""
        if (not isinstance(source_detail, list) or not isinstance(target_detail, list)
                or len(source_detail) != len(target_detail)
                or any(not isinstance(item, dict) for item in source_detail + target_detail)):
            raise IntegrationError("Vendor template detail layout returned invalid data")

        def by_name(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
            result: dict[str, dict[str, Any]] = {}
            for item in items:
                name = item.get("name")
                if not isinstance(name, str) or not name or name in result:
                    raise IntegrationError(f"Vendor {label} has ambiguous component names")
                result[name] = item
            return result

        source_editor = by_name(source_layout, "source layout")
        target_editor = by_name(target_layout, "target layout")
        source_native = by_name(source_detail, "source detail layout")
        target_native = by_name(target_detail, "target detail layout")
        if not (source_editor.keys() == source_native.keys()
                == target_editor.keys() == target_native.keys()):
            raise IntegrationError("Vendor template detail components changed during clone")

        for name in source_editor:
            source_component = source_native[name]
            target_component = target_native[name]
            source_component_id = cls._vendor_integer_value(
                source_component.get("id"), "source detail component id", minimum=1
            )
            target_component_id = cls._vendor_integer_value(
                target_component.get("id"), "target detail component id", minimum=1
            )
            if (source_component_id != cls._vendor_integer_value(
                    source_editor[name].get("id"), "source component id", minimum=1)
                    or target_component_id != cls._vendor_integer_value(
                        target_editor[name].get("id"), "target component id", minimum=1)
                    or cls._vendor_integer_value(source_component.get("styleid"),
                                                 "source detail style id", minimum=1) != source_id
                    or cls._vendor_integer_value(target_component.get("styleid"),
                                                 "target detail style id", minimum=1) != target_id):
                raise IntegrationError("Vendor template detail component identity is inconsistent")

            source_preserved = copy.deepcopy(source_component)
            target_preserved = copy.deepcopy(target_component)
            for record in (source_preserved, target_preserved):
                record.pop("id", None)
                record.pop("styleid", None)
                record.pop("fontBold", None)
            if target_preserved != source_preserved:
                raise IntegrationError("Vendor template detail component changed during clone")
            if (str(target_component.get("columnType", "")).lower() == "text"
                    and target_component.get("fontBold") != "bold"):
                raise IntegrationError("Vendor template detail text is not bold")

    @classmethod
    def _verify_clone_readback(cls, source: dict[str, Any], target_catalog: dict[str, Any],
                               target_detail: Any, target_metadata: Any,
                               target_layout: Any, desired_layout: list[dict[str, Any]],
                               source_id: int, created_id: int, target_name: str) -> None:
        if (not isinstance(target_detail, dict) or target_detail.get("id") != created_id
                or not isinstance(target_metadata, dict)
                or target_metadata.get("id") != created_id):
            raise IntegrationError("Vendor template identity could not be verified")
        if (str(target_detail.get("name", "")).strip() != target_name
                or str(target_metadata.get("name", "")).strip() != target_name):
            raise IntegrationError("Vendor template name could not be verified")
        # Saving through /mms/updateDispMData normalizes mpname even though the
        # dynamic-field set remains authoritative in styleFileds. Compare every
        # other editor property here and verify field identity separately below.
        actual_editor = cls._normalized_editor_layout(target_layout, ignore_mpname=True)
        expected_editor = cls._normalized_editor_layout(desired_layout, ignore_mpname=True)
        if actual_editor != expected_editor:
            differences = cls._difference_paths(expected_editor, actual_editor)
            raise IntegrationError(
                "Vendor template editor layout could not be verified: "
                + ", ".join(differences)
            )

        # The controller overloads `type`: /style/getStyleData uses it for the
        # style alignment (9/8/2), while /associate/getStyleMsgById uses it for
        # the physical screen type. Compare like endpoints rather than merging
        # these records and treating their two meanings as one field.
        for source_record, target_record, endpoint in (
            (source["detail"], target_detail, "style data"),
            (source["metadata"], target_metadata, "style metadata"),
        ):
            for aliases, label in ((("width",), "width"), (("height",), "height")):
                if (cls._clone_metadata_value(source_record, aliases, f"{endpoint} {label}")
                        != cls._clone_metadata_value(target_record, aliases,
                                                     f"{endpoint} {label}")):
                    raise IntegrationError(f"Vendor template {label} changed during clone")

        source_alignment = cls._clone_metadata_value(
            source["detail"],
            ("stylealign", "styleAlign", "stylealignId", "styleAlignId", "type"),
            "style alignment",
        )
        target_alignment = cls._clone_metadata_value(
            target_detail,
            ("stylealign", "styleAlign", "stylealignId", "styleAlignId", "type"),
            "style alignment",
        )
        if (cls._vendor_integer_value(source_alignment, "style alignment", minimum=1)
                != cls.CLONE_SOURCES[source_id]
                or cls._vendor_integer_value(target_alignment, "style alignment", minimum=1)
                != cls.CLONE_SOURCES[source_id]):
            raise IntegrationError("Vendor template style alignment changed during clone")

        source_screen_type = cls._clone_metadata_value(
            source["metadata"], ("screenType", "screen_type", "type"), "screen type"
        )
        target_screen_type = cls._clone_metadata_value(
            target_metadata, ("screenType", "screen_type", "type"), "screen type"
        )
        if source_screen_type != target_screen_type:
            raise IntegrationError("Vendor template screen type changed during clone")

        source_field_key = next(
            (key for key in ("styleFileds", "styleFields") if key in source["metadata"]), None
        )
        target_field_key = next(
            (key for key in ("styleFileds", "styleFields") if key in target_metadata), None
        )
        if source_field_key is None or target_field_key is None:
            raise IntegrationError("Vendor template style fields changed during clone")
        source_fields = source["metadata"][source_field_key]
        target_fields = target_metadata[target_field_key]
        if (not isinstance(source_fields, list) or not isinstance(target_fields, list)
                or any(not isinstance(item, str) or not item for item in source_fields + target_fields)
                or len(set(source_fields)) != len(source_fields)
                or len(set(target_fields)) != len(target_fields)
                or set(target_fields) != set(source_fields)):
            raise IntegrationError("Vendor template style fields changed during clone")
        cls._verify_detail_components(
            source["detail"].get("dispMs"), source["layout"],
            target_detail.get("dispMs"), desired_layout, source_id, created_id,
        )

        # Re-parse both layouts to enforce exact, unique field identities as well as value equality.
        source_names = {item.get("name") for item in source["layout"]}
        target_names = {item.get("name") for item in target_layout}
        if (None in source_names or None in target_names or len(source_names) != len(source["layout"])
                or len(target_names) != len(target_layout) or target_names != source_names):
            raise IntegrationError("Vendor template component identities changed during clone")

    def clone_vendor_template(self, client: Any, data: Any, *,
                              controller_id: str = LEGACY_CONTROLLER_ID) -> dict[str, Any]:
        """Clone one allow-listed template with reconciled, read-back-verified mutations."""
        if not isinstance(data, dict) or set(data) != {"source_id", "target_name"}:
            raise ValidationError("JSON body must contain only source_id and target_name")
        source_id = data["source_id"]
        if (isinstance(source_id, bool) or not isinstance(source_id, int)
                or source_id not in self.CLONE_SOURCES):
            raise ValidationError("Unsupported source_id", details={"field": "source_id"})
        target_name = _text(data["target_name"], "target_name")
        assert target_name is not None
        if any(ord(character) < 32 or character in "/\\?#" for character in target_name):
            raise ValidationError("Invalid target_name", details={"field": "target_name"})

        created_id: int | None = None
        rollback_names = {target_name}
        preexisting_ids: set[int] = set()
        try:
            before = self._clone_catalog(client)
            before_by_id = self._catalog_by_id(before)
            if source_id not in before_by_id:
                raise NotFoundError("Source vendor template not found")
            if any(str(item.get("name", "")).strip() == target_name for item in before):
                raise ConflictError("Target vendor template name already exists")
            source_snapshot, source_hash = self._source_snapshot(
                client, source_id, before_by_id[source_id]
            )
            preexisting_ids = set(before_by_id)
            try:
                response_id = client.create_style(self.CLONE_SOURCES[source_id])
            except Exception as create_error:
                # Re-read only for diagnostics. Without a response ID no object is owned.
                try:
                    self._clone_catalog(client)
                except Exception:
                    pass
                raise IntegrationError("Vendor create outcome is ambiguous") from create_error
            response_id = self._vendor_integer_value(
                response_id, "created style id", minimum=1, maximum=2_147_483_647
            )
            after_create = self._clone_catalog(client)
            after_create_by_id = self._catalog_by_id(after_create)
            new_ids = set(after_create_by_id) - preexisting_ids
            if response_id in preexisting_ids or response_id not in new_ids:
                raise IntegrationError("Vendor create outcome is ambiguous")
            created_id = response_id
            rollback_names.add(str(after_create_by_id[created_id].get("name", "")).strip())
            if created_id == source_id:
                raise IntegrationError("Vendor create returned the source template id")

            target_detail = client.get_style_data(created_id)
            target_layout = client.get_style_layout(created_id)
            source_components = self._components_by_identity(source_snapshot["layout"])
            target_components = self._components_by_identity(target_layout, allow_empty=True)
            mapping_type = self._vendor_integer_value(
                target_detail.get("mappingtype"), "mappingtype", minimum=1
            )
            for identity, source_component in source_components.items():
                if identity in target_components:
                    continue
                column_name = str(source_component.get("type") or "text")
                try:
                    client.add_style_field(
                        created_id, mapping_type, column_name, identity
                    )
                except Exception:
                    pass
                # Fresh read-back reconciles success, including an ambiguous status.
                target_detail = client.get_style_data(created_id)
                target_layout = client.get_style_layout(created_id)
                target_components = self._components_by_identity(target_layout)
                if identity not in target_components:
                    raise IntegrationError("Vendor field creation could not be verified")

            desired_layout = self._bold_target_layout(source_snapshot["layout"], target_layout)
            try:
                client.rename_style(created_id, self.CLONE_SOURCES[source_id], target_name)
            except Exception:
                pass
            renamed_catalog = self._catalog_by_id(self._clone_catalog(client))
            renamed_detail = client.get_style_data(created_id)
            if (created_id not in renamed_catalog
                    or str(renamed_catalog[created_id].get("name", "")).strip() != target_name
                    or str(renamed_detail.get("name", "")).strip() != target_name):
                raise IntegrationError("Vendor template rename could not be verified")

            try:
                client.save_style_layout(created_id, desired_layout)
            except Exception:
                pass
            verified_detail = client.get_style_data(created_id)
            verified_layout = client.get_style_layout(created_id)
            verified_metadata = client.get_style_detail(created_id)
            verified_preview = client.get_template_preview(created_id)
            final_catalog = self._catalog_by_id(self._clone_catalog(client))
            if (created_id not in final_catalog
                    or str(final_catalog[created_id].get("name", "")).strip() != target_name
                    or not isinstance(verified_preview, tuple) or len(verified_preview) != 2
                    or not isinstance(verified_preview[0], bytes) or not verified_preview[0]
                    or not isinstance(verified_preview[1], str)
                    or not verified_preview[1].startswith("image/")):
                raise IntegrationError("Vendor template save could not be verified")
            self._verify_clone_readback(
                source_snapshot, final_catalog[created_id], verified_detail, verified_metadata,
                verified_layout, desired_layout, source_id, created_id, target_name,
            )

            final_source, final_source_hash = self._source_snapshot(
                client, source_id, final_catalog[source_id]
            )
            if final_source_hash != source_hash:
                raise IntegrationError("Source vendor template changed during clone")
            result = {
                "id": str(created_id),
                "name": target_name,
                "source_id": str(source_id),
                "layout_sha256": self._clone_hash(verified_layout),
                "preview_sha256": hashlib.sha256(verified_preview[0]).hexdigest(),
                "source_sha256": self._source_snapshot_hash(final_source),
            }
            with self.storage.connection() as connection:
                audit_id = (str(created_id) if controller_id == LEGACY_CONTROLLER_ID
                            else f"{controller_id}:{created_id}")
                self._audit(connection, "vendor.template.cloned", "template", audit_id, {
                    "controller_id": controller_id,
                    "vendor_template_id": str(created_id),
                    "source_id": source_id, "target_name": target_name,
                    "layout_sha256": result["layout_sha256"],
                    "preview_sha256": result["preview_sha256"],
                })
            return result
        except (ValidationError, ConflictError, NotFoundError):
            raise
        except Exception as error:
            if created_id is not None:
                try:
                    self._rollback_created_style(
                        client, created_id, preexisting_ids, rollback_names
                    )
                except Exception as rollback_error:
                    raise IntegrationError(
                        "Vendor template clone failed and rollback could not be verified"
                    ) from rollback_error
            if isinstance(error, IntegrationError):
                raise
            raise IntegrationError("Vendor template clone failed") from error

    def vendor_style_detail(self, client: Any, style_id: int,
                            controller_id: str = LEGACY_CONTROLLER_ID) -> dict[str, Any]:
        try:
            item = client.get_style_detail(style_id)
        except Exception as error:
            raise IntegrationError("Vendor style detail failed") from error
        normalized = self._normalize_vendor_style(
            item, detail=True, controller_id=controller_id
        )
        if normalized["id"] != str(style_id):
            raise IntegrationError("Vendor style detail returned a mismatched id")
        with self.storage.connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM templates WHERE controller_id = ? AND vendor_id = ?",
                (controller_id, str(style_id)),
            ).fetchone()
            if exists is not None:
                self.upsert_vendor_template(connection, item, controller_id=controller_id)
        return normalized

    def vendor_photos(self, client: Any,
                      controller_id: str = LEGACY_CONTROLLER_ID) -> list[dict[str, Any]]:
        try:
            items = client.get_photos()
        except Exception as error:
            raise IntegrationError("Vendor photo catalog failed") from error
        if not isinstance(items, list):
            raise IntegrationError("Vendor photo catalog returned invalid data")
        photos = [self._normalize_vendor_photo(item, controller_id) for item in items]
        self._index_vendor_items(photos, "id", "photo catalog")
        if len({photo["name"] for photo in photos}) != len(photos):
            raise IntegrationError("Invalid vendor photo catalog response")
        with self.storage.connection() as connection:
            self.storage.replace_vendor_photos(
                connection, photos, _now(), controller_id=controller_id
            )
        return photos

    @staticmethod
    def vendor_photo_data(client: Any, photo_name: str) -> tuple[bytes, str]:
        try:
            result = client.get_photo_data(photo_name)
        except Exception as error:
            raise IntegrationError("Vendor photo data failed") from error
        if (not isinstance(result, tuple) or len(result) != 2
                or not isinstance(result[0], bytes) or not result[0]
                or not isinstance(result[1], str) or not result[1].startswith("image/")):
            raise IntegrationError("Vendor photo data returned invalid data")
        return result

    @staticmethod
    def vendor_template_preview(client: Any, style_id: int) -> tuple[bytes, str]:
        try:
            result = client.get_template_preview(style_id)
        except Exception as error:
            raise IntegrationError("Vendor template preview failed") from error
        if (not isinstance(result, tuple) or len(result) != 2
                or not isinstance(result[0], bytes) or not result[0]
                or not isinstance(result[1], str) or not result[1].startswith("image/")):
            raise IntegrationError("Vendor template preview returned invalid data")
        return result

    def sync_read_only(self, client: Any,
                       controller_id: str = LEGACY_CONTROLLER_ID) -> dict[str, dict[str, int]]:
        """Fetch approved read-only collections and atomically upsert local inventory."""
        try:
            routers = client.get_routers()
            templates = client.get_templates()
            tags = client.get_tags()
            style_catalog = client.get_style_catalog()
            extended_tags = client.get_extended_tags()
        except Exception as error:
            raise IntegrationError("Vendor read-only sync failed") from error
        if any(not isinstance(collection, list) for collection in (
            routers, templates, tags, style_catalog, extended_tags
        )):
            raise IntegrationError("Vendor read-only sync returned invalid data")
        catalog_by_id = self._index_vendor_items(style_catalog, "id", "style catalog")
        templates_by_id = self._index_vendor_items(templates, "id", "templates")
        extended_by_mac = self._index_vendor_items(extended_tags, "mac", "extended tags")
        tags_by_mac = self._index_vendor_items(tags, "mac", "tags")

        if not set(templates_by_id).issubset(catalog_by_id):
            raise IntegrationError("Vendor style catalog is missing synchronized templates")
        if set(tags_by_mac) != set(extended_by_mac):
            raise IntegrationError("Vendor tag inventories do not match")

        merged_templates: list[dict[str, Any]] = []
        catalog_fields = {
            "descriptor", "width", "height", "mappingtype", "type", "backgroundID",
            "backgroundId", "updateTime", "updatetime", "styleFileds", "rotate", "userid",
        }
        for item in templates:
            key = str(item["id"])
            catalog_item = catalog_by_id[key]
            mms_name = item.get("name")
            catalog_name = catalog_item.get("name")
            if (mms_name not in (None, "") and catalog_name not in (None, "")
                    and str(mms_name).strip() != str(catalog_name).strip()):
                raise IntegrationError("Vendor template names conflict")
            dimensions = re.fullmatch(
                r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", str(item.get("styleLen") or "")
            )
            if dimensions is not None:
                mms_width, mms_height = map(int, dimensions.groups())
                catalog_width = self._vendor_integer(catalog_item, "width", minimum=1)
                catalog_height = self._vendor_integer(catalog_item, "height", minimum=1)
                if (mms_width, mms_height) != (catalog_width, catalog_height):
                    raise IntegrationError("Vendor template dimensions conflict")
            elif item.get("width") is not None or item.get("height") is not None:
                if item.get("width") is None or item.get("height") is None:
                    raise IntegrationError("Invalid vendor template dimensions")
                if (self._vendor_integer(item, "width", minimum=1)
                        != self._vendor_integer(catalog_item, "width", minimum=1)
                        or self._vendor_integer(item, "height", minimum=1)
                        != self._vendor_integer(catalog_item, "height", minimum=1)):
                    raise IntegrationError("Vendor template dimensions conflict")
            merged = dict(item)
            for field in catalog_fields:
                if field in catalog_item:
                    merged[field] = catalog_item[field]
            if not merged.get("name"):
                merged["name"] = catalog_name
            merged_templates.append(merged)
        templates = merged_templates

        immutable_tag_fields = {
            "width", "height", "styleId", "ido", "routerStatus", "sub",
        }
        merged_tags: list[dict[str, Any]] = []
        for item in tags:
            key = str(item["mac"])
            extended = extended_by_mac[key]
            for field in immutable_tag_fields:
                if field in item and field in extended:
                    left = self._vendor_integer(item, field)
                    right = self._vendor_integer(extended, field)
                    if left != right:
                        raise IntegrationError(f"Vendor tag field conflicts: {field}")
            merged_tags.append({**extended, **item})
        tags = merged_tags
        with self.storage.connection() as connection:
            for item in routers:
                self.upsert_vendor_router(connection, item, controller_id=controller_id)
            for item in templates:
                self.upsert_vendor_template(connection, item, controller_id=controller_id)
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
                self.upsert_vendor_tag(
                    connection, item, router_ids, template_ids, template_names,
                    controller_id=controller_id,
                )
            counts = {"routers": len(routers), "templates": len(templates), "tags": len(tags)}
            audit_id = ("vendor" if controller_id == LEGACY_CONTROLLER_ID
                        else f"{controller_id}:vendor")
            self._audit(
                connection, "vendor.sync.read_only", "system", audit_id,
                {**counts, "controller_id": controller_id},
            )
        return {"synced": counts}

    def dispatch_live(self, client: Any, data: Any,
                      controller_id: str = LEGACY_CONTROLLER_ID) -> dict[str, Any]:
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
                connection.execute(
                    "UPDATE tags SET status = ? WHERE controller_id = ? AND mac = ?",
                    (item["status"], controller_id, item["mac"]),
                )
            self._audit(connection, "vendor.update_screen", "tag", ",".join(sorted(macs)), {
                "controller_id": controller_id, "count": len(updates),
                "verified_tags": verified_tags,
            })
        return {"dispatched": len(updates), "verified_tags": verified_tags}
