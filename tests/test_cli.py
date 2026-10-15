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
