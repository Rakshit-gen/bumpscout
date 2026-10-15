from bumpscout.results import parse

UNITTEST = """\
F.E
======================================================================
ERROR: test_wrap (tests.test_text.TextTests.test_wrap)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/x/tests/test_text.py", line 9, in test_wrap
    self.assertEqual(fmt.title_block("abc"), "abc")
AttributeError: module 'textwrapx' has no attribute 'wrap_text'

======================================================================
FAIL: test_round (tests.test_money.MoneyTests.test_round)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: '2.68' != '2.67'

----------------------------------------------------------------------
Ran 3 tests in 0.001s

FAILED (failures=1, errors=1)
"""


def test_unittest_output():
    r = parse(UNITTEST, 1)
    assert not r.ok and r.ran == 3
    assert r.failures == [
        ("TextTests.test_wrap", "AttributeError: module 'textwrapx' has no attribute 'wrap_text'"),
        ("MoneyTests.test_round", "AssertionError: '2.68' != '2.67'"),
    ]
    assert "tests failed: 2 of 3 ran" in r.describe()


def test_pytest_output_and_passing_runs():
    r = parse("FAILED tests/test_a.py::test_x - assert 1 == 2\n1 failed, 4 passed in 0.2s\n", 1)
    assert r.ran == 5 and r.failures == [("tests/test_a.py::test_x", "assert 1 == 2")]
    ok = parse("....\nRan 4 tests in 0.000s\n\nOK\n", 0)
    assert ok.ok and ok.describe() == "tests passed (4 ran)"


def test_a_crash_shows_the_last_lines():
    r = parse("Traceback (most recent call last):\nImportError: boom\n", 1)
    assert "ImportError: boom" in r.describe()
