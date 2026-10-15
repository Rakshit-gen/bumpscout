import unittest

from app.client import fetch


class ClientTests(unittest.TestCase):
    def test_survives_two_drops(self):
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise ConnectionError("dropped")
            return "ok"

        self.assertEqual(fetch(flaky), "ok")
