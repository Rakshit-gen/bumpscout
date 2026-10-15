import pytest

from bumpscout.sandbox import Sandbox


def test_copy_edit_patch_and_cleanup(tmp_path):
    proj = tmp_path / "app"
    (proj / ".git").mkdir(parents=True)
    (proj / "a.py").write_text("x = 1\n")
    with Sandbox(proj) as sb:
        assert not (sb.root / ".git").exists()
        sb.path("a.py").write_text("x = 2\n")
        sb.path("new.py").write_text("y = 1\n")
        patch = sb.patch()
        assert "-x = 1\n+x = 2\n" in patch and "+++ b/new.py" in patch
        assert (proj / "a.py").read_text() == "x = 1\n"
        with pytest.raises(ValueError, match="outside the project"):
            sb.path("../../etc/passwd")
        sb.reset()
        assert sb.patch() == ""
        root = sb.root
    assert not root.exists()


def test_root_is_resolved_so_paths_compare(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "a.py").write_text("x = 1\n")
    with Sandbox(tmp_path / "app") as sb:
        assert sb.root == sb.root.resolve()
        assert sb.path("a.py").relative_to(sb.root).as_posix() == "a.py"
