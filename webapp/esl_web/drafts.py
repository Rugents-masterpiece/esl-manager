"""Local browser-rendering drafts; not vendor templates or publication commands."""
from __future__ import annotations

import json
import base64
import binascii
import math
import re
import struct
import uuid
import zlib

from .service import ValidationError, ConflictError, NotFoundError, _identifier, _now
from .storage import Storage, SUPPORTED_DEVICE_MODELS

FIELD = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,63}')
DOCUMENT_FIELDS = {'schema_version', 'name', 'model_id', 'elements', 'sample_data'}
ELEMENT_FIELDS = {
    'id', 'name', 'type', 'x', 'y', 'width', 'height', 'text', 'field',
    'prefix', 'suffix', 'font_family', 'font_size', 'bold', 'italic',
    'align', 'color', 'background', 'border_width',
}
MAX_DOCUMENT_BYTES = 256 * 1024
MEDIA_FIELDS = {'image': {'image_data', 'image_fit'},
                'barcode': {'barcode_format'}, 'qrcode': {'error_correction'}}
MAX_PNG_BYTES = 128 * 1024
PNG_PREFIX = 'data:image/png;base64,'


def _invalid(field):
    raise ValidationError(f'Invalid {field}', details={'field': field})


def _string(value, field, maximum, required=False):
    if (not isinstance(value, str) or len(value) > maximum
            or (required and not value.strip())):
        _invalid(field)


