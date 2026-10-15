import unittest

from app.theme import brand_rgb


class ThemeTests(unittest.TestCase):
    def test_brand(self):
        self.assertEqual(brand_rgb(), (29, 78, 216))
