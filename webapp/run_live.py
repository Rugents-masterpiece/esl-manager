"""Start ESL Manager against the configured live vendor controller."""

from __future__ import annotations

import argparse
import json
import math
import os
import stat
from pathlib import Path
from typing import Any

from esl_web import vendor
from esl_web.controllers import CONTROLLER_ID_PATTERN, ControllerRegistry
from esl_web.server import create_server, is_valid_api_token
from esl_web.service import ForbiddenError
from esl_web.vendor import VendorClient, validate_base_url

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


class TemplateReadOnlyClient:
    """Expose template/image reads only, independent of physical-write flags."""

    _READ_METHODS = frozenset({
        'get_style_catalog', 'get_style_detail', 'get_style_layout',
        'get_photos', 'get_photo_data',
    })

    def __init__(self, client):
        self._client = client

    def __getattr__(self, name):
        if name not in self._READ_METHODS:
            raise ForbiddenError('Controller access is restricted to reading templates and their images')
        return getattr(self._client, name)


class TemplatePublishClient:
    """Expose native publishing, with separately opted-in confirmed dispatch."""

    template_publish_scope = True

    _METHODS = frozenset({
        'get_style_catalog', 'get_style_detail', 'get_style_layout', 'get_style_data',
        'get_template_preview', 'get_photos', 'get_photo_data', 'get_tag_display',
        'create_style', 'add_style_field', 'rename_style', 'save_style_layout', 'upload_photo',
    })

    def __init__(self, client, *, allow_confirmed_dispatch: bool = False):
        self._client = client
        self.allow_confirmed_dispatch = allow_confirmed_dispatch

    def _update_screen(self, updates: list[dict[str, Any]], confirmation: str) -> list[dict[str, Any]]:
        if not self.allow_confirmed_dispatch or not vendor.live_writes_authorized(confirmation):
            raise ForbiddenError('Live ESL dispatch is disabled or not explicitly confirmed')
        # The real VendorClient independently checks authorization again.
        return self._client.update_screen(updates, confirmation)

    def __getattr__(self, name):
        if self.allow_confirmed_dispatch:
            if name == 'get_tags':
                return self._client.get_tags
            if name == 'update_screen':
                return self._update_screen
        if name not in self._METHODS:
            raise ForbiddenError('Controller access is restricted to template publishing and image access')
        return getattr(self._client, name)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--templates-only', action='store_true',
                       help='Allow only template/image reads; force physical writes off')
    modes.add_argument('--template-publish', action='store_true',
                       help='Allow native template publishing and template/image reads; physical writes off by default')
    parser.add_argument('--allow-confirmed-dispatch', action='store_true',
                        help='With --template-publish only, allow explicitly confirmed physical dispatch')
    args = parser.parse_args(argv)
    if args.allow_confirmed_dispatch and not args.template_publish:
        parser.error('--allow-confirmed-dispatch requires --template-publish')
    settings = load_settings(CREDENTIALS)
    if args.templates_only:
        factory = lambda config: TemplateReadOnlyClient(VendorClient(config))
    elif args.template_publish:
        factory = lambda config: TemplatePublishClient(
            VendorClient(config), allow_confirmed_dispatch=args.allow_confirmed_dispatch)
    else:
        factory = VendorClient
    os.environ["ESL_LIVE_WRITES"] = (
        "1" if args.allow_confirmed_dispatch or (
            settings.get("live_writes") is True
            and not (args.templates_only or args.template_publish)) else "0"
    )
    registry = ControllerRegistry.from_settings(settings, client_factory=factory)
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
