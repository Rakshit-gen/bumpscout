import unittest

from app.text import heading, slugify


class TextTests(unittest.TestCase):
    def test_heading(self):
        self.assertEqual(heading("release notes"), ("Release Notes", "release-notes"))

    def test_slug_keeps_underscores(self):
        self.assertEqual(slugify("max_retries Setting"), "max_retries-setting")
