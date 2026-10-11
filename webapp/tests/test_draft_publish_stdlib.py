import builtins
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from esl_web.draft_publish import translate_native_plan

class StdlibPublicationTests(unittest.TestCase):
    def test_photo_translation_without_pillow(self):
        original = builtins.__import__
        def restricted(name, *args, **kwargs):
            if name == 'PIL' or name.startswith('PIL.'):
                raise ImportError('Pillow is not a runtime dependency')
            return original(name, *args, **kwargs)
        root = Path(__file__).resolve().parents[1]
        path = root / 'template-presets/extended-sk/2.13EPD-BWR-technical.json'
        doc = json.loads(path.read_text())
        with patch('builtins.__import__', side_effect=restricted):
            self.assertTrue(translate_native_plan(doc)['fields'])