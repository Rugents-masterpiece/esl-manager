"""Read-only conversion of vendor layouts into unsaved local rendering documents.

No inventory refresh, database access, template cloning or vendor mutation occurs.
Screen family comes from the catalog's screen type, not getStyleData's alignment
``type``. Native rendering equivalence is deliberately not promised.
"""
from __future__ import annotations

import re
from typing import NoReturn

from .service import IntegrationError, NotFoundError, ValidationError
from .storage import LEGACY_CONTROLLER_ID

FAMILIES = {(250, 132, 1): '2.13TFT-BW', (250, 122, 2): '2.13EPD-BWR',
            (296, 128, 2): '2.9EPD-BWR'}
SOURCE_ID = re.compile(r'[1-9][0-9]{0,9}')


def _integer(value, field, minimum=0, maximum=2_147_483_647):
    pattern = r'[1-9][0-9]{0,9}' if field in {'id', 'component.id'} else r'[0-9]{1,10}'
    if isinstance(value, str) and re.fullmatch(pattern, value):
        value = int(value)
    if type(value) is not int or not minimum <= value <= maximum:
        raise IntegrationError('Invalid vendor source metadata', details={'field': field})
    return value


class DraftImportService:
    def __init__(self, client, controller_id):
        if client is None or controller_id == LEGACY_CONTROLLER_ID:
            raise ValidationError('A configured non-legacy controller is required',
                                  details={'field': 'controller_id'})
        self.client = client
        self.controller_id = controller_id
        self._catalog_metadata = {}

    def _read(self, method, *args):
        try:
            return getattr(self.client, method)(*args)
        except Exception as error:
            # Vendor errors can include credentials, cookies and transport URLs.
            raise IntegrationError('Vendor source read failed',
                                   details={'operation': method}) from error

    def catalog(self):
        raw = self._read('get_style_catalog')
        if not isinstance(raw, list) or len(raw) > 10_000:
            raise IntegrationError('Invalid vendor source catalog')
        items, seen = [], set()
        metadata = {}
        for row in raw:
            if not isinstance(row, dict):
                raise IntegrationError('Invalid vendor source catalog')
            source_id = str(_integer(row.get('id'), 'id', 1))
            if source_id in seen:
                raise IntegrationError('Duplicate vendor source id')
            seen.add(source_id)
            metadata[source_id] = row
            name = row.get('name') or row.get('descriptor')
            if not isinstance(name, str) or not name.strip() or len(name) > 200:
                raise IntegrationError('Invalid vendor source name')
            width = _integer(row.get('width'), 'width', 1, 10000)
            height = _integer(row.get('height'), 'height', 1, 10000)
            screen = None if row.get('type') is None else _integer(row['type'], 'screen_type')
            model = FAMILIES.get((width, height, screen)) if screen is not None else None
            items.append({'id': source_id, 'name': name, 'width': width, 'height': height,
                          'screen_type': screen, 'model': model, 'supported': model is not None})
        self._catalog_metadata = metadata
        return {'items': items, 'controller_id': self.controller_id}

    def convert(self, source_id):
        if (not isinstance(source_id, str) or SOURCE_ID.fullmatch(source_id) is None
                or int(source_id) > 2_147_483_647):
            raise ValidationError('Invalid source id', details={'field': 'id'})
        source = next((item for item in self.catalog()['items'] if item['id'] == source_id), None)
        if source is None:
            raise NotFoundError('Vendor source not found')
        if not source['supported']:
            raise ValidationError('Unsupported vendor source screen family',
                                  details={'field': 'model'})
        metadata = self._read('get_style_detail', int(source_id))
        if (not isinstance(metadata, dict)
                or _integer(metadata.get('id'), 'id', 1) != int(source_id)):
            raise IntegrationError('Invalid vendor source detail')
        for key in ('width', 'height'):
            if _integer(metadata.get(key), key, 1) != source[key]:
                raise IntegrationError('Vendor source metadata changed', details={'field': key})
        # Detail/data type may denote alignment, never use it as screen type.
        for record in (metadata, self._catalog_metadata[source_id]):
            if any(record.get(key) not in (None, 0, '0')
                   for key in ('backgroundId', 'backgroundID', 'background_id')):
                self._unsupported('background', 'Native background has no verified read-only mapping')
        if metadata.get('rotate') not in (None, 0, '0'):
            self._unsupported('rotate', 'Rotated native screens cannot be converted')
        layout = self._read('get_style_layout', int(source_id))
        if (not isinstance(layout, list) or len(layout) > 100
                or any(not isinstance(item, dict) for item in layout)):
            raise IntegrationError('Invalid vendor source layout')
        from .drafts import DraftService
        warnings, elements, seen = [], [], set()
        for index, item in enumerate(layout):
            component_id = str(_integer(item.get('id'), 'component.id', 1))
            if component_id in seen:
                self._unsupported('component.id', 'Duplicate native component id', index)
            seen.add(component_id)
            element = self._element(item, component_id, source, warnings, index)
            try:
                DraftService.validate({'schema_version': 2, 'name': source['name'],
                                       'model_id': source['model'], 'elements': [element],
                                       'sample_data': {}})
            except ValidationError as error:
                raise ValidationError('Native component cannot be represented in local document',
                                      details={**error.details, 'component_index': index}) from error
            elements.append(element)
        document = {'schema_version': 2, 'name': source['name'], 'model_id': source['model'],
                    'elements': elements, 'sample_data': {}}
        document = DraftService.validate(document)
        return {'document': document, 'warnings': warnings,
                'source': {'id': source_id, 'name': source['name'],
                           'controller_id': self.controller_id}}

    @staticmethod
    def _unsupported(field, message, index=None) -> NoReturn:
        details = {'field': field}
        if index is not None:
            details['component_index'] = index
        raise ValidationError(message, details=details)

    def _element(self, item, component_id, source, warnings, index):
        kind = item.get('type')
        if not isinstance(kind, str) or kind not in {'text', 'rectangle', 'line', 'barcode', 'qrcode', 'photo'}:
            self._unsupported('type', 'Unsupported native component; source was not imported', index)
        if item.get('status', True) is not True:
            self._unsupported('status', 'Disabled native component cannot be represented', index)
        style = item.get('style')
        if not isinstance(style, dict):
            self._unsupported('style', 'Missing native component style', index)
        def px(key, default=None) -> int:
            value = style.get(key, default)
            if type(value) is int:
                return value
            if isinstance(value, str) and re.fullmatch(r'-?[0-9]{1,6}(?:px)?', value):
                return int(value.removesuffix('px'))
            self._unsupported(key, 'Invalid native component pixel value', index)
        x, y, width, height = px('left'), px('top'), px('width'), px('height')
        if width <= 0 or height <= 0:
            self._unsupported('bounds', 'Invalid native component size', index)
        original = (x, y, width, height)
        right, bottom = min(source['width'], x + width), min(source['height'], y + height)
        x, y = max(0, x), max(0, y)
        width, height = right - x, bottom - y
        if width <= 0 or height <= 0:
            self._unsupported('bounds', 'Native component is entirely outside the screen', index)
        if original != (x, y, width, height):
            warnings.append(f'Prvok {component_id}: orezané hranice (clipped x,y,šírka,výška) '
                            f'{original} → {(x, y, width, height)} iba v lokálnej kópii.')
        known_styles = {'left', 'top', 'width', 'height', 'font-family', 'font-size',
                        'font-weight', 'font-style', 'text-align', 'color', 'background-color',
                        'border-width', 'board-width', 'transform', 'writing-mode',
                        'autoReacting', 'text-decoration', 'z-index', 'background-image'}
        if set(style) - known_styles:
            attributes = ', '.join(sorted(set(style) - known_styles))
            warnings.append(f'Prvok {component_id}: nepodporované vlastnosti štýlu ({attributes}) sa lokálne nevykreslia.')
        for key in ('font-family', 'font-style', 'color', 'background-color', 'text-align'):
            if key in style and not isinstance(style[key], str):
                self._unsupported(key, 'Invalid native style value', index)
        if type(style.get('font-weight', 400)) not in (int, str):
            self._unsupported('font-weight', 'Invalid native font weight', index)
        if style.get('background-image') not in (None, '', 'none'):
            self._unsupported('background-image', 'Unverified native background image; import refused', index)
        font = style.get('font-family', 'Arial')
        if font not in {'Arial', 'Verdana', 'Times New Roman', 'Courier New'}:
            warnings.append(f'Prvok {component_id}: pôvodný font {font!r} bol lokálne nahradený písmom Arial.')
            font = 'Arial'
        font_size = px('font-size', 18)
        border = px('border-width', style.get('board-width', 0))
        for field, value, low, high in [('font-size', font_size, 4, 96), ('border-width', border, 0, 8)]:
            if not low <= value <= high:
                self._unsupported(field, 'Unsupported native style range', index)
        for key in ('transform', 'writing-mode'):
            if style.get(key) not in (None, '', 'none', 'horizontal-tb'):
                self._unsupported(key, 'Unsupported native style transform', index)
        for key in ('autoReacting', 'text-decoration', 'z-index'):
            if style.get(key) not in (None, False, 0, '0', '', 'none'):
                warnings.append(f'Prvok {component_id}: vlastnosť {key} sa nevykreslí; pôvodné poradie prvkov sa zachovalo.')
        if style.get('font-style', 'normal') not in {'normal', 'italic'}:
            self._unsupported('font-style', 'Unsupported native font style', index)
        if style.get('font-weight', 400) not in {400, 700, '400', '700', 'normal', 'bold'}:
            self._unsupported('font-weight', 'Unsupported native font weight', index)
        binding = item.get('mpname', '')
        # Preserve native flat field keys verbatim, including Unicode and spaces;
        # the version-2 document validator owns their safety/length contract.
        element = {'id': f'vendor-{component_id}', 'name': item.get('name'),
                   'type': 'image' if kind == 'photo' else kind,
                   'x': x, 'y': y, 'width': width, 'height': height,
                   'text': item.get('text', ''), 'field': binding,
                   'prefix': item.get('prefix', ''), 'suffix': item.get('suffix', ''),
                   'font_family': font, 'font_size': font_size,
                   'bold': style.get('font-weight', 400) in {700, '700', 'bold'},
                   'italic': style.get('font-style') == 'italic',
                   'align': style.get('text-align', 'left'),
                   'color': style.get('color', '#000000').lower(),
                   'background': style.get('background-color', 'transparent').lower(),
                   'border_width': border}
        if kind == 'barcode':
            supplied = item.get('barcode_format', item.get('barcodeFormat'))
            if supplied not in (None, '', 'CODE128', 'Code128'):
                self._unsupported('barcode_format', 'Unsupported native barcode symbology', index)
            element['barcode_format'] = 'CODE128'
            if not supplied:
                warnings.append(f'Prvok {component_id}: pôvodný formát barcode nie je uvedený; lokálna kópia predpokladá Code128, bez záruky zhody s pôvodným kódom.')
        elif kind == 'qrcode':
            supplied = item.get('error_correction', item.get('errorCorrection'))
            if supplied not in (None, '', 'L', 'M', 'Q', 'H'):
                self._unsupported('error_correction', 'Unsupported native QR ECC', index)
            element['error_correction'] = supplied or 'M'
            if not supplied:
                warnings.append(f'Prvok {component_id}: pôvodná korekcia chýb QR (ECC) nie je uvedená; lokálna kópia používa úroveň M.')
        elif kind == 'photo':
            element['image_data'] = self._photo(item.get('text', ''), component_id, warnings, index)
            element['image_fit'] = 'fill'  # Native component.js uses background-size:100% 100%.
            if element['field']:
                self._unsupported('field', 'Dynamic native photo bindings cannot be represented safely', index)
        return element

    def _photo(self, reference, component_id, warnings, index):
        if reference == '':
            warnings.append(f'Prvok {component_id}: pôvodný obrázok chýba; image_data je prázdne, náhradný obrázok (placeholder) zariadenia sa nekopíruje.')
            return ''
        if (not isinstance(reference, str) or len(reference) > 200 or not reference.strip()
                or any(ord(c) < 32 for c in reference)
                or any(c in reference for c in '/\\\\:?#') or reference in {'.', '..'}):
            self._unsupported('photo', 'Photo must reference a known vendor photo name, not a URL or path', index)
        photos = self._read('get_photos')
        if (not isinstance(photos, list) or len(photos) > 10_000
                or any(not isinstance(photo, dict) for photo in photos)):
            raise IntegrationError('Invalid vendor photo catalog')
        matches = [photo for photo in photos if photo.get('name') == reference]
        if len(matches) != 1:
            self._unsupported('photo', 'Native photo is missing or ambiguous in vendor photo catalog', index)
        data = self._read('get_photo_data', reference)
        if (not isinstance(data, tuple) or len(data) != 2 or not isinstance(data[0], bytes)
                or data[1] != 'image/png' or not data[0].startswith(b'\x89PNG\r\n\x1a\n')
                or len(data[0]) > 128 * 1024):
            self._unsupported('photo', 'Vendor photo is not a bounded PNG; import refused', index)
        import base64
        return 'data:image/png;base64,' + base64.b64encode(data[0]).decode('ascii')
