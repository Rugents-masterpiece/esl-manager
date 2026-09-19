"""Safe standard-library adapter for the vendor ESL controller."""

from __future__ import annotations

import base64
import binascii
import hashlib
import http.cookiejar
import json
import math
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
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
        if self.username is not None and (not isinstance(self.username, str) or not self.username):
            raise VendorConfigurationError("ESL_USERNAME must not be empty")
        if self.password is not None and (not isinstance(self.password, str) or not self.password):
            raise VendorConfigurationError("ESL_PASSWORD must not be empty")
        if self.session is not None and (
            not isinstance(self.session, str) or not self.session
            or any(not 33 <= ord(character) <= 126 for character in self.session)
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


def decode_document(raw: bytes | str):
    """Decode nested vendor JSON without discarding envelope metadata."""
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
        return decoded
    return value


def decode_response(raw: bytes | str):
    """Decode a vendor response and unwrap its common datalist envelope."""
    decoded = decode_document(raw)
    if isinstance(decoded, dict) and isinstance(decoded.get("datalist"), list):
        return decoded["datalist"]
    return decoded


class VendorError(RuntimeError):
    """A controller request or response failed."""


class LiveWritesDisabled(VendorError):
    """The two independent live-write guards were not both satisfied."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VendorClient:
    """Small authenticated HTTP client exposing only approved ESL operations."""

    MAX_RESPONSE_BYTES = 8 * 1024 * 1024
    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    MAX_ENCODED_IMAGE_BYTES = ((MAX_IMAGE_BYTES + 2) // 3) * 4

    def __init__(self, config: VendorConfig):
        self.config = config
        self._cookies = http.cookiejar.CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookies), _NoRedirect())
        self._logged_in = False
        self._request_lock = threading.RLock()
        self._last_request_finished = 0.0
        self._minimum_request_gap = 5.0

    def _wait_for_request_slot(self) -> None:
        remaining = self._minimum_request_gap - (time.monotonic() - self._last_request_finished)
        if remaining > 0:
            time.sleep(remaining)

    def _set_read_timeout(self, response) -> None:
        # urllib has one public timeout argument. Set the connected socket separately
        # so a stalled response body uses the configured read timeout.
        try:
            response.fp.raw._sock.settimeout(self.config.read_timeout)
        except AttributeError:
            pass

    def _request_bytes(self, method: str, path: str, body: bytes | None = None,
                       content_type: str | None = None, *, authenticate: bool = True,
                       max_bytes: int | None = None) -> tuple[bytes, str]:
        with self._request_lock:
            if authenticate:
                self._login_if_needed()
            self._wait_for_request_slot()
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
                    limit = self.MAX_RESPONSE_BYTES if max_bytes is None else max_bytes
                    raw = response.read(limit + 1)
                    if response.status >= 400:
                        raise VendorError(f"Vendor returned HTTP {response.status}")
                    response_type = response.headers.get_content_type()
            except HTTPError as error:
                error.close()
                raise VendorError(f"Vendor returned HTTP {error.code}") from error
            except (URLError, TimeoutError, OSError) as error:
                raise VendorError("Vendor request failed") from error
            finally:
                self._last_request_finished = time.monotonic()
            if len(raw) > limit:
                raise VendorError("Vendor response exceeded the configured size limit")
            return raw, response_type

    def _request_document(self, method: str, path: str, body: bytes | None = None,
                          content_type: str | None = None, *, authenticate: bool = True) -> Any:
        raw, _ = self._request_bytes(
            method, path, body, content_type, authenticate=authenticate
        )
        return decode_document(raw)

    def _request(self, method: str, path: str, body: bytes | None = None,
                 content_type: str | None = None, *, authenticate: bool = True) -> Any:
        value = self._request_document(
            method, path, body, content_type, authenticate=authenticate
        )
        if isinstance(value, dict) and isinstance(value.get("datalist"), list):
            return value["datalist"]
        return value

    def _login_if_needed(self) -> None:
        if self.config.session or self._logged_in or not self.config.username:
            return
        assert self.config.password is not None
        body = urlencode({
            "name": self.config.username,
            "passwd": hashlib.md5(self.config.password.encode()).hexdigest(),
        }).encode("ascii")
        result = self._request(
            "POST", "/login/userLogin", body,
            "application/x-www-form-urlencoded; charset=UTF-8", authenticate=False,
        )
        login_succeeded = result is True or (
            isinstance(result, str)
            and re.search(r"href=[\"'][^\"']*login/logout(?:[?\"'])", result) is not None
        )
        if not login_succeeded:
            raise VendorError("Vendor login failed")
        if not any(cookie.name == "JSESSIONID" for cookie in self._cookies):
            raise VendorError("Vendor login did not provide a session cookie")
        probe = self._request(
            "GET", "/mms/queryRouters?currentPage=0&routerId=0", authenticate=False
        )
        self._collection(probe, "authentication probe")
        self._logged_in = True

    @staticmethod
    def _collection(value: Any, resource: str) -> list[dict[str, Any]]:
        if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
            raise VendorError(f"Invalid vendor {resource} response")
        return value

    def get_routers(self) -> list[dict[str, Any]]:
        return self._collection(
            self._request("GET", "/mms/queryRouters?currentPage=0&routerId=0"),
            "routers",
        )

    def get_templates(self) -> list[dict[str, Any]]:
        return self._collection(
            self._request("GET", "/mms/queryStyles?currentPage=0&templateType=0"),
            "templates",
        )

    def get_tags(self) -> list[dict[str, Any]]:
        tags: list[dict[str, Any]] = []
        seen: set[str] = set()
        page_fingerprints: set[tuple[str, ...]] = set()
        for page in range(1, 101):
            collection = self._collection(
                self._request(
                    "GET",
                    f"/mms/queryTags?currentPage={page}&tagMac=0&routerMac=0&startTime=&endTime=&templateType=0",
                ),
                "tags",
            )
            fingerprint = tuple(str(item.get("mac") or item.get("id")) for item in collection)
            if not collection or fingerprint in page_fingerprints:
                return tags
            page_fingerprints.add(fingerprint)
            for item in collection:
                identity = str(item.get("mac") or item.get("id"))
                if identity not in seen:
                    seen.add(identity)
                    tags.append(item)
        raise VendorError("Vendor tag pagination exceeded 100 pages")

    @staticmethod
    def _documented_collection(value: Any, resource: str) -> list[dict[str, Any]]:
        if not isinstance(value, dict) or value.get("resultCode") != 10:
            raise VendorError(f"Invalid vendor {resource} response")
        items = value.get("datalist")
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise VendorError(f"Invalid vendor {resource} response")
        return items

    @staticmethod
    def _resource_name(value: Any, field: str) -> str:
        if (not isinstance(value, str) or not value.strip() or len(value.strip()) > 200
                or any(ord(character) < 32 or character in "/\\?#" for character in value)):
            raise VendorError(f"Invalid vendor {field}")
        return value.strip()

    @staticmethod
    def _image_type(data: bytes) -> str | None:
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith((b"GIF87a", b"GIF89a")):
            return "image/gif"
        if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        if data.startswith(b"BM"):
            return "image/bmp"
        return None

    def get_extended_tags(self) -> list[dict[str, Any]]:
        value = self._request_document("GET", "/associate/getTagsMsg")
        return self._collection(value, "extended tags")

    def get_style_catalog(self) -> list[dict[str, Any]]:
        value = self._request_document("GET", "/associate/getStyleMsgs")
        return self._documented_collection(value, "style catalog")

    def get_style_detail(self, style_id: int) -> dict[str, Any]:
        if isinstance(style_id, bool) or not isinstance(style_id, int) or style_id < 0:
            raise VendorError("Invalid vendor style id")
        body = json.dumps({"id": style_id}, separators=(",", ":")).encode("utf-8")
        value = self._request_document(
            "POST", f"/associate/getStyleMsgById?id={style_id}", body,
            "application/json; charset=UTF-8",
        )
        items = self._documented_collection(value, "style detail")
        if len(items) != 1 or items[0].get("id") != style_id:
            raise VendorError("Invalid vendor style detail response")
        return items[0]

    def get_photos(self) -> list[dict[str, Any]]:
        value = self._request_document("GET", "/associate/getPhotos")
        return self._documented_collection(value, "photos")

    def get_photo_data(self, photo_name: str) -> tuple[bytes, str]:
        name = self._resource_name(photo_name, "photo name")
        value = self._request_document(
            "GET", "/associate/getPhotoDataByName?" + urlencode({"photoName": name})
        )
        if not isinstance(value, dict) or value.get("resultCode") != 10:
            raise VendorError("Invalid vendor photo data response")
        encoded = value.get("data")
        duplicate = value.get("t")
        if (not isinstance(encoded, str) or not encoded
                or len(encoded) > self.MAX_ENCODED_IMAGE_BYTES):
            raise VendorError("Invalid vendor photo data response")
        if duplicate not in (None, encoded):
            raise VendorError("Vendor photo data fields disagree")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as error:
            raise VendorError("Invalid vendor photo encoding") from error
        if not data or len(data) > self.MAX_IMAGE_BYTES:
            raise VendorError("Vendor photo exceeded the configured size limit")
        media_type = self._image_type(data)
        if media_type is None:
            raise VendorError("Vendor photo is not a supported image")
        return data, media_type

    def get_template_preview(self, style_id: int) -> tuple[bytes, str]:
        detail = self.get_style_detail(style_id)
        name = self._resource_name(detail.get("name"), "style name")
        path = "/" + quote(f"{name}{style_id}.png", safe="")
        data, declared_type = self._request_bytes(
            "GET", path, max_bytes=self.MAX_IMAGE_BYTES
        )
        detected_type = self._image_type(data)
        if (not declared_type.startswith("image/") or detected_type is None
                or declared_type != detected_type):
            raise VendorError("Vendor preview is not a valid image")
        return data, detected_type

    def update_screen(self, updates: list[dict[str, Any]], confirmation: str) -> list[dict[str, Any]]:
        """Dispatch updates only when double-gated, then confirm status by read-back."""
        if not live_writes_authorized(confirmation):
            raise LiveWritesDisabled("Live ESL writes are disabled or not explicitly confirmed")
        requested_macs = {item.get("mac") for item in updates}
        before_by_mac = {item.get("mac"): item for item in self.get_tags()}
        if any(mac not in before_by_mac for mac in requested_macs):
            raise VendorError("Vendor preflight could not find every requested tag")
        before_status = {
            mac: self._update_status(before_by_mac[mac]) for mac in requested_macs
        }
        if any(status is None for status in before_status.values()):
            raise VendorError("Vendor preflight returned an invalid tag status")
        body = json.dumps(updates, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        accepted = self._request("POST", "/associate/updateScreen", body, "application/json")
        if accepted is not True:
            raise VendorError("Vendor did not accept the display update")
        tags_by_mac = {item.get("mac"): item for item in self.get_tags()}
        verified = []
        for mac in requested_macs:
            tag = tags_by_mac.get(mac)
            if tag is None:
                raise VendorError(f"Vendor read-back did not confirm tag {mac}")
            current_status = self._update_status(tag)
            if current_status not in {2, 4} or current_status == before_status[mac]:
                raise VendorError(f"Vendor read-back did not confirm tag {mac}")
            verified.append({
                **tag,
                "_verified_status": "updating" if current_status == 2 else "success",
            })
        return sorted(verified, key=lambda item: str(item.get("mac")))

    @staticmethod
    def _update_status(item: dict[str, Any] | None) -> int | None:
        if item is None:
            return None
        value = item.get("updateProgress")
        if value is None:
            value = item.get("status")
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
            return None
        if isinstance(value, str) and re.fullmatch(r"[+-]?\d+", value.strip()) is None:
            return None
        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return result if result in {0, 1, 2, 3, 4, 5} else None
