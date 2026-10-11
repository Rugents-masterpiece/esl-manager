"""Schema v2 media contract; v1 retains its original exact element fields."""
import unittest
import base64
import struct
import zlib
from esl_web.drafts import DraftService
from esl_web.service import ValidationError
from test_drafts import document

EXTRAS = {'image': {'image_data': '', 'image_fit': 'contain'},
          'barcode': {'barcode_format': 'CODE128'},
          'qrcode': {'error_correction': 'M'}}


def chunk(kind, data=b''):
    return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))


def png(width=1, height=1, depth=8, color=6, compression=0, filtering=0, interlace=0, raw=None):
    header = struct.pack('>IIBBBBB', width, height, depth, color, compression, filtering, interlace)
    if raw is None:
        raw = (b'\0' + b'\0' * (width * 4)) * height
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND')


def data_url(data):
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def media(kind):
    doc = document()
    doc['schema_version'] = 2
    doc['sample_data'] = {}
    doc['elements'][0].update(type=kind, text='123', field='', **EXTRAS[kind])
    return doc


class MediaSchemaTests(unittest.TestCase):
    def test_media_retains_common_limits_and_document_byte_bound(self):
        for kind in EXTRAS:
            for patch in [{'font_size': 97}, {'x': -1}, {'width': 251},
                          {'text': 'x' * 2001}, {'background': '#ff0000'},
                          {'field': 'bad\x00field'}, {'border_width': 9}]:
                doc = media(kind)
                doc['elements'][0].update(patch)
                with self.assertRaises(ValidationError):
                    DraftService.validate(doc)
        valid = png()
        bounded = valid[:33] + chunk(b'tEXt', b'x' * (128 * 1024 - len(valid) - 12)) + valid[33:]
        doc = media('image')
        doc['elements'][0]['image_data'] = data_url(bounded)
        doc['elements'].append(dict(doc['elements'][0], id='second'))
        with self.assertRaises(ValidationError):
            DraftService.validate(doc)

    def test_png_zlib_strategies_split_idat_and_max_dimensions(self):
        base = png()
        raw = (b'\0' + bytes(range(64))) * 16
        header = png(16, 16)[:33]
        for strategy in [zlib.Z_DEFAULT_STRATEGY, zlib.Z_FIXED, zlib.Z_HUFFMAN_ONLY]:
            for level in [0, 1, 9]:
                compressor = zlib.compressobj(level=level, strategy=strategy)
                compressed = compressor.compress(raw) + compressor.flush()
                data = header + chunk(b'IDAT', compressed[:3]) + chunk(b'IDAT', compressed[3:]) + chunk(b'IEND')
                doc = media('image')
                doc['elements'][0]['image_data'] = data_url(data)
                DraftService.validate(doc)
        doc = media('image')
        doc['elements'][0]['image_data'] = data_url(png(1024, 1024))
        DraftService.validate(doc)
        compressed = zlib.compress(b'\0' * 5)
        corrupted = compressed[:-1] + bytes([compressed[-1] ^ 1])
        for data in [base[:33] + chunk(b'IDAT', corrupted) + chunk(b'IEND'),
                     base[:33] + chunk(b'IDAT', compressed + b'extra') + chunk(b'IEND'),
                     base[:33] + chunk(b'IDAT', compressed[:-1]) + chunk(b'IEND'),
                     base[:33] + chunk(b'IEND'), base[:-12]]:
            doc['elements'][0]['image_data'] = data_url(data)
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)

    def test_png_chunk_order_palette_and_encoded_boundary(self):
        valid = png()
        pad = 128 * 1024 - len(valid) - 12
        bounded = valid[:33] + chunk(b'tEXt', b'x' * pad) + valid[33:]
        doc = media('image')
        doc['elements'][0]['image_data'] = data_url(bounded)
        DraftService.validate(doc)
        indexed = png(depth=1, color=3, raw=b'\0\0')
        indexed = indexed[:33] + chunk(b'PLTE', b'\0\0\0') + indexed[33:]
        doc['elements'][0]['image_data'] = data_url(indexed)
        DraftService.validate(doc)
        for data in [png(depth=1, color=3, raw=b'\0\0'),
                     valid[:33] + chunk(b'IDAT') + chunk(b'tEXt') + valid[33:],
                     valid[:33] + chunk(b'IDAT') + chunk(b'PLTE', b'\0\0\0') + valid[33:],
                     valid[:33] + chunk(b'acTL', b'\0' * 8) + valid[33:],
                     indexed[:33] + chunk(b'PLTE', b'\0' * 9) + indexed[48:]]:
            doc['elements'][0]['image_data'] = data_url(data)
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)

    def test_png_valid_structure_limits_and_placeholders(self):
        valid = png()
        for value in ['', data_url(valid), data_url(png(1024, 1)),
                      data_url(png(interlace=1)), data_url(png(depth=1, color=0, raw=b'\0\0'))]:
            doc = media('image')
            doc['elements'][0]['image_data'] = value
            DraftService.validate(doc)
        for value in [None, 'https://example.com/image.png', 'data:image/svg+xml;base64,AAAA',
                      'data:image/png;base64,!!!!', data_url(valid) + '\n',
                      data_url(valid)[:-1], data_url(b'not png'),
                      data_url(valid[:-1]), data_url(valid + b'junk'),
                      data_url(valid[:29] + bytes([valid[29] ^ 1]) + valid[30:]),
                      data_url(png(0)), data_url(png(1025)), data_url(png(height=1025)),
                      data_url(png(depth=3)), data_url(png(compression=1)),
                      data_url(png(filtering=1)), data_url(png(interlace=2)),
                      data_url(png(raw=b'\x05\0\0\0\0')), data_url(png(raw=b'')),
                      data_url(png(raw=b'\0' * 10000)),
                      data_url(valid[:33] + chunk(b'IDAT', b'not zlib') + chunk(b'IEND')),
                      data_url(valid[:33] + chunk(b'ABCD') + valid[33:]),
                      data_url(valid[:33] + chunk(b'IHDR', valid[16:29]) + valid[33:]),
                      data_url(valid[:33] + chunk(b'tEXt', b'x' * (128 * 1024)) + valid[33:])]:
            doc = media('image')
            doc['elements'][0]['image_data'] = value
            with self.subTest(value=str(value)[:60]), self.assertRaises(ValidationError):
                DraftService.validate(doc)

    def test_codes_validate_fallback_and_resolved_values(self):
        # Empty codes (including missing/null bindings) remain preview diagnostics.
        for value in ['', ' !~', 'x' * 2000]:
            doc = media('barcode')
            doc['elements'][0]['text'] = value
            DraftService.validate(doc)
        for value in ['é', '\n', '\x00', '\x7f']:
            for location in ['text', 'prefix', 'suffix', 'sample']:
                doc = media('barcode')
                e = doc['elements'][0]
                if location == 'sample':
                    e['field'] = 'sku'
                    doc['sample_data']['sku'] = value
                else:
                    e[location] = value
                with self.subTest(value=value, location=location), self.assertRaises(ValidationError):
                    DraftService.validate(doc)
        for kind in ['barcode', 'qrcode']:
            doc = media(kind)
            e = doc['elements'][0]
            e.update(text='x' * 2000, prefix='x')
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)
            e.update(text='fallback', prefix='', field='sku')
            for value in [None, False, 123, '']:
                doc['sample_data']['sku'] = value
                DraftService.validate(doc)
        doc = media('qrcode')
        doc['elements'][0]['text'] = '雪😀' * 1000
        DraftService.validate(doc)
        for value in ['\x00', '\n', '\x7f', '\x85']:
            doc['elements'][0]['text'] = value
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)

    def test_v2_accepts_exact_media_fields_and_original_types(self):
        for kind in EXTRAS:
            doc = media(kind)
            self.assertEqual(doc, DraftService.validate(doc))
        doc = document()
        doc['schema_version'] = 2
        self.assertEqual(doc, DraftService.validate(doc))

    def test_v1_rejects_media_and_v2_requires_only_relevant_extras(self):
        for kind, extras in EXTRAS.items():
            doc = media(kind)
            doc['schema_version'] = 1
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)
            for key in extras:
                doc = media(kind)
                del doc['elements'][0][key]
                with self.assertRaises(ValidationError):
                    DraftService.validate(doc)
            doc = media(kind)
            doc['elements'][0]['irrelevant'] = ''
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)
        for kind, key, value in [('image', 'image_fit', 'stretch'),
                                 ('barcode', 'barcode_format', 'code128'),
                                 ('qrcode', 'error_correction', 'm')]:
            doc = media(kind)
            doc['elements'][0][key] = value
            with self.assertRaises(ValidationError):
                DraftService.validate(doc)


if __name__ == '__main__':
    unittest.main()
