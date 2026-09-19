"""Start ESL Manager against the configured live vendor controller."""

from __future__ import annotations

import json
import math
import os
import stat
from pathlib import Path
from typing import Any

from esl_web.server import create_server
from esl_web.vendor import VendorClient, VendorConfig

ROOT = Path(__file__).resolve().parent
CREDENTIALS = ROOT / "data" / "live-credentials.json"
DATABASE = ROOT / "data" / "esl.sqlite3"


def load_settings(path: Path) -> dict[str, Any]:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise PermissionError(f"Credential path must be a regular file: {path}") from error
    with os.fdopen(descriptor, encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise PermissionError(f"Credential path must be a regular file: {path}")
        if info.st_uid != os.getuid():
            raise PermissionError(f"Credential file must be owned by the current user: {path}")
        if info.st_mode & 0o077:
            raise PermissionError(f"Credential file must have mode 0600: {path}")
        settings = json.load(stream)
    if not isinstance(settings, dict):
        raise ValueError("Credential file must contain a JSON object")
    if not isinstance(settings.get("live_writes"), bool):
        raise ValueError("live_writes must be an explicit JSON boolean")
    for field in ("base_url", "username", "password"):
        if not isinstance(settings.get(field), str) or not settings[field]:
            raise ValueError(f"{field} must be a non-empty string")
    for field in ("connect_timeout", "read_timeout"):
        if field not in settings:
            continue
        value = settings[field]
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0):
            raise ValueError(f"{field} must be a positive number")
    return settings


def main() -> None:
    settings = load_settings(CREDENTIALS)
    config = VendorConfig(
        base_url=settings["base_url"],
        username=settings["username"],
        password=settings["password"],
        connect_timeout=settings.get("connect_timeout", 3),
        read_timeout=settings.get("read_timeout", 10),
    )
    os.environ["ESL_LIVE_WRITES"] = "1" if settings.get("live_writes") is True else "0"
    server = create_server(
        "0.0.0.0",
        10050,
        database_path=DATABASE,
        seed=False,
        vendor_client=VendorClient(config),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
