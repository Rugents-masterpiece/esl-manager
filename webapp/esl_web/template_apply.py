"""Verified publisher receipts and independently guarded manual native dispatch.

register() is an internal publisher-only API: call it only after native read-back
verification. Registration never assigns a tag or performs a vendor request.
Authentication and controller-client selection remain the caller's responsibility.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid

from .drafts import DraftService
from .service import ConflictError, ForbiddenError, IntegrationError, NotFoundError, ValidationError
from .vendor import live_writes_authorized


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _id(value, field):
    if not isinstance(value, str) or not value or len(value) > 200:
        raise ValidationError('Invalid ' + field)
    return value


def _vendor_id(value):
    if type(value) is int:
        value = str(value)
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,9}', value) or int(value) > 2147483647:
        raise ValidationError('Invalid vendor_id')
    return value


def _scalar(value):
    if value is None or type(value) is bool:
        return
    if type(value) is str and len(value) <= 2000:
        return
    if type(value) in (int, float) and abs(value) <= 9007199254740991 and math.isfinite(value):
        return
    raise ValidationError('Values must be bounded JSON scalars')


def _bindings(document, bindings):
    if type(bindings) is not dict or len(bindings) > 100:
        raise ValidationError('Invalid publication bindings')
    elements = {element['id']: element for element in document['elements']}
    reserved = {'mac', 'styleid', 'mappingtype', 'ABDisplayFlag', '__proto__', 'constructor', 'prototype'}
    for alias, binding in bindings.items():
        if (type(alias) is not str or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,99}', alias)
                or alias in reserved or type(binding) is not dict
                or set(binding) not in ({'field', 'element_id', 'static_value'},
                                        {'field', 'element_id', 'static_value', 'renderer'})):
            raise ValidationError('Invalid publication alias')
        if type(binding['element_id']) is not str or binding['element_id'] not in elements:
            raise ValidationError('Unknown publication element')
        element = elements[binding['element_id']]
        if type(binding['field']) is not str or binding['field'] != element['field']:
            raise ValidationError('Publication source field mismatch')
        _scalar(binding['static_value'])
        if 'renderer' in binding:
            renderer = binding['renderer']
            keys = {'type', 'width', 'height', 'error_correction', 'prefix', 'suffix'}
            if (type(renderer) is not dict or set(renderer) != keys
                    or element['type'] != 'qrcode' or element['error_correction'] != 'M'
                    or any(type(renderer[key]) is not type(element[key])
                           or renderer[key] != element[key] for key in keys)):
                raise ValidationError('QR renderer must match original geometry, exact M ECC and affixes')
            if type(binding['static_value']) is not str or not binding['static_value']:
                raise ValidationError('QR requires a nonempty native photoName')
        elif element['type'] == 'qrcode':
            raise ValidationError('QR requires a native photo renderer')
        if element['type'] == 'image' and (binding['field'] or not isinstance(binding['static_value'], str) or not binding['static_value']):
            raise ValidationError('Image requires a nonempty native photoName')
    if {element['field'] for element in elements.values() if element['field']} != {binding['field'] for binding in bindings.values() if binding['field']}:
        raise ValidationError('Publication omits required source fields')


class TemplatePublicationService:
    def __init__(self, storage):
        self.storage = storage

    def initialize(self):
        with self.storage.connection() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS template_publications (
                controller_id TEXT NOT NULL, vendor_id TEXT NOT NULL,
                draft_id TEXT NOT NULL, draft_revision INTEGER NOT NULL,
                document TEXT NOT NULL, bindings TEXT NOT NULL,
                document_hash TEXT NOT NULL,
                PRIMARY KEY(controller_id, vendor_id))''')

    @staticmethod
    def _result(row):
        result = dict(row)
        result['document'] = json.loads(result['document'])
        result['bindings'] = json.loads(result['bindings'])
        return result

    def register(self, controller_id, vendor_id, draft_id, draft_revision, document, bindings):
        controller_id = _id(controller_id, 'controller_id')
        vendor_id = _vendor_id(vendor_id)
        draft_id = _id(draft_id, 'draft_id')
        if type(draft_revision) is not int or not 1 <= draft_revision <= 2147483647:
            raise ValidationError('Invalid draft_revision')
        document = DraftService.validate(document)
        _bindings(document, bindings)
        encoded = _json(document)
        with self.storage.connection() as c:
            old = c.execute('SELECT * FROM template_publications WHERE controller_id=? AND vendor_id=?', (controller_id, vendor_id)).fetchone()
            receipt = (controller_id, vendor_id, draft_id, draft_revision, encoded, _json(bindings), hashlib.sha256(encoded.encode('utf-8')).hexdigest())
            if old and old['draft_id'] == draft_id and old['draft_revision'] >= draft_revision:
                if tuple(old) == receipt:
                    return self._result(old)
                raise ConflictError('Publication revision is stale or conflicting')
            c.execute('INSERT OR REPLACE INTO template_publications VALUES (?,?,?,?,?,?,?)', receipt)
        return self.get(controller_id, vendor_id)

    def apply(self, service, client, controller_id, tag_id, body):
        confirmation = body.get('confirmation') if type(body) is dict else None
        if not live_writes_authorized(confirmation):
            raise ForbiddenError('Live ESL writes are disabled or not explicitly confirmed')
        if type(body) is not dict or set(body) != {'template_id', 'data', 'confirmation'}:
            raise ValidationError('Body requires exactly template_id, data and confirmation')
        _id(controller_id, 'controller_id')
        _id(tag_id, 'tag_id')
        _id(body['template_id'], 'template_id')
        tag = service.get_tag(tag_id)
        if tag.get('staged') or tag.get('inventory_source') == 'local':
            raise ValidationError('Staged tags cannot receive live updates')
        if tag['controller_id'] != controller_id:
            raise ValidationError('Tag belongs to another controller')
        model = tag.get('device_model')
        if not model or not tag.get('management_supported'):
            raise ValidationError('Tag has no supported exact model')
        expected = (model['width'], model['height'], model['screen_type'])
        with self.storage.connection() as c:
            row = c.execute('SELECT * FROM templates WHERE id=?', (body['template_id'],)).fetchone()
        if row is None:
            raise NotFoundError('Template not found')
        template = dict(row)
        if template['controller_id'] != controller_id:
            raise ValidationError('Template belongs to another controller')
        if (template['width'], template['height'], template['screen_type']) != expected:
            raise ValidationError('Template does not match tag model')
        receipt = self.get(controller_id, template['vendor_id'])
        if receipt['document']['model_id'] != model['id']:
            raise ValidationError('Published draft does not match tag model')
        if hashlib.sha256(_json(receipt['document']).encode()).hexdigest() != receipt['document_hash']:
            raise IntegrationError('Publication document hash mismatch')
        _bindings(receipt['document'], receipt['bindings'])
        data = body['data']
        required = {binding['field'] for binding in receipt['bindings'].values() if binding['field']}
        if type(data) is not dict or set(data) != required:
            raise ValidationError('data requires exactly the published source fields')
        for value in data.values():
            _scalar(value)
        for binding in receipt['bindings'].values():
            if binding.get('renderer') and binding['field'] and type(data[binding['field']]) is not str:
                raise ValidationError('Dynamic QR input must be a string')
        native_id = int(receipt['vendor_id'])
        try:
            detail = client.get_style_detail(native_id)
            catalog = client.get_style_catalog()
        except Exception as error:
            raise IntegrationError('Could not verify current vendor template') from error
        if not isinstance(detail, dict) or detail.get('id') != native_id:
            raise IntegrationError('Vendor detail identity mismatch')
        matches = [item for item in catalog if isinstance(item, dict) and item.get('id') == native_id] if isinstance(catalog, list) else []
        if len(matches) != 1:
            raise IntegrationError('Vendor catalog identity missing or ambiguous')
        for item in [detail, matches[0]]:
            if tuple(item.get(key) for key in ('width', 'height', 'type')) != expected:
                raise IntegrationError('Current vendor template does not match exact tag model')
        mapping = detail.get('mappingtype')
        if type(mapping) is not int or not 0 <= mapping <= 2147483647:
            raise IntegrationError('Invalid verified vendor mapping type')
        if 'mappingtype' in matches[0] and matches[0]['mappingtype'] != mapping:
            raise IntegrationError('Vendor detail and catalog mapping mismatch')
        fields = detail.get('styleFileds')
        if (not isinstance(fields, list) or any(type(field) is not str for field in fields)
                or len(set(fields)) != len(fields) or set(fields) != set(receipt['bindings'])):
            raise IntegrationError('Current vendor fields do not match publication aliases')
        payload = {'mac': tag['mac'], 'styleid': native_id, 'mappingtype': mapping}
        photos = {}
        for alias, binding in receipt['bindings'].items():
            value = data[binding['field']] if binding['field'] else binding['static_value']
            if binding.get('renderer') and binding['field']:
                from .qr_png import qr_png
                renderer = binding['renderer']
                try:
                    raw = qr_png(renderer['prefix'] + value + renderer['suffix'],
                                 renderer['width'], renderer['height'], 'M')
                except (ValueError, TypeError, UnicodeError) as error:
                    raise ValidationError('Dynamic QR cannot fit the published geometry') from error
                digest = hashlib.sha256(raw).hexdigest()
                value = 'ESLM_' + digest[:12]
                photos[value] = (raw, renderer['width'], renderer['height'], digest)
            payload[alias] = value
        if not live_writes_authorized(confirmation):
            raise ForbiddenError('Live ESL writes are disabled or not explicitly confirmed')
        attempt = {'attempt_id': uuid.uuid4().hex, 'controller_id': controller_id,
                   'template_id': body['template_id'], 'vendor_id': native_id,
                   'draft_id': receipt['draft_id'], 'draft_revision': receipt['draft_revision']}
        # Commit independently before the vendor call: failures must not erase intent.
        with self.storage.connection() as c:
            service._audit(c, 'template.apply.attempted', 'tag', tag_id, attempt)
        try:
            for name, (raw, width, height, digest) in photos.items():
                if not live_writes_authorized(confirmation):
                    raise ForbiddenError('Live ESL writes are disabled or not explicitly confirmed')
                uploaded = client.upload_photo(name, raw, width, height)
                if (type(uploaded) is not dict or uploaded.get('name') != name
                        or uploaded.get('width') != width or uploaded.get('height') != height
                        or uploaded.get('sha256') != digest or uploaded.get('content_exact') is not True):
                    raise IntegrationError('Native QR photo upload could not be verified')
            if not live_writes_authorized(confirmation):
                raise ForbiddenError('Live ESL writes are disabled or not explicitly confirmed')
            verified = client.update_screen([payload], confirmation)
            if (not isinstance(verified, list) or len(verified) != 1 or not isinstance(verified[0], dict)
                    or verified[0].get('mac') != tag['mac']
                    or verified[0].get('_verified_status') not in {'updating', 'success'}):
                raise IntegrationError('Vendor status could not be verified; outcome may be unknown')
        except Exception as error:
            error_type = re.sub(r'[^A-Za-z0-9_]', '', type(error).__name__)[:80] or 'Exception'
            with self.storage.connection() as c:
                service._audit(c, 'template.apply.failed', 'tag', tag_id,
                               dict(attempt, error_type=error_type, outcome='unknown'))
            raise IntegrationError('Vendor update could not be verified; outcome may be unknown') from error
        status = verified[0]['_verified_status']
        with self.storage.connection() as c:
            c.execute("UPDATE tags SET template_id=?, test_data=?, status=?, configuration_source='local' WHERE id=? AND controller_id=?",
                      (body['template_id'], _json(data), status, tag_id, controller_id))
            service._audit(c, 'template.apply.verified', 'tag', tag_id, dict(attempt, status=status))
        return {'dispatched': 1, 'verified_tags': [{'mac': tag['mac'], 'status': status}], 'provenance': receipt}

    def list(self, controller_id=None):
        if controller_id is not None:
            _id(controller_id, 'controller_id')
        with self.storage.connection() as c:
            rows = c.execute('SELECT * FROM template_publications' + (' WHERE controller_id=?' if controller_id is not None else '') + ' ORDER BY controller_id,vendor_id', (controller_id,) if controller_id is not None else ()).fetchall()
        return [self._result(row) for row in rows]

    def get(self, controller_id, vendor_id):
        _id(controller_id, 'controller_id')
        vendor_id = _vendor_id(vendor_id)
        with self.storage.connection() as c:
            row = c.execute('SELECT * FROM template_publications WHERE controller_id=? AND vendor_id=?', (controller_id, vendor_id)).fetchone()
        if row is None:
            raise NotFoundError('Verified publication not found')
        return self._result(row)


def initialize(storage):
    """Initialize only the auxiliary table and return its reusable service."""
    publication = TemplatePublicationService(storage)
    publication.initialize()
    return publication
