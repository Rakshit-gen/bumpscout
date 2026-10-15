import unittest

from app.cache import cache_key


class CacheTests(unittest.TestCase):
    def test_key_ignores_order(self):
        self.assertEqual(cache_key({"b": 1, "a": 2}), cache_key({"a": 2, "b": 1}))
