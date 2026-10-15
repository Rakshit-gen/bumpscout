import unittest

from app.settings import settings


class SettingsTests(unittest.TestCase):
    def test_overrides(self):
        self.assertEqual(settings('{"workers": 4}'), {"debug": False, "workers": 4})
