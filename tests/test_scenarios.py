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
