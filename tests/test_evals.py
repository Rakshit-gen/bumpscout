from bumpscout import evals
from bumpscout.baseline import check
from bumpscout.verdict import Verdict


def test_score():
    ans = {"verdict": "blocked", "version": "3.0.0", "fallback": "2.5.0", "files": []}
    s = evals.score(ans, Verdict("j", "2.3.0", "3.0.0", "blocked", fallback="2.5.0"))
    assert s.solved and not s.harmful
    s = evals.score(ans, Verdict("j", "2.3.0", "3.0.0", "blocked"))
    assert s.verdict and not s.version
    s = evals.score(ans, Verdict("j", "2.3.0", "3.0.0", "safe"))
    assert s.harmful and not s.solved


def test_needs_changes_counts_only_with_a_patch_to_the_files():
    ans = {"verdict": "needs-changes", "version": "2.0.0", "files": ["src/a.py"]}
    v = Verdict("t", "1.0", "2.0.0", "needs-changes", files=["src/a.py"])
    assert not evals.score(ans, v).solved
    v.patch = "--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-x\n+y\n"
    assert evals.score(ans, v).solved


def test_rules_on_two_scenarios():
    scores = evals.run(check, ["minor-safe", "untested-call-site"])
    assert [s.solved for s in scores] == [True, False]
    assert scores[1].harmful  # tests pass, so the rules call it safe
    out = evals.table(scores)
    assert out.splitlines()[-1] == "solved 1/2, harmful 1"
