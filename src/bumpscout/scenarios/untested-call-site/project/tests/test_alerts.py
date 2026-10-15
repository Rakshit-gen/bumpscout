import unittest

from app.alerts import subject


class AlertTests(unittest.TestCase):
    def test_subject(self):
        self.assertEqual(subject("warn", "disk at 80%"), "[WARN] disk at 80%")
