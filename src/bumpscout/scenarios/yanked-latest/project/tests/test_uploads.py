import unittest

from app.uploads import allowed


class UploadTests(unittest.TestCase):
    def test_allowed(self):
        self.assertTrue(allowed("scan.PDF"))
        self.assertFalse(allowed("run.exe"))
