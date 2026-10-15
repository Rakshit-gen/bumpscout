import pytest

from bumpscout.verdict import Verdict


def test_verdict_values_are_checked():
    v = Verdict("tablet", "1.4.0", "2.0.1", "needs-changes", files=["src/app/report.py"])
    assert v.to_dict()["files"] == ["src/app/report.py"]
    with pytest.raises(ValueError, match="verdict must be one of"):
        Verdict("tablet", "1.4.0", "2.0.1", "probably fine")
