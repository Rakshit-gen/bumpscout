"""Built-in upgrades with known answers: a small project, a package index with
the releases involved, and what the right call is."""

import json
from dataclasses import dataclass
from pathlib import Path

from ..env import FixtureEnv, python_of
from ..index import FixtureIndex
from ..session import Session

ROOT = Path(__file__).parent
VERDICTS = ("safe", "needs-changes", "blocked")


@dataclass
class Scenario:
    name: str
    title: str
    package: str
    answer: dict  # verdict, version, files that need changes
    root: Path

    @property
    def project(self) -> Path:
        return self.root / "project"

    def session(self) -> Session:
        index = FixtureIndex(self.root / "index")
        return Session(self.project, index, FixtureEnv(index, python_of(self.project)))


def names() -> list[str]:
    return sorted(p.name for p in ROOT.iterdir() if (p / "scenario.json").is_file())


def load(name: str) -> Scenario:
    if name not in names():
        raise ValueError(f"no scenario {name!r}; try one of: {', '.join(names())}")
    data = json.loads((ROOT / name / "scenario.json").read_text())
    return Scenario(name, data["title"], data["package"], data["answer"], ROOT / name)
