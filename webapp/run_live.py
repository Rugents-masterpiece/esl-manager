"""Start ESL Manager against the configured live vendor controller."""

from __future__ import annotations

import json
import math
import os
import stat
from pathlib import Path
from typing import Any

from esl_web.controllers import CONTROLLER_ID_PATTERN, ControllerRegistry
from esl_web.server import create_server, is_valid_api_token
from esl_web.vendor import validate_base_url

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
    if not is_valid_api_token(settings.get("api_token")):
        raise ValueError("api_token must be a 64-character URL-safe token")

    controllers = settings.get("controllers")
    if controllers is None:
        _validate_controller(settings)
    else:
        if not isinstance(controllers, list) or not controllers:
            raise ValueError("controllers must be a non-empty array")
        ids: set[str] = set()
        names: set[str] = set()
        base_urls: set[str] = set()
        declared_defaults = []
        for controller in controllers:
            if not isinstance(controller, dict):
                raise ValueError("each controller must be an object")
            if "default" in controller and not isinstance(controller["default"], bool):
                raise ValueError("controller default must be a boolean")
            if controller.get("default") is True:
                declared_defaults.append(controller.get("id"))
            controller_id = controller.get("id")
            name = controller.get("name")
            if (not isinstance(controller_id, str)
                    or CONTROLLER_ID_PATTERN.fullmatch(controller_id) is None):
                raise ValueError("controller id must be URL-safe and at most 64 characters")
            if (not isinstance(name, str) or name != name.strip() or not name
                    or len(name) > 100 or any(ord(character) < 32 for character in name)):
                raise ValueError("controller name must be a safe non-empty string")
            folded_name = name.casefold()
            if controller_id in ids or folded_name in names:
                raise ValueError("controller ids and names must be unique")
            ids.add(controller_id)
            names.add(folded_name)
            _validate_controller(controller)
            base_url = validate_base_url(controller["base_url"])
            if base_url in base_urls:
                raise ValueError("controller base URLs must be unique")
            base_urls.add(base_url)
        default_id = settings.get("default_controller")
        if default_id is None and len(declared_defaults) == 1:
            default_id = declared_defaults[0]
            settings["default_controller"] = default_id
        if (len(declared_defaults) > 1
                or (declared_defaults and default_id not in declared_defaults)
                or not isinstance(default_id, str)
                or CONTROLLER_ID_PATTERN.fullmatch(default_id) is None
                or default_id not in ids):
            raise ValueError("default_controller must identify a configured controller")
    return settings


def _validate_controller(settings: dict[str, Any]) -> None:
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


def main() -> None:
    settings = load_settings(CREDENTIALS)
    registry = ControllerRegistry.from_settings(settings)
    os.environ["ESL_LIVE_WRITES"] = "1" if settings.get("live_writes") is True else "0"
    server = create_server(
        "0.0.0.0",
        10050,
        database_path=DATABASE,
        seed=False,
        controller_registry=registry,
        api_token=settings["api_token"],
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
