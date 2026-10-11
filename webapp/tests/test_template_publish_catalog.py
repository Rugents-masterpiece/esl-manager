"""Local-only catalog registration and exact template configuration contracts."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from esl_web.service import IntegrationError, Service, ValidationError
from esl_web.storage import Storage
from run_live import TemplatePublishClient


class TemplatePublishCatalogTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = Storage(Path(self.directory.name) / 'test.sqlite3')
        self.storage.initialize()
        self.storage.seed_demo()
        self.service = Service(self.storage)
        self.style = {'id': 301, 'name': 'Published', 'width': 296, 'height': 128,
                      'mappingtype': 2, 'type': 2, 'styleFileds': ['name', 'price'],
                      'rotate': 0, 'userid': 1, 'backgroundId': 0}

    def rows(self, table):
        with self.storage.connection() as connection:
            return [dict(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY 1')]

    def test_local_configuration_requires_exact_screen_type_without_changing_tag(self):
        payload = {'controller_id': 'legacy', 'mac': '00:11:22:33:44:55',
                   'device_model_id': '2.9EPD-BWR', 'width': 296, 'height': 128,
                   'router_id': 'router-main', 'template_id': 'tpl-default', 'test_data': {}}
        for screen_type in (1, None, 0):
            with self.storage.connection() as connection:
                connection.execute('UPDATE templates SET screen_type = ? WHERE id = ?',
                                   (screen_type, 'tpl-default'))
            before = self.rows('tags')
            with self.subTest(screen_type=screen_type), self.assertRaises(ValidationError):
                self.service.update_tag_configuration('tag-001', payload)
            self.assertEqual(self.rows('tags'), before)
            with self.assertRaises(ValidationError):
                self.service.create_staged_tag({**payload, 'mac': 'AA:BB:CC:DD:EE:FF'})
        with self.storage.connection() as connection:
            connection.execute('UPDATE templates SET screen_type = 2 WHERE id = ?', ('tpl-default',))
        updated = self.service.update_tag_configuration('tag-001', payload)
        self.assertEqual(updated['template_compatibility'], 'compatible')

    def test_tag_detail_marks_wrong_screen_type_incompatible_without_reassigning(self):
        with self.storage.connection() as connection:
            connection.execute('UPDATE templates SET screen_type = 1 WHERE id = ?', ('tpl-default',))
        detail = self.service.get_tag('tag-001')
        self.assertEqual(detail['template_id'], 'tpl-default')
        self.assertEqual(detail['template_compatibility'], 'incompatible')
        self.assertIsNone(detail['compatible_template'])

    def test_refresh_rejects_entire_invalid_catalog_before_opening_transaction(self):
        invalid = [None, {}, [self.style, self.style], [self.style, {'id': 302}],
                   [self.style, {**self.style, 'id': 302, 'rotate': True}],
                   [self.style, {**self.style, 'id': 302, 'userid': -1}],
                   [self.style, {**self.style, 'id': 302, 'type': True}],
                   [self.style, {**self.style, 'id': 302, 'styleFileds': ['']}]]
        for catalog in invalid:
            client = Mock()
            client.get_style_catalog.return_value = catalog
            with self.subTest(catalog=catalog), \
                 patch.object(self.storage, 'connection') as transaction, \
                 self.assertRaises(IntegrationError):
                self.service.refresh_template_catalog(client, 'legacy')
            transaction.assert_not_called()

    def test_refresh_is_atomic_when_a_local_upsert_fails(self):
        client = Mock()
        client.get_style_catalog.return_value = [self.style, {**self.style, 'id': 302}]
        before = {table: self.rows(table) for table in ('templates', 'local_ids', 'audit_events')}
        upsert = self.service.upsert_vendor_template
        def fail_second(connection, item, controller_id):
            if item['id'] == 302:
                raise IntegrationError('local failure')
            return upsert(connection, item, controller_id)
        with patch.object(self.service, 'upsert_vendor_template', side_effect=fail_second), \
             self.assertRaises(IntegrationError):
            self.service.refresh_template_catalog(client, 'legacy')
        self.assertEqual(before, {table: self.rows(table) for table in before})

    def test_refresh_scopes_same_vendor_ids_and_never_removes_old_templates(self):
        self.storage.configure_controllers([{'id': 'north', 'name': 'North', 'default': True},
                                            {'id': 'south', 'name': 'South', 'default': False}])
        client = Mock()
        client.get_style_catalog.return_value = [self.style]
        north = self.service.refresh_template_catalog(client, 'north')['items'][0]
        south = self.service.refresh_template_catalog(client, 'south')['items'][0]
        self.assertNotEqual(north['id'], south['id'])
        client.get_style_catalog.return_value = []
        empty = self.service.refresh_template_catalog(client, 'north')
        self.assertEqual(empty, {'items': [], 'synced': {'templates': 0}})
        templates = {item['id']: item for item in self.service.list_templates()}
        self.assertIn(north['id'], templates)
        self.assertIn(south['id'], templates)
        self.assertIn('tpl-default', templates)

    def test_configuration_checks_every_supported_family_and_controller(self):
        for model, width, height, screen in (
                ('2.13EPD-BWR', 250, 122, 2), ('2.13TFT-BW', 250, 132, 1),
                ('2.9EPD-BWR', 296, 128, 2)):
            with self.storage.connection() as connection:
                connection.execute('UPDATE templates SET width = ?, height = ?, screen_type = ? '
                                   'WHERE id = ?', (width, height, screen, 'tpl-default'))
            payload = {'controller_id': 'legacy', 'mac': 'AA:BB:CC:DD:EE:FF',
                       'device_model_id': model, 'width': width, 'height': height,
                       'router_id': 'router-main', 'template_id': 'tpl-default', 'test_data': {}}
            with self.storage.connection() as connection:
                Service._tag_dependencies(connection, payload)
                with self.assertRaises(ValidationError):
                    Service._tag_dependencies(connection, {**payload, 'height': height + 1})
            self.storage.configure_controllers([{'id': 'north', 'name': 'North', 'default': True}])
            with self.storage.connection() as connection:
                connection.execute("UPDATE templates SET controller_id = 'north' WHERE id = 'tpl-default'")
                with self.assertRaises(ValidationError):
                    Service._tag_dependencies(connection, payload)
                connection.execute("UPDATE templates SET controller_id = 'legacy' WHERE id = 'tpl-default'")

    def test_refresh_registers_native_catalog_without_inventory_or_tag_changes(self):
        upstream = Mock()
        upstream.get_style_catalog.return_value = [self.style]
        before = {table: self.rows(table) for table in ('tags', 'routers', 'product_tags')}
        result = self.service.refresh_template_catalog(TemplatePublishClient(upstream), 'legacy')
        self.assertEqual(result['synced'], {'templates': 1})
        self.assertEqual(len(result['items']), 1)
        item = result['items'][0]
        self.assertEqual((item['id'], item['vendor_id'], item['controller_id']),
                         ('301', '301', 'legacy'))
        self.assertEqual((item['width'], item['height'], item['screen_type']), (296, 128, 2))
        self.assertEqual(item['style_fields'], ['name', 'price'])
        self.assertEqual(upstream.mock_calls, [unittest.mock.call.get_style_catalog()])
        self.assertEqual(before, {table: self.rows(table) for table in before})
        self.assertEqual(self.service.list_audit(action='vendor.templates.refreshed')[0]['details'],
                         {'controller_id': 'legacy', 'templates': 1})
        again = self.service.refresh_template_catalog(TemplatePublishClient(upstream), 'legacy')
        self.assertEqual(again['items'][0]['id'], item['id'])


if __name__ == '__main__':
    unittest.main()
