import pytest
from test_index import make

from bumpscout.index import FixtureIndex
from bumpscout.resolve import ResolutionError, resolve


@pytest.fixture
def index(tmp_path):
    make(tmp_path, "web", "1.0.0", requires=["core>=1,<2"])
    make(tmp_path, "web", "2.0.0", requires=["core>=2"])
    make(tmp_path, "core", "1.5.0")
    make(tmp_path, "core", "2.1.0")
    make(tmp_path, "core", "2.2.0", yanked=True)
    make(tmp_path, "core", "3.0.0", requires_python=">=3.14")
    return FixtureIndex(tmp_path)


def test_newest_that_fits(index):
    assert resolve(["web"], index, "3.12") == {"web": "2.0.0", "core": "2.1.0"}
    assert resolve(["web<2"], index, "3.12") == {"web": "1.0.0", "core": "1.5.0"}
    assert resolve(["core"], index, "3.14") == {"core": "3.0.0"}


def test_markers_are_respected(index):
    assert resolve(["web; python_version < '3.10'", "core<2"], index, "3.12") == {"core": "1.5.0"}


def test_a_clash_names_both_sides(index):
    with pytest.raises(ResolutionError) as e:
        resolve(["web==2.0.0", "core<2"], index, "3.12")
    assert "the project needs core<2" in str(e.value) and "web 2.0.0 needs core>=2" in str(e.value)
