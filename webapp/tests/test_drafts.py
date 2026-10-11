"""Contract tests for local-only, bounded template drafts."""
import math
import tempfile
import unittest
from pathlib import Path

from esl_web.service import ValidationError, ConflictError, NotFoundError
from esl_web.storage import Storage


def document():
    return {
        'schema_version': 1, 'name': 'Draft', 'model_id': '2.13TFT-BW',
        'sample_data': {'price': 1.5, 'name': 'Coffee', 'available': True, 'empty': None},
        'elements': [{
            'id': 'label', 'name': 'Label', 'type': 'text',
            'x': 0, 'y': 0, 'width': 250, 'height': 132,
            'text': 'Hello', 'field': 'name', 'prefix': '', 'suffix': '',
            'font_family': 'Arial', 'font_size': 16, 'bold': False,
            'italic': False, 'align': 'left', 'color': '#000000',
            'background': 'transparent', 'border_width': 0,
        }],
    }


class DraftTests(unittest.TestCase):
    def setUp(self):
        from esl_web.drafts import DraftService
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = Storage(Path(self.temp.name) / 'drafts.sqlite')
        self.storage.initialize()
        self.service = DraftService(self.storage)

    def test_initialize_is_explicit_idempotent_and_preserves_schema_version(self):
        with self.storage.connection() as connection:
            before = connection.execute('PRAGMA user_version').fetchone()[0]
            self.assertIsNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name='template_drafts'").fetchone())
        self.service.initialize()
        self.service.initialize()
        with self.storage.connection() as connection:
            self.assertEqual(before, connection.execute('PRAGMA user_version').fetchone()[0])
            self.assertIsNotNone(connection.execute(
                "SELECT name FROM sqlite_master WHERE name='template_drafts'").fetchone())

    def test_validate_returns_detached_canonical_document(self):
        original = document()
        canonical = self.service.validate(original)
        self.assertEqual(original, canonical)
        canonical['elements'][0]['text'] = 'Changed'
        self.assertEqual('Hello', original['elements'][0]['text'])
        for model, dimensions in [('2.13TFT-BW', (250, 132)),
                                  ('2.13EPD-BWR', (250, 122)),
                                  ('2.9EPD-BWR', (296, 128))]:
            for kind in ('text', 'rectangle', 'line'):
                item = document()
                item['model_id'] = model
                element = item['elements'][0]
                element.update(type=kind, width=dimensions[0], height=dimensions[1])
                if model != '2.13TFT-BW':
                    element.update(color='#ff0000', background='#ff0000')
                self.assertEqual(item, self.service.validate(item))
        repeated = document()
        repeated['elements'].append(dict(repeated['elements'][0], id='other'))
        self.service.validate(repeated)  # Repeated mapped fields are valid.

    def test_document_structure_and_size_are_bounded(self):
        invalid = [None, [], {}, dict(document(), extra=True)]
        for key, values in {
            'schema_version': [True, 0, 3, 1.0, '1'],
            'name': ['', ' ', 'x' * 201, None, 1],
            'model_id': ['unknown', [], None],
            'elements': [None, {}, [None], [document()['elements'][0]] * 101],
            'sample_data': [None, [], {'bad-key': 1}, {'x': []}, {'x': {}},
                            {'x': math.nan}, {'x': math.inf}, {'x': 'x' * 2001},
                            {f'k{i}': 1 for i in range(101)}],
        }.items():
            invalid.extend(dict(document(), **{key: value}) for value in values)
        missing = document()
        del missing['name']
        invalid.append(missing)
        duplicate = document()
        duplicate['elements'] *= 2
        invalid.append(duplicate)
        oversized = document()
        oversized['sample_data'] = {f'k{i}': '雪' * 2000 for i in range(100)}
        invalid.append(oversized)
        for item in invalid:
            with self.subTest(item=str(item)[:100]), self.assertRaises(ValidationError):
                self.service.validate(item)

    def test_every_element_field_is_required_and_checked(self):
        for key in document()['elements'][0]:
            item = document()
            del item['elements'][0][key]
            with self.subTest(missing=key), self.assertRaises(ValidationError):
                self.service.validate(item)
        bad_values = {
            'id': ['', ' ', 'x' * 65, 1], 'name': ['', ' ', 'x' * 201, None],
            'type': ['html', None, []], 'x': [-1, 250, True, 1.1],
            'y': [-1, 132, False, 1.1], 'width': [0, 251, True, 1.1],
            'height': [0, 133, True, 1.1], 'text': [None, 'x' * 2001],
            'field': ['1bad', 'x.y', '<html>', 'a' * 65, None],
            'prefix': [None, 'x' * 201], 'suffix': [None, 'x' * 201],
            'font_family': ['Comic Sans', []], 'font_size': [3, 97, True, 4.5],
            'bold': [0, 1, 'true'], 'italic': [0, None], 'align': ['justify', []],
            'color': ['#ff0000', '#000', '#FFFFFF', []],
            'background': ['#ff0000', 'none', []], 'border_width': [-1, 9, True, .5],
            'unknown': [1],
        }
        for key, values in bad_values.items():
            for value in values:
                item = document()
                item['elements'][0][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                    self.service.validate(item)
        item = document()
        item['elements'][0].update(x=249, y=131, width=1, height=1,
                                  type='line', font_size=4, border_width=8)
        self.service.validate(item)
        item['elements'][0]['width'] = 2
        with self.assertRaises(ValidationError):
            self.service.validate(item)

    def test_crud_roundtrip_snapshots_and_audit(self):
        import json
        import uuid
        self.service.initialize()
        self.assertEqual([], self.service.list())
        source = document()
        created = self.service.create(source)
        self.assertEqual({'id', 'revision', 'document', 'created_at', 'updated_at'}, set(created))
        self.assertEqual(created['id'], str(uuid.UUID(created['id'])))
        self.assertEqual(1, created['revision'])
        self.assertEqual(created['created_at'], created['updated_at'])
        source['elements'][0]['text'] = 'Mutated input'
        self.assertEqual('Hello', self.service.get(created['id'])['document']['elements'][0]['text'])
        changed = document()
        changed['name'] = "Local ' template"
        updated = self.service.update(created['id'], {'revision': 1, 'document': changed})
        self.assertEqual(2, updated['revision'])
        self.assertEqual(created['created_at'], updated['created_at'])
        self.assertEqual(changed, updated['document'])
        self.assertEqual([updated], self.service.list())
        updated['document']['name'] = 'Mutated result'
        self.assertEqual(changed, self.service.get(created['id'])['document'])
        self.assertIsNone(self.service.delete(created['id'], {'revision': 2}))
        self.assertEqual([], self.service.list())
        with self.assertRaises(NotFoundError):
            self.service.get(created['id'])
        with self.storage.connection() as connection:
            events = connection.execute('SELECT * FROM audit_events ORDER BY id').fetchall()
        self.assertEqual(['template_draft.created', 'template_draft.updated',
                          'template_draft.deleted'], [row['action'] for row in events])
        for event, revision in zip(events, [1, 2, 2]):
            self.assertEqual('template_draft', event['entity_type'])
            self.assertEqual(created['id'], event['entity_id'])
            self.assertEqual(revision, json.loads(event['details'])['revision'])

    def test_revision_identifier_and_payload_validation_never_mutate(self):
        self.service.initialize()
        created = self.service.create(document())
        draft_id = created['id']
        for revision in [True, False, 0, -1, 1.0, '1', None]:
            with self.subTest(revision=revision):
                for method, payload in [(self.service.update, {'revision': revision, 'document': document()}),
                                        (self.service.delete, {'revision': revision})]:
                    with self.assertRaises(ValidationError):
                        method(draft_id, payload)
        for payload in [None, {}, {'revision': 1},
                        {'revision': 1, 'document': document(), 'extra': 1}]:
            with self.assertRaises(ValidationError):
                self.service.update(draft_id, payload)
        for payload in [None, {}, {'revision': 1, 'extra': 1}]:
            with self.assertRaises(ValidationError):
                self.service.delete(draft_id, payload)
        for invalid_id in [None, [], "x';DROP TABLE template_drafts;--", 'x' * 65, '../x']:
            for method, args in [(self.service.get, ()),
                                 (self.service.update, ({'revision': 1, 'document': document()},)),
                                 (self.service.delete, ({'revision': 1},))]:
                with self.assertRaises(ValidationError):
                    method(invalid_id, *args)
        with self.assertRaises(ValidationError):
            self.service.create({})
        with self.assertRaises(ValidationError):
            self.service.update(draft_id, {'revision': 1, 'document': {}})
        self.assertEqual(created, self.service.get(draft_id))
        for method, payload in [(self.service.update, {'revision': 2, 'document': document()}),
                                (self.service.delete, {'revision': 2})]:
            with self.assertRaises(ConflictError):
                method(draft_id, payload)
        for method, args in [(self.service.get, ()),
                             (self.service.update, ({'revision': 1, 'document': document()},)),
                             (self.service.delete, ({'revision': 1},))]:
            with self.assertRaises(NotFoundError):
                method('00000000-0000-0000-0000-000000000000', *args)
        with self.storage.connection() as connection:
            self.assertEqual(1, connection.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])

    def test_audit_failure_rolls_back_each_mutation(self):
        import sqlite3
        self.service.initialize()
        created = self.service.create(document())
        with self.storage.connection() as connection:
            connection.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit_events "
                               "BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
        for method, args in [(self.service.create, (document(),)),
                             (self.service.update, (created['id'], {'revision': 1, 'document': document()})),
                             (self.service.delete, (created['id'], {'revision': 1}))]:
            with self.assertRaises(sqlite3.IntegrityError):
                method(*args)
            self.assertEqual([created], self.service.list())

    def test_concurrent_updates_have_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        self.service.initialize()
        created = self.service.create(document())
        barrier = Barrier(2)
        def update(name):
            item = document()
            item['name'] = name
            barrier.wait()
            try:
                return self.service.update(created['id'], {'revision': 1, 'document': item})
            except ConflictError:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(update, ['First', 'Second']))
        self.assertEqual(1, results.count('conflict'))
        self.assertEqual(2, self.service.get(created['id'])['revision'])
        with self.storage.connection() as connection:
            self.assertEqual(2, connection.execute('SELECT COUNT(*) FROM audit_events').fetchone()[0])


if __name__ == '__main__':
    unittest.main()
