from test_env import project
from test_index import make

from bumpscout.env import FixtureEnv
from bumpscout.index import FixtureIndex
from bumpscout.session import Session


def test_try_versions_and_keep_code_edits(tmp_path):
    for v in ("1.0.0", "2.0.0"):
        make(tmp_path / "index", "colorkit", v)
    project(tmp_path / "app", "colorkit>=1,<2", 'self.assertEqual(colorkit.VERSION, "1.0.0")')
    idx = FixtureIndex(tmp_path / "index")
    s = Session(tmp_path / "app", idx, FixtureEnv(idx))
    try:
        assert s.before.tests.ok and s.installed("ColorKit") == "1.0.0"
        a = s.try_version("colorkit", "2.0.0")
        assert not a.outcome.tests.ok and not a.patched
        t = s.sandbox.path("tests/test_app.py")
        t.write_text(t.read_text().replace('"1.0.0"', '"2.0.0"'))
        a = s.try_version("colorkit", "2.0.0")
        assert a.outcome.tests.ok and a.patched
        assert "pyproject.toml" not in s.code_patch() and '"2.0.0"' in s.code_patch()
        assert (tmp_path / "app" / "tests" / "test_app.py").read_text().count('"1.0.0"') == 1
    finally:
        s.close()
