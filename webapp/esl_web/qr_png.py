"""Deterministic offline QR PNGs, without imaging or network dependencies.

UTF-8 byte mode with ECI 26 makes non-ASCII payloads unambiguous. Error
correction is exact (never boosted). The four-module quiet zone is included
before integer scaling and centered on the requested white canvas.
"""
import binascii
import struct
import zlib

from ._vendor.qrcodegen import QrCode, QrSegment

__all__ = ["qr_png"]


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", binascii.crc32(kind + payload) & 0xffffffff))


def qr_png(text: str, width: int, height: int, error_correction: str = "M") -> bytes:
    """Render UTF-8 text to a grayscale PNG with exact L/M/Q/H correction.

    Raises ValueError for invalid dimensions, level, capacity, or insufficient
    canvas space; raises TypeError for a non-string payload. Dimensions are
    integer pixels (bool is not accepted), from 1 through 1024 inclusive.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    for name, value in (("width", width), ("height", height)):
        if type(value) is not int or not 1 <= value <= 1024:
            raise ValueError(f"{name} must be an integer from 1 through 1024")
    if not isinstance(error_correction, str) or error_correction not in ("L", "M", "Q", "H"):
        raise ValueError("error_correction must be exactly L, M, Q, or H")
    levels = {"L": QrCode.Ecc.LOW, "M": QrCode.Ecc.MEDIUM,
              "Q": QrCode.Ecc.QUARTILE, "H": QrCode.Ecc.HIGH}
    segments = [QrSegment.make_eci(26), QrSegment.make_bytes(text.encode("utf-8"))]
    qr = QrCode.encode_segments(segments, levels[error_correction], boostecl=False)
    size = qr.get_size()
    scale = min(width, height) // (size + 8)
    if scale < 1:
        raise ValueError(f"QR matrix and quiet zone require at least {size + 8} pixels per side")
    left = (width - size * scale) // 2
    top = (height - size * scale) // 2
    white = bytes([255]) * width
    rows = []
    for y in range(height):
        row = bytearray(white)
        module_y = (y - top) // scale
        if 0 <= module_y < size:
            for x in range(size):
                if qr.get_module(x, module_y):
                    start = left + x * scale
                    row[start:start + scale] = bytes(scale)
        rows.append(b"\x00" + row)
    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header)
            + _chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
            + _chunk(b"IEND", b""))
