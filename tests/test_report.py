from bumpscout.report import markdown
from bumpscout.verdict import Verdict


def test_markdown():
    v = Verdict(
        "tablet",
        "1.4.0",
        "2.0.1",
        "needs-changes",
        "render_table is now render",
        files=["src/app/report.py"],
        patch="--- a/src/app/report.py\n",
        new_spec="tablet<3,>=2.0.1",
        evidence=["ImportError: cannot import name 'render_table'"],
        steps=["try 2.0.1"],
    )
    out = markdown(v)
    assert out.startswith("# tablet 1.4.0 to 2.0.1: upgrade needs code changes\n")
    assert "- src/app/report.py" in out and "```diff\n--- a/src/app/report.py\n```" in out
    assert "How it got there" not in out and "1. try 2.0.1" in markdown(v, verbose=True)


def test_blocked_says_what_works():
    v = Verdict("j", "2.3.0", "3.0.0", "blocked", fallback="2.5.0")
    assert "Newest version that works: 2.5.0." in markdown(v)
    assert "No newer version works." in markdown(Verdict("j", "2.3.0", "3.0.0", "blocked"))
