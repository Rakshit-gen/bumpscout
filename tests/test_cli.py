import json

from bumpscout.cli import main


def test_scenarios(capsys):
    assert main(["scenarios"]) == 0
    assert "renamed-function" in capsys.readouterr().out


def test_check_a_scenario(capsys):
    assert main(["check", "renamed-function", "-v"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("# tablet 1.4.0 to 2.0.1: upgrade needs code changes")
    assert "1. try 2.0.1: tests failed" in out


def test_check_json(capsys):
    assert main(["check", "minor-safe", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "safe"


def test_eval_exits_1_unless_all_solved(capsys):
    assert main(["eval", "minor-safe"]) == 0
    assert main(["eval", "minor-safe", "untested-call-site"]) == 1
    assert "solved 1/2, harmful 1" in capsys.readouterr().out


def test_bad_input(capsys):
    assert main(["check", "nope"]) == 2
    assert "no scenario 'nope'" in capsys.readouterr().err


def test_model_choice(monkeypatch):
    from bumpscout.baseline import check
    from bumpscout.cli import checker

    assert checker(None) is check
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert checker(None) is not check and checker("rules") is check
    assert main(["check", "minor-safe", "--model", "gpt"]) == 2


def test_write_patch_needs_a_patch(tmp_path, capsys):
    out = tmp_path / "fix.patch"
    assert main(["check", "renamed-function", "--write-patch", str(out)]) == 1
    assert not out.exists() and "no patch" in capsys.readouterr().err


def test_a_folder_needs_a_package(tmp_path, capsys):
    assert main(["check", str(tmp_path)]) == 2
    assert "name the dependency" in capsys.readouterr().err


def test_a_folder_uses_pypi_and_uv(tmp_path, monkeypatch):
    from bumpscout import cli

    seen = {}

    class FakeSession:
        def __init__(self, project, index, env):
            seen.update(index=type(index).__name__, env=type(env).__name__, python=env.python)

    monkeypatch.setattr("bumpscout.session.Session", FakeSession)
    (tmp_path / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.12"\n')
    s, package = cli.session_for(str(tmp_path), "tablet")
    assert package == "tablet"
    assert seen == {"index": "PyPIIndex", "env": "UvEnv", "python": "3.12"}
