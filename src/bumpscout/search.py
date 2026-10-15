"""Finding where the project uses a name."""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Hit:
    path: str  # relative, with forward slashes
    line: int
    text: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.text}"

    @property
    def in_tests(self) -> bool:
        return self.path.startswith("tests/") or "/tests/" in self.path


def search(root: str | Path, name: str, limit: int = 50) -> list[Hit]:
    """Lines in the project's .py files that mention `name` as a whole word.
    `a.b` matches the attribute access too."""
    root = Path(root)
    pattern = re.compile(rf"(?<![\w.]){re.escape(name)}(?!\w)|\.{re.escape(name)}(?!\w)")
    hits = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        for i, text in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if pattern.search(text):
                hits.append(Hit(rel, i, text.strip()))
                if len(hits) >= limit:
                    return hits
    return hits
