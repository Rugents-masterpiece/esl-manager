"""Reject sample numbers that cannot survive a browser JSON round-trip."""
import unittest
from esl_web.drafts import DraftService
from esl_web.service import ValidationError
from test_drafts import document


class DraftNumberTests(unittest.TestCase):
    def test_unsafe_numbers_require_strings(self):
        for number in (9007199254740992, -9007199254740992, 1e20, 10**400):
            with self.subTest(number=number):
                item = document()
                item['sample_data'] = {'price': number}
                with self.assertRaises(ValidationError):
                    DraftService.validate(item)

    def test_strings_and_safe_numbers_round_trip(self):
        item = document()
        item['sample_data'] = {'code': '9007199254740993', 'price': 9007199254740991}
        self.assertEqual(DraftService.validate(item), item)
