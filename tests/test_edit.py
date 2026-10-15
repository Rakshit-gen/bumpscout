from bumpscout.edit import proposed_spec, set_pin
from bumpscout.pins import read_pins


def test_proposed_spec_keeps_the_style():
    assert proposed_spec("==1.2.0", "2.0.1") == "==2.0.1"
    assert proposed_spec("", "2.0") == ">=2.0"
    assert proposed_spec(">=1.2,<2", "2.1.0") == ">=2.1.0,<3"
    assert proposed_spec(">=1.2,<3", "2.1.0") == ">=2.1.0,<3"
    assert proposed_spec(">=1.2,!=1.5.0", "1.6") == ">=1.6,!=1.5.0"
    assert proposed_spec("~=1.2", "2.0") == ">=2.0"


def test_set_pin_keeps_extras_and_markers(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        "[project]\ndependencies = [\n    \"httpx[http2]>=0.27,<1; python_version >= '3.11'\",\n]\n"
    )
    (pin,) = read_pins(tmp_path)
    new = set_pin(tmp_path, pin, ">=1.0.1,<2")
    assert new == "httpx[http2]<2,>=1.0.1; python_version >= '3.11'"
    assert read_pins(tmp_path)[0].spec == "<2,>=1.0.1"
