import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Tests never reach a real model, even on a machine with a key set."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
