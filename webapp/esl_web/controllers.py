"""Validated, secret-safe access to configured ESL controllers."""

from __future__ import annotations

import re
from typing import Any

from .storage import LEGACY_CONTROLLER_ID
from .vendor import VendorClient, VendorConfig, VendorConfigurationError


CONTROLLER_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


class ControllerRegistry:
    """Own one isolated vendor client per configured controller."""

    def __init__(self, controllers: list[dict[str, Any]], default_id: str):
        if not isinstance(controllers, list) or not controllers:
            raise ValueError("controllers must be a non-empty array")
        if (not isinstance(default_id, str)
                or CONTROLLER_ID_PATTERN.fullmatch(default_id) is None
                or default_id == LEGACY_CONTROLLER_ID):
            raise ValueError("default_controller must be a valid controller id")

        validated: list[tuple[str, str, VendorConfig]] = []
        ids: set[str] = set()
        names: set[str] = set()
        base_urls: set[str] = set()
        for item in controllers:
            if not isinstance(item, dict):
                raise ValueError("each controller must be an object")
            controller_id = item.get("id")
            name = item.get("name")
            if (not isinstance(controller_id, str)
                    or CONTROLLER_ID_PATTERN.fullmatch(controller_id) is None
                    or controller_id == LEGACY_CONTROLLER_ID):
                raise ValueError("controller id must be URL-safe and at most 64 characters")
            if (not isinstance(name, str) or name != name.strip() or not name
                    or len(name) > 100 or any(ord(character) < 32 for character in name)):
                raise ValueError("controller name must be a safe non-empty string")
            base_url = item.get("base_url")
            if not isinstance(base_url, str):
                raise VendorConfigurationError("ESL_BASE_URL is required")
            config = VendorConfig(
                base_url=base_url,
                username=item.get("username"),
                password=item.get("password"),
                connect_timeout=item.get("connect_timeout", 3),
                read_timeout=item.get("read_timeout", 10),
            )
            folded_name = name.casefold()
            if controller_id in ids or folded_name in names:
                raise ValueError("controller ids and names must be unique")
            if config.base_url in base_urls:
                raise ValueError("controller base URLs must be unique")
            ids.add(controller_id)
            names.add(folded_name)
            base_urls.add(config.base_url)
            validated.append((controller_id, name, config))
        if default_id not in ids:
            raise ValueError("default_controller must identify a configured controller")

        self.default_id = default_id
        self._clients = {
            controller_id: VendorClient(config)
            for controller_id, _name, config in validated
        }
        self._metadata = tuple({
            "id": controller_id,
            "name": name,
            "base_url": config.base_url,
            "default": controller_id == default_id,
        } for controller_id, name, config in validated)

    @classmethod
    def from_settings(cls, settings: dict[str, Any]) -> ControllerRegistry:
        if "controllers" in settings:
            return cls(settings["controllers"], settings["default_controller"])
        controller = {
            "id": "default",
            "name": "Default controller",
            **{field: settings[field] for field in (
                "base_url", "username", "password", "connect_timeout", "read_timeout"
            ) if field in settings},
        }
        return cls([controller], "default")

    def get(self, controller_id: str | None = None) -> VendorClient:
        """Return the stable isolated client for an ID, or the explicit default."""
        selected = self.default_id if controller_id is None else controller_id
        try:
            return self._clients[selected]
        except KeyError as error:
            raise KeyError(f"Unknown controller: {selected}") from error

    def metadata(self) -> list[dict[str, Any]]:
        """Return public controller fields without credentials or client state."""
        return [dict(item) for item in self._metadata]

    def __repr__(self) -> str:
        return f"ControllerRegistry(default_id={self.default_id!r}, controllers={self.metadata()!r})"
