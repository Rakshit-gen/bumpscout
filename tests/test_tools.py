import pytest

from bumpscout import scenarios
from bumpscout.tools import CAP, SCHEMAS, Tools


@pytest.fixture
def tools(request):
    sc = scenarios.load(request.param)
    s = sc.session()
    yield Tools(s, sc.package)
    s.close()


def test_every_schema_has_a_tool():
    for sch in SCHEMAS:
        assert hasattr(Tools, "tool_" + sch["name"])


@pytest.mark.parametrize("tools", ["transitive-conflict"], indirect=True)
def test_project_info_and_versions(tools):
    info = tools.call("project_info", {})
    assert "python: 3.11" in info and "installed 2.2.0" in info and "tests passed" in info
    assert tools.call("versions", {}).splitlines() == [
        "2.4.0  needs shapes>=1,<2",
        "3.0.0  needs shapes>=2",
    ]


@pytest.mark.parametrize("tools", ["yanked-latest"], indirect=True)
def test_yanked_shows_and_errors_are_answers(tools):
    assert "1.6.1  YANKED" in tools.call("versions", {})
    assert tools.call("nope", {}) == "error: no tool named 'nope'"
    assert tools.call("versions", {"x": 1}).startswith("error:")
    assert len(tools.answers) == 3


def test_cap():
    from bumpscout.tools import _cap

    assert _cap("x" * (CAP + 5)).endswith("[... 5 more characters]")
