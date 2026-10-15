from test_index import make

from bumpscout.env import FixtureEnv, python_of
from bumpscout.index import FixtureIndex
from bumpscout.sandbox import Sandbox


def project(root, dep, test_body):
    (root / "tests").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "app"\nrequires-python = ">=3.11"\ndependencies = ["{dep}"]\n'
    )
    (root / "tests" / "__init__.py").write_text("")
    (root / "tests" / "test_app.py").write_text(
        "import unittest\nimport colorkit\n\n\nclass T(unittest.TestCase):\n"
        f"    def test_it(self):\n        {test_body}\n"
    )


def test_runs_the_copy_against_the_index(tmp_path):
    make(tmp_path / "index", "colorkit", "1.0.0")
    make(tmp_path / "index", "colorkit", "2.0.0")
    project(tmp_path / "app", "colorkit<2", 'self.assertEqual(colorkit.VERSION, "1.0.0")')
    env = FixtureEnv(FixtureIndex(tmp_path / "index"))
    with Sandbox(tmp_path / "app") as sb:
        out = env.run_tests(sb)
        assert out.versions == {"colorkit": "1.0.0"} and out.tests.ok and out.tests.ran == 1
        (sb.root / "pyproject.toml").write_text(
            (sb.root / "pyproject.toml").read_text().replace("colorkit<2", "colorkit==2.0.0")
        )
        out = env.run_tests(sb)
        assert not out.tests.ok and out.tests.failures[0][0] == "T.test_it"
        assert sb.patch().count("colorkit==2.0.0") == 1  # the site folder isn't in the patch
    assert python_of(tmp_path / "app") == "3.11"


def fake_uv(install_err=""):
    from subprocess import CompletedProcess

    cmds = []

    def run(cmd, cwd, **kw):
        cmds.append(cmd)
        if cmd[:2] == ["uv", "venv"]:
            (cwd.parent / "venv").mkdir()
        if cmd[:3] == ["uv", "pip", "install"] and install_err:
            return CompletedProcess(cmd, 1, "", install_err)
        if cmd[:3] == ["uv", "pip", "freeze"]:
            return CompletedProcess(cmd, 0, "Tablet==2.0.1\npytest==9.1.1\n", "")
        if "pytest" in cmd:
            return CompletedProcess(cmd, 0, "3 passed in 0.1s\n", "")
        return CompletedProcess(cmd, 0, "", "")

    return run, cmds


def test_uv_env_installs_pins_and_test_deps(tmp_path):
    from bumpscout.env import UvEnv

    app = tmp_path / "app"
    app.mkdir()
    (app / "pyproject.toml").write_text(
        '[project]\ndependencies = ["tablet==2.0.1"]\n'
        '[project.optional-dependencies]\ntest = ["hypothesis"]\n'
        '[dependency-groups]\ndev = ["pytest-mock", {include-group = "lint"}]\n'
    )
    run, cmds = fake_uv()
    with Sandbox(app) as sb:
        out = UvEnv("3.12", run=run).run_tests(sb)
        UvEnv("3.12", run=run).run_tests(sb)
    assert out.versions == {"tablet": "2.0.1", "pytest": "9.1.1"} and out.tests.ran == 3
    assert [c[:2] for c in cmds].count(["uv", "venv"]) == 1  # the venv is reused
    assert cmds[1][-4:] == ["tablet==2.0.1", "pytest-mock", "hypothesis", "pytest"]


def test_uv_env_no_solution_is_a_resolution_error(tmp_path):
    import pytest

    from bumpscout.env import UvEnv
    from bumpscout.resolve import ResolutionError

    (tmp_path / "app").mkdir()
    run, _ = fake_uv("  x No solution found when resolving: tablet==9 needs Python>=3.14")
    with Sandbox(tmp_path / "app") as sb, pytest.raises(ResolutionError, match="Python>=3.14"):
        UvEnv(run=run).run_tests(sb)
    run, _ = fake_uv("error: network unreachable")
    with Sandbox(tmp_path / "app") as sb, pytest.raises(RuntimeError, match="network"):
        UvEnv(run=run).run_tests(sb)
