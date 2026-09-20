"""SQLite persistence for the ESL Manager domain."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA_VERSION = 3
LEGACY_CONTROLLER_ID = "legacy"
SUPPORTED_DEVICE_MODELS = {
    "2.13TFT-BW": (250, 132),
    "2.13EPD-BWR": (250, 122),
    "2.9EPD-BWR": (296, 128),
}

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    ean TEXT UNIQUE,
    name TEXT NOT NULL,
    price REAL NOT NULL CHECK(price >= 0),
    currency TEXT NOT NULL DEFAULT 'EUR',
    template_id TEXT REFERENCES templates(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS routers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('online', 'offline')),
    last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    width INTEGER NOT NULL CHECK(width > 0),
    height INTEGER NOT NULL CHECK(height > 0),
    mapping_type INTEGER NOT NULL DEFAULT 0,
    descriptor TEXT,
    screen_type INTEGER,
    background_id INTEGER,
    vendor_updated_at TEXT,
    style_fields TEXT NOT NULL DEFAULT '[]',
    rotate INTEGER,
    user_id INTEGER
);
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    mac TEXT NOT NULL UNIQUE,
    label TEXT,
    width INTEGER NOT NULL CHECK(width > 0),
    height INTEGER NOT NULL CHECK(height > 0),
    battery INTEGER NOT NULL CHECK(battery BETWEEN 0 AND 100),
    rssi INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('ready', 'updating', 'failed', 'success')),
    router_id TEXT REFERENCES routers(id) ON DELETE SET NULL,
    template_id TEXT REFERENCES templates(id) ON DELETE SET NULL,
    last_seen_at TEXT,
    show_style TEXT,
    vendor_tag_id INTEGER,
    router_status INTEGER,
    sub INTEGER
);
CREATE TABLE IF NOT EXISTS vendor_photos (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    width INTEGER NOT NULL CHECK(width > 0),
    height INTEGER NOT NULL CHECK(height > 0),
    synced_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product_tags (
    product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL UNIQUE REFERENCES tags(id) ON DELETE CASCADE,
    bound_at TEXT NOT NULL,
    PRIMARY KEY(product_id, tag_id)
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('queued', 'processing', 'completed', 'partial', 'failed')),
    requested_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    total_items INTEGER NOT NULL,
    succeeded_items INTEGER NOT NULL DEFAULT 0,
    failed_items INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS job_items (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    product_id TEXT REFERENCES products(id) ON DELETE SET NULL,
    tag_id TEXT REFERENCES tags(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK(status IN ('queued', 'processing', 'succeeded', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'critical')),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    message TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0, 1)),
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tags_status ON tags(status);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(active);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at DESC);
"""


