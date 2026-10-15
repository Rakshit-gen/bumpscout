import json

from scripted import Scripted, call

from bumpscout import scenarios
from bumpscout.agent import investigate, parse_conclusion


def done(**kw):
    return json.dumps({"verdict": "safe", "version": "", "files": [], "evidence": [], **kw})


def run(name, replies, **kw):
    sc = scenarios.load(name)
    s = sc.session()
    m = Scripted(replies)
    try:
        return investigate(s, sc.package, m, **kw), m
    finally:
        s.close()


def test_finds_the_untested_call_site_and_fixes_it():
    edit = {"path": "src/app/alerts.py", "old": "send_mail(", "new": "send_email("}
    v, m = run(
        "untested-call-site",
        [
            [call("project_info")],
            [call("release_notes", 1), call("search_code", 2, name="send_mail")],
            [call("edit_file", 3, **edit)],
            [call("try_upgrade", 4, version="2.0.0")],
            "Done.\n"
            + done(
                verdict="needs-changes",
                version="2.0.0",
                files=["src/app/alerts.py"],
                evidence=["- `send_mail` is renamed to `send_email`."],
            ),
        ],
    )
    assert (v.verdict, v.files, v.notes) == ("needs-changes", ["src/app/alerts.py"], [])
    assert "+    notifykit.send_email(ONCALL" in v.patch
    assert v.steps[0] == "project_info()" and v.steps[-1] == "check: try 2.0.0"
    tool_msgs = [x for x in m.seen[-1][0] if x["role"] == "tool"]
    assert "(with your code edits)" in tool_msgs[-1]["content"]


def test_repeats_of_fixed_answers_are_not_rerun_and_budget_forces_a_conclusion():
    v, m = run(
        "minor-safe",
        [
            [call("versions")],
            [call("versions", 1)],
            [call("try_upgrade", 2, version="1.4.0")],
            done(version="1.4.0"),
        ],
        budget=2,
    )
    assert v.steps[:2] == ["versions()", "try_upgrade(version='1.4.0')"]
    assert "already answered" in m.seen[2][0][-1]["content"]
    assert m.seen[-1][1] == [] and v.verdict == "safe"


def test_one_retry_on_a_bad_reply_then_unknown():
    v, m = run("minor-safe", ["no json here", "still nothing"])
    assert v.verdict == "unknown" and "no usable conclusion" in v.notes[0]
    assert "That wasn't valid" in m.seen[1][0][-1]["content"]


def test_parse_conclusion():
    v = parse_conclusion(done(version="2.0", files="a.py", evidence="x"), "p", "1.0")
    assert (v.files, v.evidence) == (["a.py"], ["x"])


def test_the_patch_applies_to_the_real_project(tmp_path):
    import shutil
    import subprocess

    path = "src/app/report.py"
    v, _ = run(
        "renamed-function",
        [
            [call("edit_file", 0, path=path, old="import render_table", new="import render")],
            [call("edit_file", 1, path=path, old="return render_table(", new="return render(")],
            done(verdict="needs-changes", version="2.0.1"),
        ],
    )
    assert v.files == ["src/app/report.py"]
    proj = shutil.copytree(scenarios.load("renamed-function").project, tmp_path / "p")
    (tmp_path / "fix.patch").write_text(v.patch)
    r = subprocess.run(["git", "apply", str(tmp_path / "fix.patch")], cwd=proj, capture_output=True)
    assert r.returncode == 0, r.stderr
    assert "return render(rows)" in (proj / "src/app/report.py").read_text()
