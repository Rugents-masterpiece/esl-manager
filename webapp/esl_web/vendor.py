"""Safe standard-library adapter for the vendor ESL controller."""

from __future__ import annotations

import hashlib
import http.cookiejar
import json
import math
import os
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import (
    HTTPCookieProcessor,
    HTTPRedirectHandler,
    Request,
    build_opener,
)


class VendorConfigurationError(ValueError):
    """The vendor integration environment is incomplete or unsafe."""


LIVE_WRITE_CONFIRMATION = "I CONFIRM LIVE ESL UPDATE"


def live_writes_authorized(confirmation: object) -> bool:
    return os.environ.get("ESL_LIVE_WRITES") == "1" and confirmation == LIVE_WRITE_CONFIRMATION


def _validate_timeout(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VendorConfigurationError(f"{name} must be a positive number")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise VendorConfigurationError(f"{name} must be a positive number")
    return result


def _positive_timeout(environment: Mapping[str, str], name: str, default: float) -> float:
    raw = environment.get(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError as error:
        raise VendorConfigurationError(f"{name} must be a positive number") from error
    return _validate_timeout(value, name)


def validate_base_url(value: str | None) -> str:
    """Return a canonical controller URL after rejecting ambiguous URL forms."""
    if not value or not isinstance(value, str):
        raise VendorConfigurationError("ESL_BASE_URL is required")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as error:
        raise VendorConfigurationError("ESL_BASE_URL is invalid") from error
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise VendorConfigurationError("ESL_BASE_URL must use http or https and include a host")
    if parsed.username is not None or parsed.password is not None:
        raise VendorConfigurationError("ESL_BASE_URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise VendorConfigurationError("ESL_BASE_URL must not contain a query or fragment")
    if any(ord(character) < 33 or ord(character) == 127 for character in value):
        raise VendorConfigurationError("ESL_BASE_URL contains invalid characters")
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    netloc = host if port is None else f"{host}:{port}"
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme.lower(), netloc, path, "", ""))


@dataclass(frozen=True)
class VendorConfig:
    base_url: str
    username: str | None = None
    password: str | None = None
    session: str | None = None
    connect_timeout: float = 3.0
    read_timeout: float = 10.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_url", validate_base_url(self.base_url))
        object.__setattr__(self, "connect_timeout", _validate_timeout(
            self.connect_timeout, "ESL_CONNECT_TIMEOUT"
        ))
        object.__setattr__(self, "read_timeout", _validate_timeout(
            self.read_timeout, "ESL_READ_TIMEOUT"
        ))
        if (self.username is None) != (self.password is None):
            raise VendorConfigurationError("ESL_USERNAME and ESL_PASSWORD must be configured together")
        if self.username is not None and not self.username:
            raise VendorConfigurationError("ESL_USERNAME must not be empty")
        if self.password is not None and not self.password:
            raise VendorConfigurationError("ESL_PASSWORD must not be empty")
        if self.session is not None and (
            not self.session or any(not 33 <= ord(character) <= 126 for character in self.session)
        ):
            raise VendorConfigurationError("ESL_SESSION contains invalid characters")

    @classmethod
    def from_env(cls, environment: Mapping[str, str] | None = None) -> VendorConfig:
        env = os.environ if environment is None else environment
        username = env.get("ESL_USERNAME") or None
        password = env.get("ESL_PASSWORD") or None
        if (username is None) != (password is None):
            raise VendorConfigurationError("ESL_USERNAME and ESL_PASSWORD must be configured together")
        return cls(
            base_url=validate_base_url(env.get("ESL_BASE_URL")),
            username=username,
            password=password,
            session=env.get("ESL_SESSION") or None,
            connect_timeout=_positive_timeout(env, "ESL_CONNECT_TIMEOUT", 3.0),
            read_timeout=_positive_timeout(env, "ESL_READ_TIMEOUT", 10.0),
        )


def decode_response(raw: bytes | str):
    """Decode the inconsistent response shapes returned by the ESL controller."""
    if isinstance(raw, bytes):
        text = raw.decode("utf-8")
    elif isinstance(raw, str):
        text = raw
    else:
        raise TypeError("Vendor response must be bytes or text")
    value = text.strip()
    for _ in range(2):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return value
        if isinstance(decoded, str):
            value = decoded
            continue
        if isinstance(decoded, dict) and isinstance(decoded.get("datalist"), list):
            return decoded["datalist"]
        return decoded
    return value


class VendorError(RuntimeError):
    """A controller request or response failed."""


class LiveWritesDisabled(VendorError):
    """The two independent live-write guards were not both satisfied."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VendorClient:
    """Small authenticated HTTP client exposing only approved ESL operations."""

    def __init__(self, config: VendorConfig):
        self.config = config
        self._cookies = http.cookiejar.CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookies), _NoRedirect())
        self._logged_in = False

    def _set_read_timeout(self, response) -> None:
        # urllib has one public timeout argument. Set the connected socket separately
        # so a stalled response body uses the configured read timeout.
        try:
            response.fp.raw._sock.settimeout(self.config.read_timeout)
        except AttributeError:
            pass

    def _request(self, method: str, path: str, body: bytes | None = None,
                 content_type: str | None = None, *, authenticate: bool = True) -> Any:
        if authenticate:
            self._login_if_needed()
        request = Request(self.config.base_url + path, data=body, method=method)
        request.add_header("Accept", "application/json, text/plain, */*")
        request.add_header("X-Requested-With", "XMLHttpRequest")
        if content_type:
            request.add_header("Content-Type", content_type)
        if self.config.session:
            request.add_header("Cookie", f"JSESSIONID={self.config.session}")
        try:
            with self._opener.open(request, timeout=self.config.connect_timeout) as response:
                self._set_read_timeout(response)
                raw = response.read()
                if response.status >= 400:
                    raise VendorError(f"Vendor returned HTTP {response.status}")
        except HTTPError as error:
            error.close()
            raise VendorError(f"Vendor returned HTTP {error.code}") from error
        except (URLError, TimeoutError, OSError) as error:
            raise VendorError("Vendor request failed") from error
        return decode_response(raw)

    def _login_if_needed(self) -> None:
        if self.config.session or self._logged_in or not self.config.username:
            return
        assert self.config.password is not None
        body = urlencode({
            "username": self.config.username,
            "passwd": hashlib.md5(self.config.password.encode()).hexdigest(),
        }).encode("ascii")
        result = self._request(
            "POST", "/login/userLogin", body,
            "application/x-www-form-urlencoded; charset=UTF-8", authenticate=False,
        )
        if result is not True:
            raise VendorError("Vendor login failed")
        if not any(cookie.name == "JSESSIONID" for cookie in self._cookies):
            raise VendorError("Vendor login did not provide a session cookie")
        self._logged_in = True

    @staticmethod
    def _collection(value: Any, resource: str) -> list[dict[str, Any]]:
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise VendorError(f"Invalid vendor {resource} response")
        return value

    def get_routers(self) -> list[dict[str, Any]]:
        return self._collection(self._request("GET", "/associate/getRoutersMsg"), "routers")

    def get_templates(self) -> list[dict[str, Any]]:
        return self._collection(self._request("GET", "/associate/getStyleMsgs"), "templates")

    def get_tags(self) -> list[dict[str, Any]]:
        return self._collection(self._request("GET", "/associate/getTagsMsg"), "tags")

    def update_screen(self, updates: list[dict[str, Any]], confirmation: str) -> list[dict[str, Any]]:
        """Dispatch updates only when double-gated, then confirm status by read-back."""
        if not live_writes_authorized(confirmation):
            raise LiveWritesDisabled("Live ESL writes are disabled or not explicitly confirmed")
        body = json.dumps(updates, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        accepted = self._request("POST", "/associate/updateScreen", body, "application/json")
        if accepted is not True:
            raise VendorError("Vendor did not accept the display update")
        requested_macs = {item.get("mac") for item in updates}
        tags_by_mac = {item.get("mac"): item for item in self.get_tags()}
        verified = []
        for mac in requested_macs:
            tag = tags_by_mac.get(mac)
            if tag is None or tag.get("status") not in {2, 4, "2", "4"}:
                raise VendorError(f"Vendor read-back did not confirm tag {mac}")
            verified.append(tag)
        return sorted(verified, key=lambda item: str(item.get("mac")))
