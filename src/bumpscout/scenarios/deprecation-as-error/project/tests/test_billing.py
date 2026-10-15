import unittest
import warnings

from app.billing import days_overdue


class BillingTests(unittest.TestCase):
    def setUp(self):
        # this project fails on any warning
        ctx = warnings.catch_warnings()
        ctx.__enter__()
        self.addCleanup(ctx.__exit__, None, None, None)
        warnings.simplefilter("error")

    def test_overdue(self):
        self.assertEqual(days_overdue("2026-03-01", "2026-03-11"), 10)
        self.assertEqual(days_overdue("2026-03-11", "2026-03-01"), 0)
