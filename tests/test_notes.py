from bumpscout.index import Release
from bumpscout.notes import changed_names, combined


def test_changed_names():
    notes = (
        "## 2.0.0\n- `render_table` is now `render`.\n- Removed `load_ini()`.\n"
        "- Add `lighten`.\n- `parse()` without `fmt` is deprecated.\n"
    )
    assert changed_names(notes) == ["render_table", "render", "load_ini", "parse", "fmt"]
    assert changed_names("- Faster `dumps`.\n") == []


def test_combined_is_newest_first_with_headings():
    rs = [Release("1.1.0", notes="- fix"), Release("1.2.0", notes="## 1.2.0\n- add x")]
    assert combined(rs) == "## 1.2.0\n- add x\n\n## 1.1.0\n- fix"
    assert combined([Release("2.0.0")]) == "## 2.0.0\n(no release notes)"
