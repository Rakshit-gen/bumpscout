import pytest

from bumpscout import scenarios
from bumpscout.checks import check, patched_files
from bumpscout.verdict import Verdict


@pytest.fixture
def sess(request):
    sc = scenarios.load(request.param)
    s = sc.session()
    yield s
    s.close()


def V(*a, **kw):
    return Verdict(*a, **kw)


@pytest.mark.parametrize("sess", ["renamed-function"], indirect=True)
def test_safe_with_failing_tests_becomes_needs_changes(sess):
    v = check(V("tablet", "1.4.0", "2.0.1", "safe", evidence=["made up"]), sess, ["nothing"])
    assert v.verdict == "needs-changes" and not v.patch
    assert any("tests failed" in n for n in v.notes)
    assert v.evidence == [] and "made up" in v.notes[0]


@pytest.mark.parametrize("sess", ["renamed-function"], indirect=True)
def test_a_working_patch_is_kept_with_its_files(sess):
    f = sess.sandbox.path("src/app/report.py")
    f.write_text(f.read_text().replace("render_table", "render"))
    v = check(V("tablet", "1.4.0", "2.0.1", "safe"), sess, [])
    assert v.verdict == "needs-changes" and v.files == ["src/app/report.py"]
    assert patched_files(v.patch) == ["src/app/report.py"]
    assert v.new_spec == "tablet<3,>=2.0.1"


@pytest.mark.parametrize("sess", ["python-too-old"], indirect=True)
def test_blocked_and_the_fallback_are_tried(sess):
    v = check(V("jsonfast", "2.3.0", "3.0.0", "safe"), sess, [])
    assert v.verdict == "blocked" and not v.fallback
    v = check(V("jsonfast", "2.3.0", "3.0.0", "blocked", fallback="2.5.0"), sess, [])
    assert v.fallback == "2.5.0" and v.new_spec == "jsonfast==2.5.0" and not v.notes


@pytest.mark.parametrize("sess", ["minor-safe"], indirect=True)
def test_blocked_that_installs_is_not_blocked(sess):
    v = check(V("colorkit", "1.2.0", "1.4.0", "blocked", fallback="1.3.0"), sess, [])
    assert v.verdict == "safe" and not v.fallback


@pytest.mark.parametrize("sess", ["scary-notes-but-safe"], indirect=True)
def test_needs_changes_without_a_patch_is_noted(sess):
    v = check(V("strutil", "1.3.0", "2.0.0", "needs-changes", files=["src/app/text.py"]), sess, [])
    assert v.verdict == "needs-changes" and "no patch" in v.notes[-1]
