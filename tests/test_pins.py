import pytest

from bumpscout.pins import find, read_pins


def test_reads_pyproject_and_requirements(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "app"\ndependencies = ["Requests>=2.31,<3", "typing_extensions"]\n'
    )
    (tmp_path / "requirements-dev.txt").write_text(
        "# tools\n-r requirements.txt\npytest==8.4.2  # tests\nnot a requirement!!\n"
    )
    pins = read_pins(tmp_path)
    assert [(p.name, p.spec, p.source) for p in pins] == [
        ("requests", "<3,>=2.31", "pyproject.toml"),
        ("typing-extensions", "", "pyproject.toml"),
        ("pytest", "==8.4.2", "requirements-dev.txt"),
    ]
    assert find(pins, "Typing_Extensions").text == "typing_extensions"
    with pytest.raises(ValueError, match="not a direct dependency"):
        find(pins, "flask")
