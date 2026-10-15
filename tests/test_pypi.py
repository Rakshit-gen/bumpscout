import pytest

from bumpscout.pypi import PyPIIndex


def file(py=">=3.9", yanked=False):
    return {"requires_python": py, "yanked": yanked}


DATA = {
    "info": {"name": "Tablet", "project_urls": {}},
    "releases": {
        "1.10.0": [file()],
        "1.9.0": [file(py=None)],
        "2.0.0rc1": [file()],
        "2.0.0": [file(">=3.12"), file(">=3.12")],
        "2.0.1": [file(yanked=True)],
        "0.1": [],
        "not-a-version": [file()],
    },
}


def test_releases_from_the_json_api():
    urls = []

    def fetch(url, headers):
        urls.append(url)
        return DATA

    idx = PyPIIndex(fetch)
    rs = idx.releases("Tablet")
    assert [r.version for r in rs] == ["1.9.0", "1.10.0", "2.0.0", "2.0.1"]
    assert rs[0].requires_python == "" and rs[2].requires_python == ">=3.12"
    assert rs[3].yanked and not rs[2].yanked
    idx.releases("tablet")
    assert urls == ["https://pypi.org/pypi/tablet/json"]  # fetched once
    assert rs[0].notes.startswith("(no release notes: the package doesn't link")


def test_unknown_package():
    def fetch(url, headers):
        raise ValueError(f"{url} returned 404")

    with pytest.raises(ValueError, match="404"):
        PyPIIndex(fetch).releases("nope")


def test_notes_from_github_releases(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    data = {**DATA, "info": {"project_urls": {"Source": "https://github.com/acme/tablet.git"}}}
    gh = [{"tag_name": "v2.0.0", "body": "- `render_table` is now `render`.\n"}]
    seen = []

    def fetch(url, headers):
        seen.append((url, headers))
        return gh if "api.github.com" in url else data

    idx = PyPIIndex(fetch)
    idx.releases("tablet")
    rs = {r.version: r for r in idx.releases("tablet")}
    assert len(seen) == 2
    assert rs["2.0.0"].notes == "- `render_table` is now `render`."
    assert rs["1.9.0"].notes == "(no GitHub release for this version in acme/tablet)"
    assert seen[1] == (
        "https://api.github.com/repos/acme/tablet/releases?per_page=100",
        {"Authorization": "Bearer t"},
    )


def test_tag_versions():
    from bumpscout.pypi import tag_version

    assert [tag_version(t) for t in ("v1.2.0", "tablet-1.2.0", "tablet==1.2", "x")] == [
        "1.2.0",
        "1.2.0",
        "1.2",
        "x",
    ]
