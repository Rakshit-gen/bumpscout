import unittest

from app.urls import depth


class UrlTests(unittest.TestCase):
    def test_depth(self):
        self.assertEqual(depth("/api/v1/users"), 3)
