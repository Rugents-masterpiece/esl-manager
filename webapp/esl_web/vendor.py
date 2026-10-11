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

    def get_tag_display(self, mac: str) -> dict[str, Any]:
        """Read controller metadata, never claim a physical screen read-back."""
        from .service import Service, IntegrationError
        try:
            identity = Service._vendor_tag_identity(mac)
            indexed = Service._index_vendor_tags(self.get_tags(), 'display tags')
            row = indexed.get(identity)
            if row is None:
                raise VendorError('Controller did not find the requested tag')
            raw_id = row.get('id')
            if isinstance(raw_id, bool) or re.fullmatch(r'[1-9][0-9]{0,9}', str(raw_id)) is None:
                raise VendorError('Invalid controller tag id')
            tag_id = self._style_id(int(str(raw_id)))
            value = self._request_document('GET', f'/tag/getTagById?id={tag_id}')
            tag = value.get('tag') if isinstance(value, dict) else None
            if (not isinstance(tag, dict) or tag.get('id') != tag_id
                    or Service._vendor_tag_identity(tag.get('mac')) != identity):
                raise VendorError('Controller tag detail identity differs')
            width, height = tag.get('width'), tag.get('height')
            if any(type(n) is not int or not 1 <= n <= 1024 for n in (width, height)):
                raise VendorError('Invalid controller display dimensions')
            style_id = tag.get('styleid')
            if style_id in (None, 0):
                style_id = None
            else:
                style_id = self._style_id(style_id)
            updated = tag.get('updatetime')
            if updated is not None and (type(updated) is not int or not 0 <= updated <= 8640000000000000):
                raise VendorError('Invalid controller display timestamp')
            native = tag.get('tagAndGood')
            if native is not None and not isinstance(native, dict):
                raise VendorError('Invalid controller native transmission metadata')
            native = native or {}
            native_updated = native.get('timestamp')
            if native_updated is not None and (type(native_updated) is not int
                    or not 0 <= native_updated <= 8640000000000000):
                raise VendorError('Invalid controller native transmission timestamp')
            return {'mac': identity, 'vendor_tag_id': tag_id, 'width': width, 'height': height,
                    'style_id': style_id, 'update_progress': self._update_status(tag),
                    'updated_at_ms': updated, 'physical_screen_verified': False,
                    'native_update_progress': self._update_status({'status': native.get('status')}),
                    'native_updated_at_ms': native_updated,
                    'native_update_source': 'tag.tagAndGood',
                    'image_source': 'controller_template_preview'}
        except IntegrationError as error:
            raise VendorError('Invalid controller tag identity') from error

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

    @staticmethod
    def _style_id(style_id: Any) -> int:
        if (isinstance(style_id, bool) or not isinstance(style_id, int)
                or not 0 < style_id <= 2_147_483_647):
            raise VendorError("Invalid vendor style id")
        return style_id

    @staticmethod
    def _layout(value: Any) -> list[dict[str, Any]]:
        if isinstance(value, str):
            value = decode_document(value)
        if (not isinstance(value, list) or len(value) > 500
                or any(not isinstance(item, dict) for item in value)):
            raise VendorError("Invalid vendor style layout response")
        return value

    def get_style_layout(self, style_id: int) -> list[dict[str, Any]]:
        style_id = self._style_id(style_id)
        value = self._request_document(
            "POST", f"/style/getDispMsData?id={style_id}", b"{}",
            "application/json; charset=UTF-8",
        )
        return self._layout(value)

    def get_style_data(self, style_id: int) -> dict[str, Any]:
        style_id = self._style_id(style_id)
        value = self._request_document("GET", f"/style/getStyleData?id={style_id}")
        if isinstance(value, dict) and "datalist" in value:
            items = self._documented_collection(value, "style data")
            if len(items) != 1:
                raise VendorError("Invalid vendor style data response")
            value = items[0]
        if not isinstance(value, dict) or value.get("id") != style_id:
            raise VendorError("Invalid vendor style data response")
        return value

    def create_style(self, style_align_id: int) -> int:
        style_align_id = self._style_id(style_align_id)
        value = self._request_document(
            "GET", f"/mms/addStyles?id=0&stylealignId={style_align_id}"
        )
        candidates: list[Any]
        if isinstance(value, dict):
            candidates = [value.get("id"), value.get("styleid"), value.get("styleId")]
        elif isinstance(value, str):
            candidates = re.findall(
                r"id=[\"']sytleId[\"'][^>]*\bvalue=[\"'](\d{1,10})[\"']",
                value,
                flags=re.IGNORECASE,
            )
        else:
            candidates = []
        ids = {
            int(candidate) for candidate in candidates
            if not isinstance(candidate, bool)
            and isinstance(candidate, (int, str))
            and re.fullmatch(r"\d{1,10}", str(candidate))
            and 0 < int(candidate) <= 2_147_483_647
        }
        if len(ids) != 1:
            raise VendorError("Vendor create response did not identify one style")
        return ids.pop()

    def add_style_field(self, style_id: int, mapping_type: int, column_name: str,
                        mapping_text: str) -> Any:
        style_id = self._style_id(style_id)
        mapping_type = self._style_id(mapping_type)
        column = self._resource_name(column_name, "column name")
        mapping = self._resource_name(mapping_text, "mapping text")
        path = "/style/addColumnAndGood?" + urlencode({
            "columnName": column, "mappingText": mapping,
            "mappingtype": mapping_type, "styleid": style_id,
        })
        return self._request_document(
            "POST", path, b"{}", "application/json; charset=UTF-8"
        )

    def rename_style(self, style_id: int, style_align_id: int, target_name: str) -> Any:
        style_id = self._style_id(style_id)
        style_align_id = self._style_id(style_align_id)
        name = self._resource_name(target_name, "style name")
        path = "/style/updateStyleAlign?" + urlencode({
            "styleid": style_id, "stylealign": style_align_id, "styleName": name,
        })
        return self._request_document(
            "POST", path, b"{}", "application/json; charset=UTF-8"
        )

    def save_style_layout(self, style_id: int, layout: list[dict[str, Any]]) -> Any:
        style_id = self._style_id(style_id)
        layout = self._layout(layout)
        order_json = json.dumps(layout, ensure_ascii=False, separators=(",", ":"))
        body = urlencode({"orderJson": order_json}).encode("utf-8")
        return self._request_document(
            "POST", f"/mms/updateDispMData?id={style_id}", body,
            "application/x-www-form-urlencoded; charset=UTF-8",
        )

    def delete_style(self, style_id: int) -> None:
        style_id = self._style_id(style_id)
        value = self._request_document("GET", f"/style/deleteStyles?styleid={style_id}")
        if not isinstance(value, dict) or value.get("resultCode") != 10:
            raise VendorError("Vendor did not confirm style deletion")

    def get_photos(self) -> list[dict[str, Any]]:
        value = self._request_document("GET", "/associate/getPhotos")
        return self._documented_collection(value, "photos")

    def upload_photo(self, name: str, data: bytes, width: int, height: int) -> dict[str, Any]:
        """Create a named PNG once; reconcile the exact target after any outcome."""
        if (not isinstance(name, str)
                or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}', name) is None
                or not isinstance(data, bytes)
                or type(width) is not int or type(height) is not int
                or not 1 <= width <= 1024 or not 1 <= height <= 1024):
            raise VendorError('Invalid native photo upload')
        from .drafts import _png
        try:
            _png('data:image/png;base64,' + base64.b64encode(data).decode('ascii'))
        except Exception as error:
            raise VendorError('Invalid native photo PNG') from error
        if (int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')) != (width, height):
            raise VendorError('Native photo dimensions disagree')

        def verify(rows):
            targets = [row for row in rows if row.get('name') == name]
            if len(targets) != 1 or (targets[0].get('width'), targets[0].get('height')) != (width, height):
                raise VendorError('Native photo metadata could not be verified')
            actual, media_type = self.get_photo_data(name)
            if actual != data or media_type != 'image/png':
                raise VendorError('Native photo content could not be verified')
            return {'name': name, 'width': width, 'height': height,
                    'content_exact': True, 'sha256': hashlib.sha256(actual).hexdigest()}

        with self._request_lock:
            before = self.get_photos()
            if any(row.get('name') == name for row in before):
                return verify(before)
            boundary = 'esl-' + os.urandom(24).hex()
            parts = []
            for field, value in (('name', name), ('width', str(width)), ('height', str(height))):
                parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"'
                              f'\r\n\r\n{value}\r\n').encode('ascii'))
            parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="photo"; '
                          f'filename="{name}.png"\r\nContent-Type: image/png\r\n\r\n').encode('ascii'))
            parts.append(data)
            # Match the native form: the optional red-plane file part exists
            # even when no file is selected. Some legacy handlers dereference it.
            parts.append((f'\r\n--{boundary}\r\nContent-Disposition: form-data; '
                          'name="redphoto"; filename=""\r\n'
                          'Content-Type: application/octet-stream\r\n\r\n').encode('ascii'))
            parts.append(f'\r\n--{boundary}--\r\n'.encode('ascii'))
            try:
                self._request_document('POST', '/style/uploadPhoto', b''.join(parts),
                                       f'multipart/form-data; boundary={boundary}')
            except VendorError:
                # A timeout or error may follow a successful mutation; do not retry.
                pass
            return verify(self.get_photos())

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
        """Send the native array once; verify fresh native transmission, not MMS assignment."""
        if not live_writes_authorized(confirmation):
            raise LiveWritesDisabled("Live ESL writes are disabled or not explicitly confirmed")
        # Import lazily: the service imports the write gate from this module.
        from .service import IntegrationError, Service

        try:
            requested_macs = {
                Service._vendor_tag_identity(item.get("mac")) for item in updates
            }
            if len(requested_macs) != len(updates):
                raise VendorError("Duplicate requested vendor tag identity")
        except IntegrationError as error:
            raise VendorError("Vendor preflight returned invalid tag identities") from error
        before_by_mac = {mac: self.get_tag_display(mac) for mac in sorted(requested_macs)}
        for mac, tag in before_by_mac.items():
            if (tag.get('mac') != mac or type(tag.get('native_update_progress')) is not int
                    or tag['native_update_progress'] not in {0, 1, 3, 4, 5}):
                raise VendorError("Vendor preflight returned an invalid or already-updating native tag status")
            timestamp = tag.get('native_updated_at_ms')
            if type(timestamp) is not int or not 0 <= timestamp <= 8640000000000000:
                raise VendorError("Vendor preflight returned an invalid native transmission timestamp")
        # Captured modern component.js emits an array without ABDisplayFlag.
        # Legacy A/B flags and JSON-string wrapping can be accepted but ignored.
        wire_updates = [{key: value for key, value in item.items() if key != 'ABDisplayFlag'}
                        for item in updates]
        body = json.dumps(wire_updates, ensure_ascii=False, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
        # Recheck the process gate immediately before the only physical mutation.
        if not live_writes_authorized(confirmation):
            raise LiveWritesDisabled("Live ESL writes are disabled or not explicitly confirmed")
        accepted = self._request("POST", "/associate/updateScreen", body, "application/json")
        if accepted is not True:
            raise VendorError("Vendor did not accept the display update")
        verified = []
        for mac in sorted(requested_macs):
            tag = self.get_tag_display(mac)
            before = before_by_mac[mac]
            current_status = tag.get('native_update_progress')
            timestamp = tag.get('native_updated_at_ms')
            previous_timestamp = before.get('native_updated_at_ms')
            fresh_timestamp = (type(timestamp) is int and type(previous_timestamp) is int
                               and 0 <= timestamp <= 8640000000000000
                               and timestamp > previous_timestamp)
            if (tag.get('mac') != mac or type(current_status) is not int
                    or current_status not in {2, 4}
                    or not fresh_timestamp):
                raise VendorError(f"Vendor read-back did not confirm tag {mac}")
            verified.append({
                **tag,
                "_verified_status": "updating" if current_status == 2 else "success",
            })
        return verified

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
