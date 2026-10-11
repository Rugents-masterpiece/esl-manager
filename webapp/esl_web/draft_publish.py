"""Detached draft-to-native publication. No database, server or tag dispatch coupling.

The caller supplies the already-authorized, serialized VendorClient. Registration
is optional: register(raw_metadata) may wrap Service.upsert_vendor_template using
its own transaction and controller_id. Without it, metadata is returned, not saved.
"""
from __future__ import annotations

import copy
import base64
import hashlib

import json
import re
import threading

from .drafts import DraftService, _png, PNG_PREFIX
from .native_raster import prepare_native_raster
from .qr_png import qr_png
from .service import IntegrationError, Service, ValidationError
from .storage import SUPPORTED_DEVICE_MODELS


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def translate_native_plan(document, *, media_assets=None):
    """Return a deterministic detached native plan without vendor calls.

    media_assets optionally maps original element IDs to explicitly prepared,
    exact-size PNG bytes. Never stretch/pad implicitly. Source hash always covers
    the original validated document; native_plan_sha256 covers translated content.
    bindings.static_value is raw native text (photo name for images). QR photos
    retain source field/affixes in a renderer recipe; their native affixes are
    empty because the raster already contains them. Rectangles are static RGBA
    photos, with white-text holes and explicit fills prepared offline. Dynamic
    apply must resolve binding.field from real data, not inject the publication's
    sample_data/fallback into product payloads.
    """
    doc = DraftService.validate(document)
    try:
        raster = prepare_native_raster(doc)
    except ValueError as error:
        raise ValidationError(str(error)) from error
    width, height = SUPPORTED_DEVICE_MODELS[doc['model_id']]
    alignment, screen_type = Service.CLONE_MODELS[(width, height)]
    fields, mapping = [], {}
    warnings = ['Native HuaweiSans substitutes local fonts; glyph/metric fidelity requires a live pilot.',
                'Controller clamps native border width to 1px; local border fidelity is not guaranteed.',
                'Controller ignores z-index (always 0); native layering is not guaranteed.',
                'Native single-line font adaptation is enabled for text to keep values inside their boxes; font size/slant may differ from the local editor.']
    for index, element in enumerate(doc['elements']):
        kind = {'rectangle': 'photo', 'image': 'photo', 'qrcode': 'photo'}.get(element['type'], element['type'])
        if kind not in {'text', 'barcode', 'qrcode', 'photo'}:
            raise ValidationError('Unsupported native element type: ' + element['type'])
        if element['italic']:
            raise ValidationError('Native italic style has no verified dispMs representation')
        alias = f'dp_{index:03d}_{_hash(element["id"])[:10]}'
        text = doc['sample_data'].get(element['field'], element['text']) if element['field'] else element['text']
        text = '' if text is None else ('true' if text else 'false') if type(text) is bool else str(text)
        if element['type'] == 'rectangle':
            if element['field'] or element['text'] or element['prefix'] or element['suffix']:
                raise ValidationError('Rectangle must be unbound and blank')
            text = ''
            warnings.append(f'{alias}: rectangle rendered as an exact-size RGBA photo with white-text holes.')
        if kind == 'barcode':
            warnings.append(f'{alias}: requested CODE128; native symbology and quiet zone require live decoding verification.')
        if element['type'] == 'qrcode':
            if element['error_correction'] != 'M':
                raise ValidationError(f"QR element {element['id']!r}: native publication requires exact ECC M")
            warnings.append(f'{alias}: QR ECC M rendered as a photo; native QR uses L, not M.')
        component: dict = dict(type=kind, feil=kind, mpname=alias, status=True,
                         table='tb_photos' if kind == 'photo' else 'tb_tagsandgoods',
                         text=str(text), prefix=element['prefix'], suffix=element['suffix'],
                         style={'left': f'{element["x"]}px', 'top': f'{element["y"]}px',
                                'width': f'{element["width"]}px', 'height': f'{element["height"]}px',
                                'font-family': 'HuaweiSans-Bold' if element['bold'] else 'HuaweiSans-Regular',
                                'font-size': f'{element["font_size"]}px',
                                'font-weight': '700' if element['bold'] else '400',
                                'text-align': element['align'], 'color': element['color'],
                                'background-color': '#ffffff00' if element['background'] == 'transparent' else element['background'],
                                'board-width': '1px',
                                'autoReacting': kind == 'text', 'text-decoration': 'none', 'z-index': 0})
        backgrounds = raster.get('text_backgrounds', raster['white_backgrounds'])
        if element['id'] in backgrounds:
            component['style']['background-color'] = backgrounds[element['id']]
        field: dict = dict(alias=alias, column_name=kind, component=component)
        if kind == 'photo':
            if element['type'] == 'rectangle':
                raw = raster['rectangles'][element['id']]
            elif element['type'] == 'qrcode':
                try:
                    raw = qr_png(element['prefix'] + text + element['suffix'],
                                 element['width'], element['height'], 'M')
                except ValueError as error:
                    raise ValidationError(f"QR element {element['id']!r}: {error}") from error
                component['prefix'] = component['suffix'] = ''
            else:
                if element['field'] or element['prefix'] or element['suffix'] or not element['image_data']:
                    raise ValidationError('Native photos require an explicit static PNG without a dynamic binding or affixes')
                supplied = (media_assets or {}).get(element['id'])
                raw = supplied if supplied is not None else base64.b64decode(element['image_data'].split(',', 1)[1], validate=True)
            if not isinstance(raw, bytes):
                raise ValidationError('Prepared media asset must be PNG bytes')
            _png(PNG_PREFIX + base64.b64encode(raw).decode('ascii'))
            size = (element['width'], element['height'])
            source_size = (int.from_bytes(raw[16:20]), int.from_bytes(raw[20:24]))
            if source_size != size:
                raise ValidationError('Photo dimensions differ; provide an explicitly fit/padded media_assets PNG')
            photo_name = f'ESLM_{hashlib.sha256(raw).hexdigest()[:12]}_{index:03d}'
            component['text'] = photo_name
            field['media'] = dict(name=photo_name, bytes=raw, width=size[0], height=size[1])
            warnings.append(f'{alias}: exact-size PNG; native color conversion requires live preview verification.')
        fields.append(field)
        mapping[alias] = dict(element_id=element['id'], field=element['field'],
                              prefix=element['prefix'], suffix=element['suffix'], fallback=component['text'],
                              static_value=component['text'])
        if element['type'] == 'qrcode':
            mapping[alias]['renderer'] = dict(type='qrcode', width=element['width'],
                                             height=element['height'], error_correction='M',
                                             prefix=element['prefix'], suffix=element['suffix'])
    return dict(name=doc['name'], model_id=doc['model_id'], width=width, height=height,
                alignment=alignment, screen_type=screen_type, fields=fields,
                mapping=mapping, bindings={alias: {key: copy.deepcopy(value) for key, value in entry.items()
                                                  if key in {'element_id', 'field', 'static_value', 'renderer'}}
                                           for alias, entry in mapping.items()}, source_sha256=_hash(doc),
                native_plan_sha256=_hash({'fields': [{k: v for k, v in f.items() if k != 'media'} for f in fields]}),
                warnings=warnings)


