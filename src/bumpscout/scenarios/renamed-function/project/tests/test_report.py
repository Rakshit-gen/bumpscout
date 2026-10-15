import unittest

from app.report import sales_report


class ReportTests(unittest.TestCase):
    def test_rows_line_up(self):
        out = sales_report({"west": 12, "east": 7})
        self.assertEqual(out.splitlines(), ["region  total", "east    7", "west    12"])
