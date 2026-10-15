from bumpscout import scenarios
from bumpscout.baseline import check


def run(name):
    sc = scenarios.load(name)
    s = sc.session()
    try:
        return check(s, sc.package)
    finally:
        s.close()


def test_safe_when_the_tests_pass():
    v = run("minor-safe")
    assert (v.verdict, v.version, v.new_spec) == ("safe", "1.4.0", "colorkit==1.4.0")


def test_needs_changes_points_at_the_file():
    v = run("renamed-function")
    assert (v.verdict, v.version, v.files) == ("needs-changes", "2.0.1", ["src/app/report.py"])
    assert any("render_table" in e for e in v.evidence)


def test_blocked_falls_back_to_the_newest_that_works():
    v = run("python-too-old")
    assert (v.verdict, v.version, v.fallback) == ("blocked", "3.0.0", "2.5.0")
    assert "Python 3.11" in v.reason


def test_yanked_releases_are_skipped():
    assert run("yanked-latest").version == "1.6.0"
