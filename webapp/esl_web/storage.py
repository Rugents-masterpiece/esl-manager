"""SQLite persistence for the ESL Manager domain."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


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
    mapping_type INTEGER NOT NULL DEFAULT 0
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
    last_seen_at TEXT
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
            connection.executescript(SCHEMA)

    def seed_demo(self) -> None:
        """Insert deterministic sample data without duplicating rows."""
        statements = (
            ("INSERT OR IGNORE INTO templates VALUES (?, ?, ?, ?, ?)",
             ("tpl-default", "Základná cenovka", 296, 128, 0)),
            ("INSERT OR IGNORE INTO routers VALUES (?, ?, ?, ?, ?)",
             ("router-main", "Predajňa", "192.0.2.10", "online", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("prod-coffee", "SKU-COFFEE", "8580000000011", "Káva", 6.49, "EUR", "tpl-default", "2026-01-01T09:00:00Z", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("prod-tea", "SKU-TEA", "8580000000028", "Čaj", 3.29, "EUR", "tpl-default", "2026-01-01T09:00:00Z", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO tags VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("tag-001", "00:11:22:33:44:55", "Regál A", 296, 128, 88, -55, "ready", "router-main", "tpl-default", "2026-01-01T09:00:00Z")),
            ("INSERT OR IGNORE INTO tags VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
             ("tag-002", "00:11:22:33:44:66", "Regál B", 296, 128, 15, -82, "failed", "router-main", "tpl-default", "2026-01-01T08:55:00Z")),
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