def _by_id(layout):
    if not isinstance(layout, list) or any(not isinstance(e, dict) for e in layout):
        raise IntegrationError('Invalid native component list')
    result, names = {}, set()
    for e in layout:
        component_id = Service._vendor_integer_value(e.get('id'), 'component id', minimum=1)
        if component_id in result or not e.get('name') or e['name'] in names:
            raise IntegrationError('Ambiguous native component identity')
        result[component_id] = e
        names.add(e['name'])
    return result


def _field_names(metadata):
    fields = metadata.get('styleFileds', metadata.get('styleFields'))
    if not isinstance(fields, list) or any(not isinstance(f, str) or not f for f in fields) or len(fields) != len(set(fields)):
        raise IntegrationError('Invalid authoritative styleFileds')
    return set(fields)


def verify_native_components(editor, native, target_id):
    """Verify captured endpoint-native dispMs, including signed color integers."""
    expected, actual = _by_id(editor), _by_id(native)
    if expected.keys() != actual.keys():
        raise IntegrationError('Native dispMs component IDs differ')
    for component_id, e in expected.items():
        n, style = actual[component_id], e['style']
        def px(key):
            value = style[key]
            if re.fullmatch(r'-?\d+px', str(value)) is None:
                raise IntegrationError('Invalid native pixel value')
            return int(str(value)[:-2])
        values = dict(id=component_id, styleid=target_id, name=e['name'],
                      columnType=e['type'], sourceColumn=e['feil'],
                      source=e.get('table', 'tb_tagsandgoods'), status=e['status'],
                      text=e['text'], startText=e['prefix'], endText=e['suffix'],
                      x=px('left'), y=px('top'), width=px('width'), height=px('height'),
                      textX=px('left'), textY=px('top'), fontFamily=style['font-family'],
                      fontSize=px('font-size'), fontBold='bold' if str(style['font-weight']) == '700' else 'normal',
                      lineBoarderWidth=px('board-width'), text_align=style['text-align'],
                      textDecoration=style.get('text-decoration', 'none'), vertical=False,
                      autoReacting=style.get('autoReacting', False), z_index=style.get('z-index', 0))
        for key, value in values.items():
            if key not in n or n[key] != value:
                raise IntegrationError(f'Native dispMs mismatch: {component_id}.{key}')
        for native_key, css_key in [('fontColor', 'color'), ('backgroundColor', 'background-color')]:
            value = n.get(native_key)
            if type(value) is not int or (value & 0xffffffff) != int(style[css_key][1:], 16):
                raise IntegrationError(f'Native dispMs mismatch: {component_id}.{native_key}')


