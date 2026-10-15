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

    def fetch(url):
        urls.append(url)
        return DATA

    idx = PyPIIndex(fetch)
    rs = idx.releases("Tablet")
    assert [r.version for r in rs] == ["1.9.0", "1.10.0", "2.0.0", "2.0.1"]
    assert rs[0].requires_python == "" and rs[2].requires_python == ">=3.12"
    assert rs[3].yanked and not rs[2].yanked
    idx.releases("tablet")
    assert urls == ["https://pypi.org/pypi/tablet/json"]  # fetched once


def test_unknown_package():
    def fetch(url):
        raise ValueError(f"{url} returned 404")

    with pytest.raises(ValueError, match="404"):
        PyPIIndex(fetch).releases("nope")
