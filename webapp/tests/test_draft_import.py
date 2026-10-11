"""Read-only source catalog contracts against native vendor shapes."""
import importlib
import unittest
from unittest.mock import Mock, call

from esl_web.service import IntegrationError, ValidationError


def native(kind='text', **extra):
    return {'id': 2615, 'name': 'text2', 'type': kind, 'mpname': 'PriceRetail',
            'text': '999,99', 'prefix': '', 'suffix': '€', 'status': True,
            'style': {'left': '105px', 'top': '52px', 'width': '134px', 'height': '32px',
                      'font-family': 'HuaweiSans-Bold', 'font-size': '28px',
                      'color': '#ffffff', 'background-color': '#000000',
                      'board-width': '1px', 'font-weight': 700, 'text-align': 'right'}, **extra}


def importer(layout=None):
    from esl_web.draft_import import DraftImportService
    client = Mock()
    metadata = {'id': 145, 'name': 'EPD', 'width': 250, 'height': 122, 'type': 2,
                'backgroundId': 0, 'rotate': 0}
    client.get_style_catalog.return_value = [metadata]
    client.get_style_detail.return_value = metadata
    client.get_style_layout.return_value = [native()] if layout is None else layout
    return DraftImportService(client, 'shop'), client


class ConversionTests(unittest.TestCase):
    def test_native_text_preserves_bindings_and_emits_font_warning(self):
        service, client = importer()
        result = service.convert('145')
        element = result['document']['elements'][0]
        self.assertEqual(result['document']['schema_version'], 2)
        self.assertEqual(result['source'], {'id': '145', 'name': 'EPD', 'controller_id': 'shop'})
        self.assertEqual(element['field'], 'PriceRetail')
        self.assertEqual(element['text'], '999,99')
        self.assertEqual(element['suffix'], '€')
        self.assertEqual(element['border_width'], 1)
        self.assertTrue(element['bold'])
        self.assertEqual(element['font_family'], 'Arial')
        self.assertTrue(any('font' in warning for warning in result['warnings']))
        self.assertEqual(client.mock_calls, [call.get_style_catalog(), call.get_style_detail(145),
                                             call.get_style_layout(145)])

    def test_unmapped_native_style_is_diagnosed_not_silently_dropped(self):
        item = native()
        item['style']['letter-spacing'] = '2px'
        service, _ = importer([item])
        result = service.convert('145')
        self.assertTrue(any('nepodporované vlastnosti' in warning and 'letter-spacing' in warning
                            for warning in result['warnings']))

    def test_native_backgroundID_alias_cannot_be_silently_omitted(self):
        service, client = importer()
        client.get_style_detail.return_value = {**client.get_style_detail.return_value, 'backgroundID': 50}
        with self.assertRaises(ValidationError) as raised:
            service.convert('145')
        self.assertEqual(raised.exception.details['field'], 'background')

    def test_flat_unicode_space_bindings_are_preserved_verbatim(self):
        for binding in ('价格', '商品名', 'pozadie názvu', 'kod položky', 'test '):
            with self.subTest(binding=binding):
                service, _ = importer([native(mpname=binding)])
                result = service.convert('145')
                self.assertEqual(result['document']['elements'][0]['field'], binding)

    def test_native_binding_outside_local_schema_is_rejected_with_component_diagnostic(self):
        service, _ = importer([native(mpname='bad\x00field')])
        with self.assertRaises(ValidationError) as raised:
            service.convert('145')
        self.assertEqual(raised.exception.details['component_index'], 0)
        self.assertEqual(raised.exception.details['field'], 'field')

    def test_unknown_duplicate_disabled_and_impossible_components_reject_whole_import(self):
        for layout in ([native('unknown')], [native(), native()], [native(status=False)],
                       [native(style={'left': '300px', 'top': '0px', 'width': '5px', 'height': '5px'})]):
            with self.subTest(layout=layout):
                service, client = importer(layout)
                with self.assertRaises(ValidationError) as raised:
                    service.convert('145')
                self.assertIn('component_index', raised.exception.details)
                self.assertTrue(all(c[0] in {'get_style_catalog', 'get_style_detail', 'get_style_layout'}
                                    for c in client.mock_calls))

    def test_missing_or_ambiguous_photo_rejects_without_photo_data_request(self):
        for photos in ([], [{'name': 'logo.png'}, {'name': 'logo.png'}]):
            service, client = importer([native('photo', text='logo.png', mpname='')])
            client.get_photos.return_value = photos
            with self.assertRaises(ValidationError):
                service.convert('145')
            client.get_photo_data.assert_not_called()

    def test_alignment_type_in_detail_is_not_screen_type(self):
        service, client = importer()
        client.get_style_detail.return_value = {**client.get_style_detail.return_value, 'type': 9}
        self.assertEqual(service.convert('145')['document']['model_id'], '2.13EPD-BWR')

    def test_malformed_styles_have_explicit_validation_diagnostics(self):
        for key, value in [('color', None), ('background-color', {}), ('font-family', []),
                           ('font-weight', {}), ('transform', 'rotate(90deg)'),
                           ('background-image', 'url(http://internal/private)')]:
            item = native()
            item['style'][key] = value
            service, _ = importer([item])
            with self.subTest(key=key), self.assertRaises(ValidationError) as raised:
                service.convert('145')
            self.assertIn('field', raised.exception.details)

    def test_source_and_component_identifiers_are_not_repaired(self):
        service, client = importer()
        client.get_style_catalog.return_value[0]['id'] = '0145'
        with self.assertRaises(IntegrationError):
            service.catalog()
        service, _ = importer([native(id='02615')])
        with self.assertRaises(IntegrationError):
            service.convert('145')

    def test_codes_report_assumed_local_defaults(self):
        for kind, key, value, warning in [('barcode', 'barcode_format', 'CODE128', 'Code128'),
                                          ('qrcode', 'error_correction', 'M', 'ECC')]:
            with self.subTest(kind=kind):
                service, _ = importer([native(kind, text='123456', suffix='')])
                result = service.convert('145')
                self.assertEqual(result['document']['elements'][0][key], value)
                self.assertTrue(any(warning in text for text in result['warnings']))

    def test_photo_is_resolved_only_through_known_authenticated_vendor_catalog(self):
        import base64
        import struct
        import zlib
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
               + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\x00\xff')) + chunk(b'IEND', b''))
        service, client = importer([native('photo', text='logo.png', mpname='')])
        client.get_photos.return_value = [{'id': 7, 'name': 'logo.png'}]
        client.get_photo_data.return_value = (png, 'image/png')
        result = service.convert('145')
        element = result['document']['elements'][0]
        self.assertEqual(element['type'], 'image')
        self.assertEqual(element['image_fit'], 'fill')
        self.assertEqual(element['image_data'], 'data:image/png;base64,' + base64.b64encode(png).decode())
        client.get_photo_data.assert_called_once_with('logo.png')

    def test_photo_without_reference_has_explicit_disabled_warning(self):
        service, client = importer([native('photo', text='', mpname='')])
        result = service.convert('145')
        self.assertEqual(result['document']['elements'][0]['image_data'], '')
        self.assertTrue(any('image_data je prázdne' in warning for warning in result['warnings']))
        client.get_photos.assert_not_called()

    def test_external_image_reference_is_rejected_before_any_image_read(self):
        service, client = importer([native('photo', text='http://127.0.0.1/private', mpname='')])
        with self.assertRaises(ValidationError):
            service.convert('145')
        client.get_photos.assert_not_called()
        client.get_photo_data.assert_not_called()

    def test_out_of_bounds_is_explicitly_clipped_without_mutating_source(self):
        item = native()
        item['style'].update({'left': '165px', 'width': '90px'})
        service, _ = importer([item])
        result = service.convert('145')
        self.assertEqual(result['document']['elements'][0]['width'], 85)
        self.assertEqual(item['style']['width'], '90px')
        self.assertTrue(any('90' in w and '85' in w and 'clip' in w for w in result['warnings']))



class SourceCatalogTests(unittest.TestCase):
    def test_catalog_uses_exact_screen_family_without_storage_or_writes(self):
        module = importlib.import_module('esl_web.draft_import')
        client = Mock()
        client.get_style_catalog.return_value = [
            {'id': 145, 'name': 'EPD', 'width': 250, 'height': 122, 'type': 2},
            {'id': 147, 'name': 'TFT', 'width': 250, 'height': 132, 'type': 1},
            {'id': 150, 'name': 'Wrong screen', 'width': 250, 'height': 132, 'type': 2},
        ]
        result = module.DraftImportService(client, 'shop').catalog()
        self.assertEqual(result['controller_id'], 'shop')
        self.assertEqual([row['model'] for row in result['items']],
                         ['2.13EPD-BWR', '2.13TFT-BW', None])
        self.assertEqual([row['supported'] for row in result['items']], [True, True, False])
        self.assertEqual(client.mock_calls, [unittest.mock.call.get_style_catalog()])


if __name__ == '__main__':
    unittest.main()
