import json

import pytest

from bumpscout.index import FixtureIndex, between


def make(root, name, version, notes="", **meta):
    d = root / name / version
    (d / "src" / name).mkdir(parents=True)
    (d / "src" / name / "__init__.py").write_text(f'VERSION = "{version}"\n')
    (d / "meta.json").write_text(json.dumps(meta))
    if notes:
        (d / "notes.md").write_text(notes)


def test_fixture_index(tmp_path):
    for v in ("1.10.0", "1.2.0", "2.0.0"):
        make(tmp_path, "colorkit", v, notes=f"# {v}\n", requires_python=">=3.9")
    idx = FixtureIndex(tmp_path)
    rel = idx.releases("ColorKit")
    assert [r.version for r in rel] == ["1.2.0", "1.10.0", "2.0.0"]
    assert rel[0].requires_python == ">=3.9" and rel[0].notes == "# 1.2.0\n"
    assert [r.version for r in between(rel, "1.2.0", "2.0.0")] == ["1.10.0", "2.0.0"]
    assert (idx.source("colorkit", "2.0.0") / "colorkit" / "__init__.py").is_file()
    with pytest.raises(ValueError, match="not in the index"):
        idx.releases("nope")