def _integer(value, field, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        _invalid(field)


def _choice(value, field, choices):
    if not isinstance(value, str) or value not in choices:
        _invalid(field)


def _valid_field_key(value, version):
    if not isinstance(value, str):
        return False
    if version == 1:
        return FIELD.fullmatch(value) is not None
    # V2 preserves native names verbatim; bindings are flat keys, never expressions.
    return bool(value) and len(value) <= 100 and not re.search(
        r'[\x00-\x1f\x7f-\x9f\ud800-\udfff]', value)


def _exact(value, field, fields):
    if not isinstance(value, dict) or set(value) != fields:
        _invalid(field)


def _code(value, kind):
    # Empty content is permitted: preview reports missing/empty encodable values.
    if len(value) > 2000 or any(
            (not 32 <= ord(char) <= 126 if kind == 'barcode'
             else ord(char) < 32 or 127 <= ord(char) <= 159
             or 0xD800 <= ord(char) <= 0xDFFF) for char in value):
        _invalid('code.value')


def _png(value):
    """Validate a bounded static PNG, including chunks and bounded raster inflation."""
    if value == '':
        return
    if (not isinstance(value, str) or not value.startswith(PNG_PREFIX)
            or len(value) > len(PNG_PREFIX) + 4 * ((MAX_PNG_BYTES + 2) // 3)):
        _invalid('image_data')
    try:
        encoded = value[len(PNG_PREFIX):]
        data = base64.b64decode(encoded, validate=True)
        if (len(data) > MAX_PNG_BYTES or base64.b64encode(data).decode('ascii') != encoded
                or data[:8] != b'\x89PNG\r\n\x1a\n'):
            _invalid('image_data')
        offset, header, palette, ended, idat_done = 8, None, False, False, False
        idat_started = False
        width = height = depth = color = interlace = 0
        image = bytearray()
        while offset < len(data):
            if offset + 12 > len(data):
                _invalid('image_data')
            size = struct.unpack_from('>I', data, offset)[0]
            kind = data[offset + 4:offset + 8]
            end = offset + 12 + size
            if (end > len(data) or not re.fullmatch(b'[A-Za-z]{2}[A-Z][A-Za-z]', kind)
                    or zlib.crc32(data[offset + 4:end - 4]) != struct.unpack_from('>I', data, end - 4)[0]
                    or (header is None and kind != b'IHDR')):
                _invalid('image_data')
            payload = data[offset + 8:end - 4]
            if kind == b'IHDR':
                if header is not None or size != 13:
                    _invalid('image_data')
                header = struct.unpack('>IIBBBBB', payload)
                width, height, depth, color, compression, filtering, interlace = header
                depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
                if (not 1 <= width <= 1024 or not 1 <= height <= 1024
                        or depth not in depths.get(color, set()) or compression != 0
                        or filtering != 0 or interlace not in (0, 1)):
                    _invalid('image_data')
            elif kind == b'PLTE':
                if palette or idat_started or size == 0 or size % 3 or size > 768 or color in (0, 4) or (color == 3 and size // 3 > 2 ** depth):
                    _invalid('image_data')
                palette = True
            elif kind == b'IDAT':
                if idat_done or (color == 3 and not palette):
                    _invalid('image_data')
                idat_started = True
                image.extend(payload)
            elif kind == b'IEND':
                if size or not image or end != len(data):
                    _invalid('image_data')
                ended = True
            elif not (kind[0] & 32) or kind in (b'acTL', b'fcTL', b'fdAT'):
                _invalid('image_data')
            if idat_started and kind != b'IDAT':
                idat_done = True
            offset = end
        if not ended or header is None:
            _invalid('image_data')
        channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
        passes = [(0, 0, 1, 1)] if not interlace else [
            (0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4),
            (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)]
        rows = []
        for x, y, dx, dy in passes:
            pw = max(0, (width - x + dx - 1) // dx)
            ph = max(0, (height - y + dy - 1) // dy)
            if pw and ph:
                rows.extend([1 + (pw * channels * depth + 7) // 8] * ph)
        expected = sum(rows)  # At most ~8 MiB at 1024x1024, RGBA16.
        inflater = zlib.decompressobj()
        raw = inflater.decompress(image, expected + 1)
        if len(raw) != expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
            _invalid('image_data')
        offset = 0
        for size in rows:
            if raw[offset] > 4:
                _invalid('image_data')
            offset += size
    except (ValueError, binascii.Error, struct.error, zlib.error) as error:
        raise ValidationError('Invalid image_data', details={'field': 'image_data'}) from error


class DraftService:
    def __init__(self, storage: Storage):
        self.storage = storage

    @staticmethod
    def validate(document):
        """Return a detached JSON snapshot after strict local-rendering validation."""
        _exact(document, 'document', DOCUMENT_FIELDS)
        _integer(document['schema_version'], 'schema_version', 1, 2)
        _string(document['name'], 'name', 200, required=True)
        model = document['model_id']
        _choice(model, 'model_id', SUPPORTED_DEVICE_MODELS)
        width, height = SUPPORTED_DEVICE_MODELS[model]
        elements = document['elements']
        if not isinstance(elements, list) or len(elements) > 100:
            _invalid('elements')
        palette = {'#000000', '#ffffff'}
        if model.endswith('EPD-BWR'):
            palette.add('#ff0000')
        seen = set()
        for element in elements:
            if not isinstance(element, dict):
                _invalid('element')
            kind = element.get('type')
            types = {'text', 'rectangle', 'line'}
            if document['schema_version'] == 2:
                types |= MEDIA_FIELDS.keys()
            _choice(kind, 'type', types)
            _exact(element, 'element', ELEMENT_FIELDS | MEDIA_FIELDS.get(kind, set()))
            if kind == 'image':
                _choice(element['image_fit'], 'image_fit', {'contain', 'cover', 'fill'})
                _png(element['image_data'])
            elif kind == 'barcode':
                _choice(element['barcode_format'], 'barcode_format', {'CODE128'})
            elif kind == 'qrcode':
                _choice(element['error_correction'], 'error_correction', {'L', 'M', 'Q', 'H'})
            _string(element['id'], 'id', 64, required=True)
            _string(element['name'], 'name', 200, required=True)
            if element['id'] in seen:
                _invalid('elements.id')
            seen.add(element['id'])

            _integer(element['x'], 'x', 0, width - 1)
            _integer(element['y'], 'y', 0, height - 1)
            _integer(element['width'], 'width', 1, width - element['x'])
            _integer(element['height'], 'height', 1, height - element['y'])
            for field, limit in [('text', 2000), ('prefix', 200), ('suffix', 200)]:
                _string(element[field], field, limit)
            field = element['field']
            if field != '' and not _valid_field_key(field, document['schema_version']):
                _invalid('field')
            _choice(element['font_family'], 'font_family',
                    {'Arial', 'Verdana', 'Times New Roman', 'Courier New'})
            _integer(element['font_size'], 'font_size', 4, 96)
            _integer(element['border_width'], 'border_width', 0, 8)
            for field in ('bold', 'italic'):
                if type(element[field]) is not bool:
                    _invalid(field)
            _choice(element['align'], 'align', {'left', 'center', 'right'})
            _choice(element['color'], 'color', palette)
            _choice(element['background'], 'background', palette | {'transparent'})
        sample = document['sample_data']
        if not isinstance(sample, dict) or len(sample) > 100:
            _invalid('sample_data')
        for key, value in sample.items():
            if not _valid_field_key(key, document['schema_version']):
                _invalid('sample_data.key')
            if isinstance(value, str):
                _string(value, 'sample_data.value', 2000)
            elif value is None or type(value) is bool:
                pass
            elif (type(value) in (int, float) and abs(value) <= 9007199254740991
                  and math.isfinite(value)):
                pass
            else:
                _invalid('sample_data.value')
        for element in elements:
            if element['type'] not in {'barcode', 'qrcode'}:
                continue
            kind = element['type']
            for field in ('text', 'prefix', 'suffix'):
                _code(element[field], kind)
            _code(element['prefix'] + element['text'] + element['suffix'], kind)
            value = sample.get(element['field'], element['text'])
            if value is None:
                value = ''
            elif type(value) is bool:
                value = 'true' if value else 'false'
            _code(element['prefix'] + str(value) + element['suffix'], kind)
        try:
            encoded = json.dumps(document, ensure_ascii=False, allow_nan=False,
                                 sort_keys=True, separators=(',', ':'))
            if len(encoded.encode('utf-8')) > MAX_DOCUMENT_BYTES:
                _invalid('document.size')
            return json.loads(encoded)
        except (TypeError, ValueError, UnicodeError) as error:
            raise ValidationError('Invalid document JSON') from error

    @staticmethod
    def _result(row):
        result = dict(row)
        result['document'] = json.loads(result['document'])
        return result

    @staticmethod
    def _get(connection, draft_id):
        row = connection.execute('SELECT * FROM template_drafts WHERE id = ?',
                                 (draft_id,)).fetchone()
        if row is None:
            raise NotFoundError('Template draft not found')
        return row

    @staticmethod
    def _audit(connection, action, draft_id, revision, timestamp):
        connection.execute(
            'INSERT INTO audit_events(action, entity_type, entity_id, details, created_at) '
            'VALUES (?, ?, ?, ?, ?)',
            (f'template_draft.{action}', 'template_draft', draft_id,
             json.dumps({'revision': revision}), timestamp),
        )

    @staticmethod
    def _revision_payload(payload, fields):
        _exact(payload, 'payload', fields)
        revision = payload['revision']
        if type(revision) is not int or revision <= 0:
            _invalid('revision')
        return revision

    def list(self):
        """Return complete detached records in stable creation/ID order."""
        with self.storage.connection() as connection:
            return [self._result(row) for row in connection.execute(
                'SELECT * FROM template_drafts ORDER BY created_at, id')]

    def get(self, draft_id):
        draft_id = _identifier(draft_id)
        with self.storage.connection() as connection:
            return self._result(self._get(connection, draft_id))

    def create(self, document):
        canonical = self.validate(document)
        draft_id = _identifier(str(uuid.uuid4()))
        timestamp = _now()
        with self.storage.connection() as connection:
            connection.execute(
                'INSERT INTO template_drafts(id, revision, document, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?)',
                (draft_id, 1, json.dumps(canonical, ensure_ascii=False, separators=(',', ':')),
                 timestamp, timestamp),
            )
            self._audit(connection, 'created', draft_id, 1, timestamp)
            return self._result(self._get(connection, draft_id))

    def update(self, draft_id, payload):
        draft_id = _identifier(draft_id)
        revision = self._revision_payload(payload, {'revision', 'document'})
        canonical = self.validate(payload['document'])
        with self.storage.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            current = self._get(connection, draft_id)
            if current['revision'] != revision:
                raise ConflictError('Template draft revision is stale',
                                    details={'revision': current['revision']})
            timestamp = _now()
            connection.execute(
                'UPDATE template_drafts SET document = ?, revision = revision + 1, '
                'updated_at = ? WHERE id = ? AND revision = ?',
                (json.dumps(canonical, ensure_ascii=False, separators=(',', ':')),
                 timestamp, draft_id, revision),
            )
            self._audit(connection, 'updated', draft_id, revision + 1, timestamp)
            return self._result(self._get(connection, draft_id))

    def delete(self, draft_id, payload) -> None:
        draft_id = _identifier(draft_id)
        revision = self._revision_payload(payload, {'revision'})
        with self.storage.connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            current = self._get(connection, draft_id)
            if current['revision'] != revision:
                raise ConflictError('Template draft revision is stale',
                                    details={'revision': current['revision']})
            connection.execute('DELETE FROM template_drafts WHERE id = ? AND revision = ?',
                               (draft_id, revision))
            self._audit(connection, 'deleted', draft_id, revision, _now())

    def initialize(self) -> None:
        """Explicitly create the additive draft table without migrating core schema."""
        with self.storage.connection() as connection:
            connection.execute('''CREATE TABLE IF NOT EXISTS template_drafts (
                id TEXT PRIMARY KEY,
                revision INTEGER NOT NULL CHECK(revision > 0),
                document TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )''')
