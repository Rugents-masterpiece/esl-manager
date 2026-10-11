"""Offline renderer contracts; ZXing is optional and development-only."""
import binascii
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "webapp"))


def unpack_png(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, []
    while pos < len(data):
        size = struct.unpack_from(">I", data, pos)[0]
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + size]
        crc = struct.unpack_from(">I", data, pos + 8 + size)[0]
        assert crc == binascii.crc32(kind + payload) & 0xffffffff
        chunks.append((kind, payload))
        pos += size + 12
    assert pos == len(data)
    assert [kind for kind, _ in chunks] == [b"IHDR", b"IDAT", b"IEND"]
    width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    assert (depth, color, compression, filtering, interlace) == (8, 0, 0, 0, 0)
    assert chunks[-1][1] == b""
    raw = zlib.decompress(chunks[1][1])
    assert len(raw) == (width + 1) * height
    rows = []
    for y in range(height):
        start = y * (width + 1)
        assert raw[start] == 0
        rows.append(raw[start + 1:start + width + 1])
    assert all(set(row) <= {0, 255} for row in rows)
    return width, height, rows


class QrPngTests(unittest.TestCase):
    def renderer(self):
        self.assertTrue((ROOT / "webapp/esl_web/qr_png.py").is_file(), "renderer not implemented")
        return importlib.import_module("esl_web.qr_png").qr_png

    def test_reject_invalid_dimensions(self):
        render = self.renderer()
        for value in (0, -1, 1025, True, False, 29.0, "100", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    render("a", value, 100)
                with self.assertRaises(ValueError):
                    render("a", 100, value)

    def test_reject_canvas_too_small(self):
        render = self.renderer()
        for width, height in ((1, 1), (28, 100), (100, 28)):
            with self.subTest(width=width, height=height):
                with self.assertRaises(ValueError):
                    render("a", width, height)
        self.assertEqual(unpack_png(render("a", 29, 29))[:2], (29, 29))

    def test_reject_invalid_payload_and_level(self):
        render = self.renderer()
        for text in (None, 42, b"abc"):
            with self.subTest(text=text), self.assertRaises(TypeError):
                render(text, 100, 100)
        for level in ("m", "", "X", None, [], 1):
            with self.subTest(level=level), self.assertRaises(ValueError):
                render("a", 100, 100, level)
        with self.assertRaises(ValueError):
            render("\ud800", 100, 100)

    def test_reject_excess_capacity(self):
        with self.assertRaises(ValueError):
            self.renderer()("x" * 3000, 1024, 1024)

    def test_integer_centered_scaling_and_quiet_zone(self):
        from esl_web._vendor.qrcodegen import QrCode, QrSegment
        render = self.renderer()
        for text, width, height in (("a", 29, 29), ("a", 100, 131), ("Žluťoučký 🛒 漢字", 173, 121), ("", 1024, 1024)):
            with self.subTest(text=text, width=width, height=height):
                qr = QrCode.encode_segments([QrSegment.make_eci(26), QrSegment.make_bytes(text.encode("utf-8"))], QrCode.Ecc.MEDIUM, boostecl=False)
                size = qr.get_size()
                scale = min(width, height) // (size + 8)
                left, top = (width - size * scale) // 2, (height - size * scale) // 2
                _, _, rows = unpack_png(render(text, width, height))
                black = [(x, y) for y, row in enumerate(rows) for x, pixel in enumerate(row) if pixel == 0]
                self.assertEqual((min(x for x, y in black), min(y for x, y in black), max(x for x, y in black), max(y for x, y in black)), (left, top, left + size * scale - 1, top + size * scale - 1))
                self.assertGreaterEqual(min(left, top, width - left - size * scale, height - top - size * scale), 4 * scale)
                for y, row in enumerate(rows):
                    expected = bytearray([255]) * width
                    my = (y - top) // scale
                    if 0 <= my < size:
                        for mx in range(size):
                            if qr.get_module(mx, my):
                                expected[left + mx * scale:left + (mx + 1) * scale] = bytes(scale)
                    self.assertEqual(row, expected)

    def test_exact_ecc_format_bits(self):
        # Inspect QR format information, independently of the encoder API.
        # Short payloads would be boosted to H by the upstream default.
        render = self.renderer()
        for level, bits in (("L", 1), ("M", 0), ("Q", 3), ("H", 2)):
            with self.subTest(level=level):
                _, _, rows = unpack_png(render("a", 29, 29, level))
                coords = [(8, y) for y in range(6)] + [(8, 7), (8, 8), (7, 8)] + [(14 - i, 8) for i in range(9, 15)]
                masked = sum((rows[y + 4][x + 4] == 0) << i for i, (x, y) in enumerate(coords))
                code = masked ^ 0x5412
                self.assertEqual(code >> 13, bits)
                remainder = code >> 10
                for _ in range(10):
                    remainder = (remainder << 1) ^ ((remainder >> 9) * 0x537)
                self.assertEqual(code & 0x3ff, remainder)
        self.assertEqual(render("a", 29, 29), render("a", 29, 29, "M"))

    def test_large_utf8_capacity(self):
        render = self.renderer()
        self.assertEqual(unpack_png(render("x" * 2300, 1024, 1024))[:2], (1024, 1024))
        for text in ("x" * 2400, "🛒" * 600):
            with self.subTest(length=len(text)), self.assertRaises(ValueError):
                render(text, 1024, 1024)
        with self.assertRaises(ValueError):
            render("x" * 100, 29, 29)

    def test_stdlib_only_isolated_runtime(self):
        script = '''import sys
sys.path.insert(0, sys.argv[1])
from esl_web.qr_png import qr_png
assert qr_png("Ž 🛒", 120, 120).startswith(b"\\x89PNG")
assert not any(n.split(".")[0] in {"PIL", "numpy", "qrcode", "zxingcpp", "requests"} for n in sys.modules)
print("stdlib-only OK")
'''
        proc = subprocess.run([sys.executable, "-I", "-S", "-c", script, str(ROOT / "webapp")], capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("stdlib-only OK", proc.stdout)

    def test_vendored_source_hash_and_license(self):
        import hashlib
        vendor = ROOT / "webapp/esl_web/_vendor"
        manifest = json.loads((vendor / "qrcodegen-manifest.json").read_text())
        self.assertEqual(manifest["commit"], "3c6d0b3cefb4e049dc337e82237c9644399716a8")
        data = (vendor / "qrcodegen.py").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), manifest["files"]["qrcodegen.py"]["sha256"])
        self.assertIn(b"Copyright (c) Project Nayuki. (MIT License)", data)
        self.assertIn("Permission is hereby granted", (vendor / "qrcodegen-LICENSE.txt").read_text())

    def test_independent_zxing_payload_and_exact_ecc(self):
        python = Path("/tmp/esl-media-decode-venv/bin/python")
        if not python.is_file():
            self.skipTest("optional development ZXing environment unavailable")
        probe = subprocess.run([str(python), "-c", "import zxingcpp; from PIL import Image"], capture_output=True, timeout=30)
        if probe.returncode:
            self.skipTest("optional development ZXing/Pillow unavailable")
        render = self.renderer()
        script = '''import json, sys, zxingcpp
from PIL import Image
with Image.open(sys.argv[1]) as image:
    result = zxingcpp.read_barcode(image)
assert result is not None, "ZXing failed to decode"
print(json.dumps({"text": result.text, "ec_level": result.ec_level}))
'''
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "qr.png"
            for text in ("a", "https://example.test/product/42?price=3.50&store=7", "Žluťoučký 🛒 漢字"):
                for level in ("L", "M", "Q", "H"):
                    with self.subTest(text=text, level=level):
                        image.write_bytes(render(text, 320, 240, level))
                        result = subprocess.run([str(python), "-c", script, str(image)], capture_output=True, text=True, timeout=30)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(json.loads(result.stdout), {"text": text, "ec_level": level})

    def test_valid_deterministic_png(self):
        render = self.renderer()
        data = render("https://example.test/product/42", 160, 120)
        self.assertIsInstance(data, bytes)
        self.assertEqual(data, render("https://example.test/product/42", 160, 120))
        width, height, rows = unpack_png(data)
        self.assertEqual((width, height), (160, 120))
        self.assertTrue(any(0 in row for row in rows))


if __name__ == "__main__":
    unittest.main()
