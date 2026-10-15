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