class DraftPublishService:
    """New response-owned targets only. Caller supplies durable journal storage.

    journal is a mutable dict, not persistence; journal_sink receives snapshots
    before mutations and after readback. Protect journals and serialize operations
    per controller across processes. Incomplete journals refuse automatic replay.
    Verified journals support fresh-read idempotency; rollback is explicit.
    """
    def __init__(self, client, *, media_uploader=None, register=None,
                 journal_sink=None, controller_id='legacy'):
        self.client = client
        self.media_uploader = media_uploader
        self.register = register
        self.journal_sink = journal_sink
        self.controller_id = controller_id
        self._lock = threading.RLock()

    def _record(self, journal, **changes):
        journal.update(changes)
        if self.journal_sink is not None:
            self.journal_sink(copy.deepcopy(journal))

    def publish(self, document, target_name=None, *, journal=None, media_assets=None):
        """Publish one document. media_uploader is client.upload_photo-compatible.

        media_uploader(name, bytes, width, height) must reconcile its own outcome
        and raise unless verified; no upload retry here. register(raw_metadata)
        wraps Service.upsert_vendor_template in the caller's transaction. A failed
        registration leaves remote verified state available for retry.
        """
        with self._lock:
            plan = translate_native_plan(document, media_assets=media_assets)
            if any('media' in f for f in plan['fields']) and self.media_uploader is None:
                raise ValidationError('Explicit media_uploader=client.upload_photo is required')
            name = plan['name'] if target_name is None else target_name
            if not isinstance(name, str) or not name.strip() or len(name) > 200 or any(ord(c) < 32 or c in '/\\?#' for c in name):
                raise ValidationError('Invalid target_name')
            j = journal if journal is not None else {}
            key = _hash([self.controller_id, plan['source_sha256'], plan['native_plan_sha256'], name])
            if j:
                if j.get('key') != key or j.get('controller_id') != self.controller_id:
                    raise ValidationError('Journal does not match source/name/controller')
                if j.get('status') != 'verified':
                    raise IntegrationError('Incomplete journal: refuse automatic mutation replay')
                result = self._verify(plan, j['owned_target_id'], name, j['mappingtype'], j['desired_layout'])
                result['registered'] = bool(j.get('registered'))
                if self.register is not None and not result['registered']:
                    self.register(copy.deepcopy(result['raw_metadata']))
                    self._record(j, registered=True)
                    result['registered'] = True
                result['journal'] = copy.deepcopy(j)
                return result
            client = self.client
            before = Service._catalog_by_id(Service._clone_catalog(client))
            if any(item.get('name') == name for item in before.values()):
                raise ValidationError('Target name already exists; no name-only adoption')
            self._record(j, version=1, key=key, controller_id=self.controller_id,
                         source_sha256=plan['source_sha256'], target_name=name,
                         preexisting_ids=sorted(before), owned_target_id=None,
                         status='creating', registered=False, uploaded_media=[])
            try:
                try:
                    target = client.create_style(plan['alignment'])
                except Exception as error:
                    Service._clone_catalog(client)
                    raise IntegrationError('Create outcome ambiguous; no target ownership') from error
                if type(target) is not int or not 0 < target <= 2147483647 or target in before:
                    raise IntegrationError('Create response did not establish target ownership')
                after = Service._catalog_by_id(Service._clone_catalog(client))
                if target not in after:
                    raise IntegrationError('Create response target absent from fresh catalog')
                self._record(j, owned_target_id=target, allowed_names=[after[target]['name'], name], status='building')
                data = client.get_style_data(target)
                if data.get('id') != target:
                    raise IntegrationError('Created style data identity mismatch')
                mappingtype = Service._vendor_integer_value(data.get('mappingtype'), 'mappingtype', minimum=1)
                self._record(j, mappingtype=mappingtype)
                desired = []
                old_layout = _by_id(client.get_style_layout(target))
                old_fields = _field_names(client.get_style_detail(target))
                for field in plan['fields']:
                    if 'media' in field:
                        media = field['media']
                        self._record(j, pending_operation={'kind': 'upload', 'name': media['name']})
                        assert self.media_uploader is not None
                        self.media_uploader(media['name'], media['bytes'], media['width'], media['height'])
                        self._record(j, uploaded_media=j['uploaded_media'] + [dict(
                            name=media['name'], width=media['width'], height=media['height'],
                            sha256=hashlib.sha256(media['bytes']).hexdigest())])
                    if field['alias'] in old_fields:
                        raise IntegrationError('Unexpected existing field alias in new target')
                    self._record(j, pending_operation={'kind': 'add', 'alias': field['alias']})
                    reply = None
                    try:
                        reply = client.add_style_field(target, mappingtype, field['column_name'], field['alias'])
                    except Exception:
                        pass
                    new_layout = _by_id(client.get_style_layout(target))
                    expected_fields = old_fields | {field['alias']}
                    # Only the controller's exact integer application-success
                    # reply permits deferred metadata verification. All unknown
                    # outcomes are reconciled once, never retried.
                    if type(reply) is not int or reply != 1:
                        if _field_names(client.get_style_detail(target)) != expected_fields:
                            raise IntegrationError('Field creation could not be unambiguously verified')
                    added_ids = new_layout.keys() - old_layout.keys()
                    if not old_layout.keys() <= new_layout.keys() or len(added_ids) != 1:
                        raise IntegrationError('Field creation could not be unambiguously verified')
                    created = new_layout[next(iter(added_ids))]
                    if created.get('type') != field['column_name'] or created.get('mpname') not in (field['alias'], field['column_name']):
                        raise IntegrationError('Native field kind or mapping differs')
                    component = copy.deepcopy(field['component'])
                    component.update(id=created['id'], name=created['name'])
                    desired.append(component)
                    old_layout, old_fields = new_layout, expected_fields
                    self._record(j, desired_layout=copy.deepcopy(desired), pending_operation=None)
                self._record(j, pending_operation={'kind': 'rename'})
                try:
                    client.rename_style(target, plan['alignment'], name)
                except Exception:
                    pass
                renamed = Service._catalog_by_id(Service._clone_catalog(client))
                if target not in renamed or renamed[target].get('name') != name or client.get_style_data(target).get('name') != name:
                    raise IntegrationError('Rename could not be verified')
                self._record(j, pending_operation={'kind': 'save'})
                try:
                    client.save_style_layout(target, desired)
                except Exception:
                    pass
                result = self._verify(plan, target, name, mappingtype, desired)
                self._record(j, status='verified', pending_operation=None,
                             layout_sha256=result['layout_sha256'], preview_sha256=result['preview_sha256'])
            except Exception as error:
                self._record(j, status='failed', failure_type=type(error).__name__)
                if isinstance(error, (ValidationError, IntegrationError)):
                    raise
                raise IntegrationError('Native draft publication failed; consult caller journal') from error
            if self.register is not None:
                self.register(copy.deepcopy(result['raw_metadata']))
                self._record(j, registered=True)
                result['registered'] = True
            result['journal'] = copy.deepcopy(j)
            return result

    def _verify(self, plan, target, name, mappingtype, desired):
        client = self.client
        data = client.get_style_data(target)
        layout = client.get_style_layout(target)
        metadata = client.get_style_detail(target)
        catalog = Service._catalog_by_id(Service._clone_catalog(client))
        if target not in catalog:
            raise IntegrationError('Target absent from fresh catalog')
        for record, native_type in [(catalog[target], plan['screen_type']), (metadata, plan['screen_type']), (data, plan['alignment'])]:
            expected = dict(id=target, name=name, width=plan['width'], height=plan['height'], mappingtype=mappingtype, type=native_type)
            if any(record.get(k) != v for k, v in expected.items()):
                raise IntegrationError('Target identity/model/mapping/name readback differs')
        if _field_names(metadata) != set(plan['mapping']):
            raise IntegrationError('Authoritative styleFileds differ')
        expected_ids, actual_ids = _by_id(desired), _by_id(layout)
        if expected_ids.keys() != actual_ids.keys():
            raise IntegrationError('Native editor component IDs differ')
        restored = copy.deepcopy(layout)
        for component in restored:
            expected = expected_ids[int(component['id'])]
            # Permit only the documented kind normalization, with authoritative
            # alias membership and the one-call-created owned-ID association.
            if component.get('mpname') not in (expected['mpname'], expected['type']):
                raise IntegrationError('Native editor mapping changed unexpectedly')
            component['mpname'] = expected['mpname']
        if Service._normalized_editor_layout(restored) != Service._normalized_editor_layout(desired):
            raise IntegrationError('Native editor readback differs')
        verify_native_components(desired, data.get('dispMs'), target)
        preview = client.get_template_preview(target)
        if not isinstance(preview, tuple) or len(preview) != 2 or not isinstance(preview[0], bytes) or not preview[0] or not isinstance(preview[1], str) or not preview[1].startswith('image/'):
            raise IntegrationError('Native preview missing')
        component_mapping = {e['mpname']: dict(component_id=e['id'], component_name=e['name'], **plan['mapping'][e['mpname']]) for e in desired}
        return dict(vendor_id=target, name=name, controller_id=self.controller_id,
                    verified=True, registered=False, mappingtype=mappingtype,
                    model_id=plan['model_id'], mapping=copy.deepcopy(plan['mapping']), bindings=copy.deepcopy(plan['bindings']),
                    component_mapping=component_mapping, source_sha256=plan['source_sha256'],
                    raw_metadata=copy.deepcopy(metadata), native_data=copy.deepcopy(data),
                    native_layout=copy.deepcopy(layout), layout_sha256=_hash(restored),
                    preview_sha256=hashlib.sha256(preview[0]).hexdigest(),
                    preview_type=preview[1], preview_bytes=preview[0], warnings=list(plan['warnings']))

    def rollback(self, journal):
        """Explicit one-call delete; no photo deletion or registered-target removal.

        Caller must authorize rollback and protect journal integrity. Photos are
        not deleted because no verified photo-delete contract exists.
        """
        with self._lock:
            target = journal.get('owned_target_id')
            if journal.get('controller_id') != self.controller_id or type(target) is not int or target in journal.get('preexisting_ids', []) or journal.get('registered'):
                raise IntegrationError('Refusing rollback: target ownership/registration is unsafe')
            before = Service._catalog_by_id(Service._clone_catalog(self.client))
            if target not in before:
                self._record(journal, status='rolled_back')
                return True
            data = self.client.get_style_data(target)
            if before[target].get('name') not in journal.get('allowed_names', []) or data.get('id') != target or data.get('name') != before[target]['name'] or data.get('mappingtype') != journal.get('mappingtype'):
                raise IntegrationError('Refusing rollback of changed target')
            self._record(journal, pending_operation={'kind': 'delete'}, status='rolling_back')
            try:
                self.client.delete_style(target)
            except Exception:
                pass
            if target in Service._catalog_by_id(Service._clone_catalog(self.client)):
                raise IntegrationError('Rollback deletion could not be verified')
            self._record(journal, status='rolled_back', pending_operation=None)
            return True
