"""Offline, dependency-free contracts for the native rectangle compositing adapter."""
import importlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'webapp'))
from esl_web.drafts import DraftService


def decode_rgba(data):
    """Independently check PNG chunks, CRCs, geometry, and unfiltered RGBA rows."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    chunks = []
    offset = 8
    while offset < len(data):
        size = struct.unpack_from('>I', data, offset)[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + size]
        crc = struct.unpack_from('>I', data, offset + 8 + size)[0]
        assert crc == zlib.crc32(kind + payload)
        chunks.append((kind, payload))
        offset += size + 12
    assert offset == len(data)
    assert [kind for kind, _ in chunks] == [b'IHDR', b'IDAT', b'IEND']
    width, height, depth, color, compression, filtering, interlace = struct.unpack(
        '>IIBBBBB', chunks[0][1])
    assert (depth, color, compression, filtering, interlace) == (8, 6, 0, 0, 0)
    assert chunks[-1][1] == b''
    raw = zlib.decompress(chunks[1][1])
    stride = 4 * width + 1
    assert len(raw) == stride * height
    rows = []
    for y in range(height):
        assert raw[y * stride] == 0
        row = raw[y * stride + 1:(y + 1) * stride]
        rows.append([tuple(row[x * 4:x * 4 + 4]) for x in range(width)])
    return width, height, rows


def element(identifier, kind='rectangle', **changes):
    result: dict = dict(id=identifier, name=identifier, type=kind, x=2, y=3,
                  width=8, height=6, text='', field='', prefix='', suffix='',
                  font_family='Arial', font_size=12, bold=False, italic=False,
                  align='left', color='#000000', background='#ff0000', border_width=0)
    result.update(changes)
    return result


def document(*elements):
    return DraftService.validate(dict(schema_version=2, name='Žltá cenovka',
                                     model_id='2.9EPD-BWR', elements=list(elements),
                                     sample_data={'Cena s DPH': '3,49 €'}))


class NativeRasterTests(unittest.TestCase):
    def prepare(self, doc):
        self.assertTrue((ROOT / 'webapp/esl_web/native_raster.py').is_file(),
                        'native compositing adapter not implemented')
        return importlib.import_module('esl_web.native_raster').prepare_native_raster(doc)

    def test_later_rectangles_and_black_text_mask_all_preceding_rectangles(self):
        red = element('red', x=0, y=0, width=8, height=6)
        white = element('white-panel', x=2, y=1, width=4, height=4,
                        background='#ffffff')
        condition = element('condition', 'text', x=1, y=2, width=6, height=2,
                            background='#ffffff', text='Podmienka')
        result = self.prepare(document(red, white, condition))
        for rect, later in ((red, (white, condition)), (white, (condition,))):
            _, _, rows = decode_rgba(result['rectangles'][rect['id']])
            rgb = tuple(bytes.fromhex(rect['background'][1:]))
            for y, row in enumerate(rows):
                for x, pixel in enumerate(row):
                    gx, gy = rect['x'] + x, rect['y'] + y
                    hole = any(e['x'] <= gx < e['x'] + e['width']
                               and e['y'] <= gy < e['y'] + e['height'] for e in later)
                    self.assertEqual(pixel, (0, 0, 0, 0) if hole else rgb + (255,))

    def test_every_text_background_uses_visible_rectangles_or_default_white(self):
        for color in ('#000000', '#ff0000', '#ffffff'):
            text = element('text', 'text', x=0, y=0, width=8, height=6,
                           color=color, background='transparent')
            cases = (
                ((), '#ffffff'),
                ((element('outside', x=20),), '#ffffff'),
                ((element('full', x=0, y=0),), '#ff0000'),
                ((element('left', x=0, y=0, width=4),
                  element('right', x=4, y=0, width=4)), '#ff0000'),
                ((element('hidden', x=1, y=1, width=2, height=2,
                          background='#000000'),
                  element('cover', x=0, y=0)), '#ff0000'),
            )
            for preceding, expected in cases:
                with self.subTest(color=color, ids=[r['id'] for r in preceding]):
                    doc = document(*preceding, text, element('late', x=0, y=0,
                                                            background='#000000'))
                    before = json.dumps(doc, ensure_ascii=False)
                    result = self.prepare(doc)
                    self.assertEqual(result['text_backgrounds'], {'text': expected})
                    self.assertEqual(result['white_backgrounds'],
                                     {'text': expected} if color == '#ffffff' else {})
                    self.assertEqual(json.dumps(doc, ensure_ascii=False), before)

    def test_explicit_background_wins_for_every_text_color_over_mixed_rectangles(self):
        for color in ('#000000', '#ff0000', '#ffffff'):
            result = self.prepare(document(
                element('partial', x=0, y=0, width=4),
                element('text', 'text', x=0, y=0, width=8, height=6,
                        color=color, background='#000000')))
            self.assertEqual(result['text_backgrounds'], {'text': '#000000'})

    def test_nonuniform_visible_background_is_rejected_with_text_id(self):
        cases = (
            (element('partial', x=0, y=0, width=4),),
            (element('base', x=0, y=0),
             element('stripe', x=3, y=2, width=1, height=1, background='#ffffff')),
            (element('base', x=0, y=0),
             element('bottom', x=0, y=5, width=8, height=1, background='#000000')),
        )
        for color in ('#000000', '#ff0000', '#ffffff'):
            for preceding in cases:
                with self.subTest(color=color, ids=[r['id'] for r in preceding]):
                    doc = document(*preceding, element(
                        'mixed', 'text', x=0, y=0, width=8, height=6,
                        color=color, background='transparent'))
                    before = json.dumps(doc, ensure_ascii=False)
                    with self.assertRaisesRegex(ValueError, 'mixed.*nonuniform'):
                        self.prepare(doc)
                    self.assertEqual(json.dumps(doc, ensure_ascii=False), before)

    def test_solid_rectangle_exact_size_color_and_original_id(self):
        for color in ('#ff0000', '#000000', '#ffffff'):
            with self.subTest(color=color):
                doc = document(element('pôvodné-id', background=color))
                before = json.dumps(doc, ensure_ascii=False)
                result = self.prepare(doc)
                self.assertEqual(set(result), {'rectangles', 'text_backgrounds', 'white_backgrounds'})
                self.assertEqual(result['text_backgrounds'], {})
                self.assertEqual(result['white_backgrounds'], {})
                self.assertEqual(set(result['rectangles']), {'pôvodné-id'})
                png = result['rectangles']['pôvodné-id']
                self.assertIsInstance(png, bytes)
                width, height, rows = decode_rgba(png)
                self.assertEqual((width, height), (8, 6))
                rgb = tuple(bytes.fromhex(color[1:]))
                self.assertEqual(rows, [[rgb + (255,)] * 8 for _ in range(6)])
                self.assertEqual(json.dumps(doc, ensure_ascii=False), before)
                self.assertEqual(self.prepare(doc), result)

    def test_later_white_box_gets_background_and_fully_transparent_hole(self):
        doc = document(element('red'), element(
            'white', 'text', x=4, y=4, width=3, height=2,
            background='transparent', color='#ffffff', field='Cena s DPH',
            prefix='Cena: ', suffix=' €', text='Žltá'))
        before = json.dumps(doc, ensure_ascii=False)
        result = self.prepare(doc)
        self.assertEqual(result['white_backgrounds'], {'white': '#ff0000'})
        _, _, rows = decode_rgba(result['rectangles']['red'])
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                self.assertEqual(pixel, (0, 0, 0, 0) if 2 <= x < 5 and 1 <= y < 3
                                 else (255, 0, 0, 255))
        self.assertEqual(json.dumps(doc, ensure_ascii=False), before)

    def test_explicit_white_text_background_wins_and_needs_no_container(self):
        white = element('explicit', 'text', x=4, y=4, width=3, height=2,
                        color='#ffffff', background='#000000')
        for elements in ((white,), (element('red'), white)):
            with self.subTest(count=len(elements)):
                result = self.prepare(document(*elements))
                self.assertEqual(result['white_backgrounds'], {'explicit': '#000000'})
                if 'red' in result['rectangles']:
                    _, _, rows = decode_rgba(result['rectangles']['red'])
                    self.assertEqual(rows[1][2], (0, 0, 0, 0))
                    self.assertEqual(rows[0][0], (255, 0, 0, 255))

    def test_transparent_white_text_defaults_to_white_without_a_rectangle(self):
        white = element('orphan', 'text', x=4, y=4, width=3, height=2,
                        background='transparent', color='#ffffff')
        cases = ((white,), (white, element('late')),
                 (element('elsewhere', x=30), white))
        for elements in cases:
            with self.subTest(ids=[e['id'] for e in elements]):
                doc = document(*elements)
                before = json.dumps(doc, ensure_ascii=False)
                result = self.prepare(doc)
                self.assertEqual(result['text_backgrounds'], {'orphan': '#ffffff'})
                self.assertEqual(result['white_backgrounds'], {'orphan': '#ffffff'})
                self.assertEqual(json.dumps(doc, ensure_ascii=False), before)

    def test_nonzero_source_borders_are_rejected_for_every_type(self):
        examples = [element('bordered', 'rectangle'), element('bordered', 'text'),
                    element('bordered', 'line'),
                    element('bordered', 'barcode', barcode_format='CODE128'),
                    element('bordered', 'qrcode', error_correction='M'),
                    element('bordered', 'image', image_data='', image_fit='contain')]
        for example in examples:
            for border in (1, 8):
                with self.subTest(kind=example['type'], border=border):
                    example['border_width'] = border
                    with self.assertRaisesRegex(ValueError, 'bordered.*border'):
                        self.prepare(document(example))

    def test_transparent_rectangle_is_rejected_with_source_id(self):
        rectangle = element('unfilled', background='transparent')
        white = element('white', 'text', color='#ffffff', background='transparent')
        for elements in ((rectangle,), (rectangle, white)):
            with self.subTest(count=len(elements)):
                with self.assertRaisesRegex(ValueError, 'unfilled.*transparent'):
                    self.prepare(document(*elements))

    def test_multirect_overlap_masks_every_preceding_rectangle_not_just_parent(self):
        outer = element('outer', x=0, y=0, width=12, height=10)
        inner = element('inner', x=2, y=2, width=8, height=6, background='#000000')
        partial = element('partial', x=5, y=0, width=4, height=4,
                          background='#ffffff')
        white = element('white', 'text', x=3, y=3, width=5, height=3,
                        color='#ffffff', background='#000000')
        result = self.prepare(document(outer, inner, partial, white))
        self.assertEqual(result['white_backgrounds'], {'white': '#000000'})
        for rectangle in (outer, inner, partial):
            with self.subTest(rectangle=rectangle['id']):
                width, height, rows = decode_rgba(result['rectangles'][rectangle['id']])
                self.assertEqual((width, height), (rectangle['width'], rectangle['height']))
                rgb = tuple(bytes.fromhex(rectangle['background'][1:]))
                for y, row in enumerate(rows):
                    for x, pixel in enumerate(row):
                        gx, gy = rectangle['x'] + x, rectangle['y'] + y
                        later = {'outer': (inner, partial, white),
                                 'inner': (partial, white), 'partial': (white,)}[rectangle['id']]
                        hole = any(e['x'] <= gx < e['x'] + e['width']
                                   and e['y'] <= gy < e['y'] + e['height'] for e in later)
                        self.assertEqual(pixel, (0, 0, 0, 0) if hole
                                         else rgb + (255,))

    def test_masks_union_overlapping_white_and_black_text_boxes(self):
        rect = element('red', x=0, y=0, width=8, height=6)
        white1 = element('one', 'text', x=0, y=0, width=4, height=3,
                         color='#ffffff', background='transparent')
        white2 = element('two', 'text', x=2, y=2, width=4, height=3,
                         color='#ffffff', background='transparent')
        black = element('black', 'text', x=6, y=0, width=2, height=2,
                        background='transparent')
        result = self.prepare(document(rect, white1, white2, black))
        self.assertEqual(result['white_backgrounds'], {'one': '#ff0000', 'two': '#ff0000'})
        _, _, rows = decode_rgba(result['rectangles']['red'])
        for y, row in enumerate(rows):
            for x, pixel in enumerate(row):
                hole = ((0 <= x < 4 and 0 <= y < 3) or (2 <= x < 6 and 2 <= y < 5)
                        or (6 <= x < 8 and 0 <= y < 2))
                self.assertEqual(pixel, (0, 0, 0, 0) if hole else (255, 0, 0, 255))

    def test_only_later_white_boxes_cut_holes_touching_edges_do_not_overlap(self):
        early = element('early', 'text', color='#ffffff', background='#000000')
        rect = element('red')
        adjacent = element('adjacent', 'text', x=10, y=3, width=2, height=6,
                           color='#ffffff', background='#000000')
        result = self.prepare(document(early, rect, adjacent))
        self.assertEqual(result['white_backgrounds'],
                         {'early': '#000000', 'adjacent': '#000000'})
        _, _, rows = decode_rgba(result['rectangles']['red'])
        self.assertEqual(rows, [[(255, 0, 0, 255)] * 8 for _ in range(6)])

    def test_same_size_white_box_makes_rectangle_entirely_transparent(self):
        result = self.prepare(document(element('red'), element(
            'full', 'text', color='#ffffff', background='transparent')))
        self.assertEqual(result['white_backgrounds'], {'full': '#ff0000'})
        _, _, rows = decode_rgba(result['rectangles']['red'])
        self.assertEqual(rows, [[(0, 0, 0, 0)] * 8 for _ in range(6)])

    def test_empty_and_nonparticipating_elements_make_no_entries(self):
        for doc in (document(), document(
                element('line', 'line'),
                element('barcode', 'barcode', barcode_format='CODE128'),
                element('qr', 'qrcode', error_correction='M'),
                element('image', 'image', image_data='', image_fit='contain'))):
            self.assertEqual(self.prepare(doc), {'rectangles': {}, 'text_backgrounds': {},
                                                'white_backgrounds': {}})

    def test_all_30_presets_exact_geometry_every_pixel_and_all_text_backgrounds(self):
        preset_root = ROOT / 'webapp/template-presets'
        paths = sorted([*preset_root.glob('retail-sk/*.json'),
                        *preset_root.glob('extended-sk/*.json')])
        self.assertEqual(len(paths), 30)
        total_elements = total_rectangles = total_white = 0
        for path in paths:
            with self.subTest(preset=path.name):
                source = json.loads(path.read_text(encoding='utf-8'))
                doc = DraftService.validate(source)
                result = self.prepare(doc)
                self.assertEqual(doc, source, 'adapter must preserve UTF-8 and source fields')
                elements = doc['elements']
                total_elements += len(elements)
                self.assertTrue(all(e['border_width'] == 0 for e in elements))
                rectangles = [e for e in elements if e['type'] == 'rectangle']
                whites = [e for e in elements if e['type'] == 'text' and e['color'] == '#ffffff']
                total_rectangles += len(rectangles)
                total_white += len(whites)
                self.assertEqual(set(result['rectangles']), {e['id'] for e in rectangles})
                self.assertEqual(set(result['white_backgrounds']), {e['id'] for e in whites})
                texts = [e for e in elements if e['type'] == 'text']
                self.assertEqual(set(result['text_backgrounds']), {e['id'] for e in texts})
                for index, text in enumerate(elements):
                    if text not in texts:
                        continue
                    if text['background'] != 'transparent':
                        expected = text['background']
                    else:
                        preceding = [r for r in elements[:index] if r['type'] == 'rectangle']
                        colors = set()
                        for y in range(text['y'], text['y'] + text['height']):
                            for x in range(text['x'], text['x'] + text['width']):
                                color = '#ffffff'
                                for rect in preceding:
                                    if (rect['x'] <= x < rect['x'] + rect['width']
                                            and rect['y'] <= y < rect['y'] + rect['height']):
                                        color = rect['background']
                                colors.add(color)
                        self.assertEqual(len(colors), 1, (path.name, text['id'], colors))
                        expected = colors.pop()
                    self.assertEqual(result['text_backgrounds'][text['id']], expected)
                    if text in whites:
                        self.assertEqual(result['white_backgrounds'][text['id']], expected)
                for index, rect in enumerate(elements):
                    if rect['type'] != 'rectangle':
                        continue
                    width, height, rows = decode_rgba(result['rectangles'][rect['id']])
                    self.assertEqual((width, height), (rect['width'], rect['height']))
                    later_boxes = [e for e in elements[index + 1:]
                                   if e['type'] in ('text', 'rectangle')]
                    rgb = tuple(bytes.fromhex(rect['background'][1:]))
                    for y, row in enumerate(rows):
                        for x, pixel in enumerate(row):
                            gx, gy = rect['x'] + x, rect['y'] + y
                            hole = any(t['x'] <= gx < t['x'] + t['width']
                                       and t['y'] <= gy < t['y'] + t['height']
                                       for t in later_boxes)
                            self.assertEqual(pixel, (0, 0, 0, 0) if hole else rgb + (255,),
                                             (path.name, rect['id'], x, y))
        self.assertEqual((total_elements, total_rectangles, total_white), (228, 24, 30))

    def test_runs_without_site_packages_or_imaging_libraries(self):
        doc = document(element('red'), element('white', 'text', x=4, y=4,
                        width=3, height=2, color='#ffffff', background='transparent'))
        script = (
            'import sys\n'
            f'sys.path.insert(0, {str(ROOT / "webapp")!r})\n'
            'from esl_web.native_raster import prepare_native_raster\n'
            f'result = prepare_native_raster({doc!r})\n'
            'assert result["white_backgrounds"] == {"white": "#ff0000"}\n'
            'assert result["text_backgrounds"] == {"white": "#ff0000"}\n'
            'assert result["rectangles"]["red"].startswith(b"\\x89PNG\\r\\n\\x1a\\n")\n'
            'assert not any(m == "PIL" or m.startswith("PIL.") or '
            'm == "numpy" or m.startswith("numpy.") for m in sys.modules)\n'
        )
        completed = subprocess.run([sys.executable, '-S', '-B', '-c', script],
                                   capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, '')


if __name__ == '__main__':
    unittest.main()
