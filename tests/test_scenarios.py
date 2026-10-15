import pytest

from bumpscout import scenarios
from bumpscout.scenarios import VERDICTS


@pytest.mark.parametrize("name", scenarios.names())
def test_scenario_is_well_formed_and_its_tests_pass_today(name):
    sc = scenarios.load(name)
    assert sc.title and sc.answer["verdict"] in VERDICTS and sc.answer["version"]
    s = sc.session()
    try:
        assert s.before.tests.ok, s.before.tests.describe()
        assert s.installed(sc.package)
    finally:
        s.close()


def test_unknown():
    with pytest.raises(ValueError, match="no scenario"):
        scenarios.load("nope")


@pytest.mark.parametrize("name", scenarios.names())
def test_the_answer_holds(name):
    """Safe answers pass as they are; blocked ones can't install but the
    fallback can; files named as needing changes exist."""
    sc = scenarios.load(name)
    s = sc.session()
    try:
        for f in sc.answer["files"]:
            assert (sc.project / f).is_file()
        a = s.try_version(sc.package, sc.answer["version"])
        if sc.answer["verdict"] == "safe":
            assert a.outcome.tests.ok, a.outcome.tests.describe()
        if sc.answer["verdict"] == "blocked":
            assert a.blocked
            assert s.try_version(sc.package, sc.answer["fallback"]).outcome.tests.ok
    finally:
        s.close()
