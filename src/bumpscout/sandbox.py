"""A scratch copy of the project. Upgrades are tried here; the project
itself is never written to."""

import difflib
import shutil
import tempfile
from pathlib import Path

IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "*.pyc",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
)


class Sandbox:
    def __init__(self, project: str | Path):
        self.project = Path(project).resolve()
        if not self.project.is_dir():
            raise ValueError(f"{project} is not a folder")
        self._tmp = tempfile.TemporaryDirectory(prefix="bumpscout-")
        self.root = (
            Path(self._tmp.name).resolve() / self.project.name
        )  # /var is /private/var on macOS
        shutil.copytree(self.project, self.root, ignore=IGNORE)

    def close(self) -> None:
        self._tmp.cleanup()

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def path(self, rel: str) -> Path:
        """A path inside the copy; refuses anything that escapes it."""
        p = (self.root / rel).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError(f"{rel} is outside the project")
        return p

    def reset(self) -> None:
        """Throw away every change made to the copy."""
        shutil.rmtree(self.root)
        shutil.copytree(self.project, self.root, ignore=IGNORE)

    def patch(self) -> str:
        """A unified diff of the copy against the project (text files only)."""
        out = []
        files = {p.relative_to(self.root) for p in self.root.rglob("*") if p.is_file()}
        for rel in sorted(files):
            new = self.root / rel
            old = self.project / rel
            try:
                b = new.read_text()
                a = old.read_text() if old.is_file() else ""
            except UnicodeDecodeError:
                continue
            if a != b:
                out += difflib.unified_diff(
                    a.splitlines(keepends=True),
                    b.splitlines(keepends=True),
                    f"a/{rel}",
                    f"b/{rel}",
                )
        return "".join(out)
