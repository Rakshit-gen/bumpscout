from bumpscout.search import search


def test_whole_words_and_attribute_access(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "a.py").write_text(
        "from tablet import render_table\nx = tablet.render_table(rows)\nrender_tables = 1\n"
    )
    (tmp_path / "tests" / "test_a.py").write_text("render_table([])\n")
    hits = search(tmp_path, "render_table")
    assert [(h.path, h.line) for h in hits] == [
        ("src/a.py", 1),
        ("src/a.py", 2),
        ("tests/test_a.py", 1),
    ]
    assert hits[-1].in_tests and not hits[0].in_tests
    assert str(hits[0]) == "src/a.py:1: from tablet import render_table"
    assert len(search(tmp_path, "render_table", limit=2)) == 2