class Storage:
    """Own the database schema and short-lived SQLite connections."""

    TABLES = (
        "controllers",
        "device_models",
        "products",
        "tags",
        "routers",
        "templates",
        "product_tags",
        "jobs",
        "job_items",
        "alerts",
        "audit_events",
    )

    def __init__(self, path: str | Path):
        self.path = str(path)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            self._execute_statements(connection, SCHEMA)
            self._ensure_columns(connection, "templates", {
                "descriptor": "TEXT",
                "screen_type": "INTEGER",
                "background_id": "INTEGER",
                "vendor_updated_at": "TEXT",
                "style_fields": "TEXT NOT NULL DEFAULT '[]'",
                "rotate": "INTEGER",
                "user_id": "INTEGER",
            })
            self._ensure_columns(connection, "tags", {
                "show_style": "TEXT",
                "vendor_tag_id": "INTEGER",
                "router_status": "INTEGER",
                "sub": "INTEGER",
            })
            connection.commit()
            connection.execute("PRAGMA foreign_keys = OFF")
            try:
                connection.execute("BEGIN IMMEDIATE")
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if version < 2:
                    self._migrate_controller_scope(connection)
                if version < 3:
                    self._migrate_tag_configuration(connection)
                if version < SCHEMA_VERSION:
                    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.execute("PRAGMA foreign_keys = ON")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise sqlite3.IntegrityError(f"Foreign key check failed: {violations!r}")

    @staticmethod
    def _migrate_controller_scope(connection: sqlite3.Connection) -> None:
        """Rebuild vendor-owned tables with stable local and scoped vendor identities."""
        statements = """
            PRAGMA legacy_alter_table = ON;
            CREATE TABLE controllers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                is_default INTEGER NOT NULL DEFAULT 0 CHECK(is_default IN (0, 1))
            );
            CREATE UNIQUE INDEX idx_controllers_one_default
                ON controllers(is_default) WHERE is_default = 1;
            INSERT INTO controllers(id, name, is_default) VALUES ('legacy', 'Legacy controller', 1);

            CREATE TABLE device_models (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                width INTEGER NOT NULL CHECK(width > 0),
                height INTEGER NOT NULL CHECK(height > 0),
                alignment_id INTEGER NOT NULL CHECK(alignment_id > 0),
                screen_type INTEGER NOT NULL CHECK(screen_type > 0)
            );
            INSERT INTO device_models VALUES ('2.13TFT-BW', '2.13TFT-BW', 250, 132, 8, 1);
            INSERT INTO device_models VALUES ('2.13EPD-BWR', '2.13EPD-BWR', 250, 122, 9, 2);
            INSERT INTO device_models VALUES ('2.9EPD-BWR', '2.9EPD-BWR', 296, 128, 2, 2);

            CREATE TABLE local_id_sequences (
                entity TEXT PRIMARY KEY,
                next_value INTEGER NOT NULL CHECK(next_value > 0)
            );
            CREATE TABLE local_ids (
                entity TEXT NOT NULL,
                controller_id TEXT NOT NULL REFERENCES controllers(id) ON DELETE CASCADE,
                vendor_id TEXT NOT NULL,
                local_id TEXT NOT NULL,
                PRIMARY KEY(entity, controller_id, vendor_id),
                UNIQUE(entity, local_id)
            );

            ALTER TABLE routers RENAME TO routers_v1;
            CREATE TABLE routers (
                id TEXT PRIMARY KEY,
                controller_id TEXT NOT NULL REFERENCES controllers(id) ON DELETE CASCADE,
                vendor_id TEXT NOT NULL,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('online', 'offline')),
                last_seen_at TEXT,
                UNIQUE(controller_id, vendor_id),
                UNIQUE(controller_id, address)
            );
            INSERT INTO routers(id, controller_id, vendor_id, name, address, status, last_seen_at)
                SELECT id, 'legacy', id, name, address, status, last_seen_at FROM routers_v1;

            ALTER TABLE templates RENAME TO templates_v1;
            CREATE TABLE templates (
                id TEXT PRIMARY KEY,
                controller_id TEXT NOT NULL REFERENCES controllers(id) ON DELETE CASCADE,
                vendor_id TEXT NOT NULL,
                name TEXT NOT NULL,
                width INTEGER NOT NULL CHECK(width > 0),
                height INTEGER NOT NULL CHECK(height > 0),
                mapping_type INTEGER NOT NULL DEFAULT 0,
                descriptor TEXT,
                screen_type INTEGER,
                background_id INTEGER,
                vendor_updated_at TEXT,
                style_fields TEXT NOT NULL DEFAULT '[]',
                rotate INTEGER,
                user_id INTEGER,
                UNIQUE(controller_id, vendor_id),
                UNIQUE(controller_id, name)
            );
            INSERT INTO templates(
                id, controller_id, vendor_id, name, width, height, mapping_type, descriptor,
                screen_type, background_id, vendor_updated_at, style_fields, rotate, user_id
            ) SELECT id, 'legacy', id, name, width, height, mapping_type, descriptor,
                     screen_type, background_id, vendor_updated_at, style_fields, rotate, user_id
                FROM templates_v1;

            ALTER TABLE tags RENAME TO tags_v1;
            CREATE TABLE tags (
                id TEXT PRIMARY KEY,
                controller_id TEXT NOT NULL REFERENCES controllers(id) ON DELETE CASCADE,
                vendor_id TEXT NOT NULL,
                mac TEXT NOT NULL,
                label TEXT,
                width INTEGER NOT NULL CHECK(width > 0),
                height INTEGER NOT NULL CHECK(height > 0),
                battery INTEGER NOT NULL CHECK(battery BETWEEN 0 AND 100),
                rssi INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ready', 'updating', 'failed', 'success')),
                router_id TEXT REFERENCES routers(id) ON DELETE SET NULL,
                template_id TEXT REFERENCES templates(id) ON DELETE SET NULL,
                device_model_id TEXT REFERENCES device_models(id) ON DELETE SET NULL,
                last_seen_at TEXT,
                show_style TEXT,
                vendor_tag_id INTEGER,
                router_status INTEGER,
                sub INTEGER,
                UNIQUE(controller_id, vendor_id),
                UNIQUE(controller_id, mac)
            );
            INSERT INTO tags(
                id, controller_id, vendor_id, mac, label, width, height, battery, rssi, status,
                router_id, template_id, last_seen_at, show_style, vendor_tag_id, router_status, sub
            ) SELECT source.id, 'legacy',
                     CASE
                         WHEN source.vendor_tag_id IS NULL OR source.vendor_tag_id = 0
                             THEN 'id:' || hex(CAST(source.id AS BLOB))
                         WHEN (SELECT COUNT(*) FROM tags_v1 AS duplicate
                               WHERE duplicate.vendor_tag_id = source.vendor_tag_id) > 1
                             THEN CAST(source.vendor_tag_id AS TEXT) || ':id:'
                                  || hex(CAST(source.id AS BLOB))
                         ELSE CAST(source.vendor_tag_id AS TEXT)
                     END,
                     source.mac, source.label, source.width,
                     source.height, source.battery, source.rssi, source.status,
                     source.router_id, source.template_id, source.last_seen_at, source.show_style,
                     source.vendor_tag_id, source.router_status, source.sub FROM tags_v1 AS source;

            ALTER TABLE vendor_photos RENAME TO vendor_photos_v1;
            CREATE TABLE vendor_photos (
                id TEXT PRIMARY KEY,
                controller_id TEXT NOT NULL REFERENCES controllers(id) ON DELETE CASCADE,
                vendor_id TEXT NOT NULL,
                name TEXT NOT NULL,
                width INTEGER NOT NULL CHECK(width > 0),
                height INTEGER NOT NULL CHECK(height > 0),
                synced_at TEXT NOT NULL,
                UNIQUE(controller_id, vendor_id),
                UNIQUE(controller_id, name)
            );
            INSERT INTO vendor_photos(id, controller_id, vendor_id, name, width, height, synced_at)
                SELECT id, 'legacy', id, name, width, height, synced_at FROM vendor_photos_v1;

            DROP TABLE tags_v1;
            DROP TABLE routers_v1;
            DROP TABLE templates_v1;
            DROP TABLE vendor_photos_v1;
            CREATE INDEX IF NOT EXISTS idx_tags_status ON tags(status);
            PRAGMA legacy_alter_table = OFF;
        """
        Storage._execute_statements(connection, statements)

    @staticmethod
    def _migrate_tag_configuration(connection: sqlite3.Connection) -> None:
        """Add local tag configuration state while preserving vendor inventory."""
        Storage._ensure_columns(connection, "tags", {
            "inventory_source": "TEXT NOT NULL DEFAULT 'vendor'",
            "configuration_source": "TEXT NOT NULL DEFAULT 'vendor'",
            "test_data": "TEXT NOT NULL DEFAULT '{}'",
        })
        rows = connection.execute("SELECT id, controller_id, mac FROM tags").fetchall()
        normalized: dict[tuple[str, str], str] = {}
        for row in rows:
            mac = Storage.normalized_mac(row["mac"])
            key = (row["controller_id"], mac.casefold())
            if key in normalized and normalized[key] != row["id"]:
                raise sqlite3.IntegrityError("Normalized tag MAC collision")
            normalized[key] = row["id"]
            connection.execute("UPDATE tags SET mac = ? WHERE id = ?", (mac, row["id"]))
        for model_id, (width, height) in SUPPORTED_DEVICE_MODELS.items():
            connection.execute(
                "UPDATE tags SET device_model_id = ? WHERE device_model_id IS NULL "
                "AND width = ? AND height = ?", (model_id, width, height),
            )

    @staticmethod
    def normalized_mac(value: str) -> str:
        """Canonicalize standard 48-bit MACs and preserve opaque legacy vendor IDs."""
        compact = value.strip()
        for separator in (":", ".", "-"):
            compact = compact.replace(separator, "")
        if (len(compact) == 12
                and all(character in "0123456789abcdefABCDEF" for character in compact)):
            return ":".join(
                compact[index:index + 2] for index in range(0, 12, 2)
            ).upper()
        return value

    @staticmethod
    def _execute_statements(connection: sqlite3.Connection, statements: str) -> None:
        """Execute simple schema statements without executescript's implicit commit."""
        for statement in statements.split(";"):
            if statement.strip():
                connection.execute(statement)

    @staticmethod
    def _ensure_columns(connection: sqlite3.Connection, table: str,
                        columns: dict[str, str]) -> None:
        existing = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def seed_demo(self) -> None:
        """Insert deterministic sample data without duplicating rows."""
        statements = (
            ("INSERT OR IGNORE INTO templates(id, controller_id, vendor_id, name, width, height, mapping_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
             ("tpl-default", LEGACY_CONTROLLER_ID, "tpl-default", "Základná cenovka", 296, 128, 0)),
            ("INSERT OR IGNORE INTO routers(id, controller_id, vendor_id, name, address, status, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
             ("router-main", LEGACY_CONTROLLER_ID, "router-main", "Predajňa", "192.0.2.10", "online", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("prod-coffee", "SKU-COFFEE", "8580000000011", "Káva", 6.49, "EUR", "tpl-default", "2026-01-01T09:00:00Z", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("prod-tea", "SKU-TEA", "8580000000028", "Čaj", 3.29, "EUR", "tpl-default", "2026-01-01T09:00:00Z", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO tags(id, controller_id, vendor_id, mac, label, width, height, battery, rssi, status, router_id, template_id, device_model_id, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("tag-001", LEGACY_CONTROLLER_ID, "tag-001", "00:11:22:33:44:55", "Regál A", 296, 128, 88, -55, "ready", "router-main", "tpl-default", "2.9EPD-BWR", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO tags(id, controller_id, vendor_id, mac, label, width, height, battery, rssi, status, router_id, template_id, device_model_id, last_seen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("tag-002", LEGACY_CONTROLLER_ID, "tag-002", "00:11:22:33:44:66", "Regál B", 296, 128, 15, -82, "failed", "router-main", "tpl-default", "2.9EPD-BWR", "2026-01-01T08:55:00Z")),
            ("INSERT OR IGNORE INTO product_tags VALUES (?, ?, ?)",
             ("prod-coffee", "tag-001", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
             ("job-demo", "failed", "2026-01-01T09:00:00Z", "2026-01-01T09:01:00Z", "2026-01-01T09:02:00Z", 1, 0, 1)),
            ("INSERT OR IGNORE INTO job_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
             ("item-demo", "job-demo", "prod-tea", "tag-002", "failed", 1, "Simulated failure", "2026-01-01T09:02:00Z")),
            ("INSERT OR IGNORE INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("alert-low-battery", "low_battery", "warning", "tag", "tag-002", "Nízka batéria", 1, "2026-01-01T09:00:00Z", None)),
        )
        with self.connection() as connection:
            for sql, values in statements:
                connection.execute(sql, values)
            connection.execute(
                "INSERT INTO audit_events(action, entity_type, entity_id, details, created_at) "
                "SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS "
                "(SELECT 1 FROM audit_events WHERE action = ? AND entity_id = ?)",
                ("demo.seed", "system", "demo", "{}", "2026-01-01T09:00:00Z", "demo.seed", "demo"),
            )

    def table_counts(self) -> dict[str, int]:
        with self.connection() as connection:
            return {
                table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in self.TABLES
            }

    def configure_controllers(self, controllers: list[dict]) -> None:
        """Persist public registry metadata without storing controller credentials."""
        with self.connection() as connection:
            connection.execute("UPDATE controllers SET is_default = 0 WHERE is_default = 1")
            for controller in controllers:
                connection.execute(
                    "INSERT INTO controllers(id, name, is_default) VALUES (?, ?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
                    "is_default=excluded.is_default",
                    (controller["id"], controller["name"], int(controller["default"])),
                )

    @staticmethod
    def local_id(connection: sqlite3.Connection, entity: str,
                 controller_id: str, vendor_id: object) -> str:
        """Return a stable transactionally allocated ID that cannot overlap an existing PK."""
        tables = {"router": "routers", "template": "templates", "tag": "tags",
                  "photo": "vendor_photos"}
        if entity not in tables:
            raise ValueError("Unknown local ID entity")
        table = tables[entity]
        value = str(vendor_id)
        mapped = connection.execute(
            "SELECT local_id FROM local_ids "
            "WHERE entity = ? AND controller_id = ? AND vendor_id = ?",
            (entity, controller_id, value),
        ).fetchone()
        if mapped is not None:
            return mapped[0]
        persisted = connection.execute(
            f"SELECT id FROM {table} WHERE controller_id = ? AND vendor_id = ?",
            (controller_id, value),
        ).fetchone()
        if persisted is not None:
            try:
                connection.execute(
                    "INSERT INTO local_ids(entity, controller_id, vendor_id, local_id) "
                    "VALUES (?, ?, ?, ?)",
                    (entity, controller_id, value, persisted[0]),
                )
            except sqlite3.IntegrityError:
                owner = connection.execute(
                    "SELECT controller_id, vendor_id FROM local_ids "
                    "WHERE entity = ? AND local_id = ?",
                    (entity, persisted[0]),
                ).fetchone()
                if owner is None or tuple(owner) != (controller_id, value):
                    raise
            return persisted[0]
        raw_id_available = (
            connection.execute(f"SELECT 1 FROM {table} WHERE id = ?", (value,)).fetchone()
            is None
            and connection.execute(
                "SELECT 1 FROM local_ids WHERE entity = ? AND local_id = ?",
                (entity, value),
            ).fetchone() is None
        )
        if controller_id == LEGACY_CONTROLLER_ID and raw_id_available:
            connection.execute(
                "INSERT INTO local_ids(entity, controller_id, vendor_id, local_id) "
                "VALUES (?, ?, ?, ?)",
                (entity, controller_id, value, value),
            )
            return value
        while True:
            allocated = connection.execute(
                "INSERT INTO local_id_sequences(entity, next_value) VALUES (?, 2) "
                "ON CONFLICT(entity) DO UPDATE SET next_value = next_value + 1 "
                "RETURNING next_value - 1",
                (entity,),
            ).fetchone()[0]
            candidate = f"scoped-{entity}-{allocated}"
            if (connection.execute(
                    f"SELECT 1 FROM {table} WHERE id = ?", (candidate,)
            ).fetchone() is not None or connection.execute(
                    "SELECT 1 FROM local_ids WHERE entity = ? AND local_id = ?",
                    (entity, candidate),
            ).fetchone() is not None):
                continue
            connection.execute(
                "INSERT INTO local_ids(entity, controller_id, vendor_id, local_id) "
                "VALUES (?, ?, ?, ?)",
                (entity, controller_id, value, candidate),
            )
            return candidate

    def upsert_router(self, connection: sqlite3.Connection, router: dict,
                      controller_id: str = LEGACY_CONTROLLER_ID) -> None:
        """Insert or update one normalized vendor router in an existing transaction."""
        vendor_id = str(router["id"])
        local_id = self.local_id(connection, "router", controller_id, vendor_id)
        connection.execute(
            "INSERT INTO routers(id, controller_id, vendor_id, name, address, status, last_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(controller_id, vendor_id) DO UPDATE SET name=excluded.name, "
            "address=excluded.address, status=excluded.status, last_seen_at=excluded.last_seen_at",
            (local_id, controller_id, vendor_id, router["name"], router["address"],
             router["status"], router["last_seen_at"]),
        )

    def upsert_template(self, connection: sqlite3.Connection, template: dict,
                        controller_id: str = LEGACY_CONTROLLER_ID) -> None:
        """Insert or update one normalized vendor template in an existing transaction."""
        vendor_id = str(template["id"])
        local_id = self.local_id(connection, "template", controller_id, vendor_id)
        connection.execute(
            "INSERT INTO templates(id, controller_id, vendor_id, name, width, height, mapping_type, descriptor, screen_type, "
            "background_id, vendor_updated_at, style_fields, rotate, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(controller_id, vendor_id) DO UPDATE SET name=excluded.name, width=excluded.width, "
            "height=excluded.height, mapping_type=excluded.mapping_type, descriptor=excluded.descriptor, "
            "screen_type=excluded.screen_type, background_id=excluded.background_id, "
            "vendor_updated_at=excluded.vendor_updated_at, style_fields=excluded.style_fields, "
            "rotate=excluded.rotate, user_id=excluded.user_id",
            (local_id, controller_id, vendor_id, template["name"], template["width"], template["height"],
             template["mapping_type"], template.get("descriptor"), template.get("screen_type"),
             template.get("background_id"), template.get("vendor_updated_at"),
             json.dumps(template.get("style_fields", []), ensure_ascii=False),
             template.get("rotate"), template.get("user_id")),
        )

    @staticmethod
    def _disambiguated_tag_vendor_id(vendor_id: str, source_id: object) -> str:
        encoded = str(source_id).encode("utf-8").hex().upper()
        return f"{vendor_id}:id:{encoded}"

    def upsert_tag(self, connection: sqlite3.Connection, tag: dict,
                   controller_id: str = LEGACY_CONTROLLER_ID) -> None:
        """Insert or update one normalized vendor tag in an existing transaction."""
        raw_vendor_id = tag.get("vendor_tag_id")
        positive_vendor_id = raw_vendor_id not in (None, "", 0, "0")
        base_vendor_id = str(raw_vendor_id) if positive_vendor_id else str(tag["id"])
        mac = self.normalized_mac(tag["mac"])
        existing = connection.execute(
            "SELECT id, vendor_id FROM tags WHERE controller_id = ? AND mac = ?",
            (controller_id, mac),
        ).fetchone()
        if existing is not None:
            local_id, vendor_id = existing
        else:
            vendor_id = base_vendor_id
            disambiguated_identity = self._disambiguated_tag_vendor_id(
                base_vendor_id, tag["id"]
            )
            local_identity = (
                disambiguated_identity
                if positive_vendor_id and controller_id != LEGACY_CONTROLLER_ID
                else str(tag["id"])
            )
            if positive_vendor_id:
                collision = connection.execute(
                    "SELECT id FROM tags WHERE controller_id = ? AND vendor_id = ?",
                    (controller_id, base_vendor_id),
                ).fetchone()
                if collision is not None:
                    reserved = connection.execute(
                        "SELECT vendor_id FROM local_ids "
                        "WHERE entity = 'tag' AND controller_id = ? AND local_id = ?",
                        (controller_id, collision["id"]),
                    ).fetchone()
                    existing_identity = (
                        reserved[0]
                        if (reserved is not None
                            and reserved[0].startswith(f"{base_vendor_id}:id:"))
                        else self._disambiguated_tag_vendor_id(
                            base_vendor_id, collision["id"]
                        )
                    )
                    connection.execute(
                        "UPDATE tags SET vendor_id = ? WHERE id = ?",
                        (existing_identity, collision["id"]),
                    )
                    vendor_id = disambiguated_identity
            local_id = self.local_id(connection, "tag", controller_id, local_identity)
        router_id = (self.local_id(connection, "router", controller_id, tag["router_id"])
                     if tag.get("router_id") is not None else None)
        template_id = (self.local_id(connection, "template", controller_id, tag["template_id"])
                       if tag.get("template_id") is not None else None)
        device_model_id = next((
            model_id for model_id, dimensions in SUPPORTED_DEVICE_MODELS.items()
            if dimensions == (tag["width"], tag["height"])
        ), None)
        connection.execute(
            "INSERT INTO tags(id, controller_id, vendor_id, mac, label, width, height, battery, rssi, status, router_id, template_id, "
            "device_model_id, last_seen_at, show_style, vendor_tag_id, router_status, sub) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(controller_id, vendor_id) DO UPDATE SET "
            "mac=CASE WHEN tags.configuration_source = 'local' THEN tags.mac ELSE excluded.mac END, "
            "label=CASE WHEN tags.configuration_source = 'local' THEN tags.label ELSE excluded.label END, "
            "width=CASE WHEN tags.configuration_source = 'local' THEN tags.width ELSE excluded.width END, "
            "height=CASE WHEN tags.configuration_source = 'local' THEN tags.height ELSE excluded.height END, "
            "battery=excluded.battery, rssi=excluded.rssi, status=excluded.status, "
            "router_id=CASE WHEN tags.configuration_source = 'local' THEN tags.router_id ELSE excluded.router_id END, "
            "template_id=CASE WHEN tags.configuration_source = 'local' THEN tags.template_id ELSE excluded.template_id END, "
            "device_model_id=CASE WHEN tags.configuration_source = 'local' THEN tags.device_model_id ELSE excluded.device_model_id END, "
            "last_seen_at=excluded.last_seen_at, show_style=excluded.show_style, "
            "vendor_tag_id=excluded.vendor_tag_id, router_status=excluded.router_status, "
            "sub=excluded.sub, inventory_source='vendor'",
            (local_id, controller_id, vendor_id, mac, tag["label"], tag["width"],
             tag["height"], tag["battery"], tag["rssi"], tag["status"], router_id, template_id,
             device_model_id, tag["last_seen_at"], tag.get("show_style"), tag.get("vendor_tag_id"),
             tag.get("router_status"), tag.get("sub")),
        )

    def replace_vendor_photos(self, connection: sqlite3.Connection,
                              photos: list[dict], synced_at: str,
                              controller_id: str = LEGACY_CONTROLLER_ID) -> None:
        connection.execute("DELETE FROM vendor_photos WHERE controller_id = ?", (controller_id,))
        connection.executemany(
            "INSERT INTO vendor_photos(id, controller_id, vendor_id, name, width, height, synced_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(self.local_id(connection, "photo", controller_id, photo["id"]),
              controller_id, str(photo["id"]), photo["name"], photo["width"], photo["height"],
              synced_at)
             for photo in photos],
        )
