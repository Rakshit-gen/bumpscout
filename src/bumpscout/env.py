"""Running the scratch copy's tests with a given set of package versions."""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .index import FixtureIndex
from .pins import read_pins
from .resolve import resolve
from .results import TestRun, parse
from .sandbox import Sandbox


@dataclass
class Outcome:
    versions: dict[str, str]  # what was installed
    tests: TestRun


class FixtureEnv:
    """Installs by copying package sources from a fixture index onto
    PYTHONPATH and runs `python -m unittest`. Nothing is downloaded."""

    def __init__(self, index: FixtureIndex, python: str | None = None, timeout: float = 120):
        self.index = index
        self.python = python or f"{sys.version_info.major}.{sys.version_info.minor}"
        self.timeout = timeout

    def run_tests(self, sb: Sandbox) -> Outcome:
        versions = resolve([p.text for p in read_pins(sb.root)], self.index, self.python)
        site = sb.root.parent / "site"
        shutil.rmtree(site, ignore_errors=True)
        site.mkdir()
        for name, version in versions.items():
            shutil.copytree(self.index.source(name, version), site, dirs_exist_ok=True)
        path = os.pathsep.join(str(p) for p in (site, sb.root / "src", sb.root))
        env = {**os.environ, "PYTHONPATH": path, "PYTHONDONTWRITEBYTECODE": "1"}
        cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]
        try:
            r = subprocess.run(
                cmd, cwd=sb.root, env=env, capture_output=True, text=True, timeout=self.timeout
            )
        except subprocess.TimeoutExpired:
            return Outcome(versions, TestRun(124, f"tests timed out after {self.timeout:.0f}s"))
        return Outcome(versions, parse(r.stdout + r.stderr, r.returncode))


def python_of(root: str | Path) -> str:
    """The lowest Python the project says it supports, e.g. '3.11'."""
    import tomllib

    py = Path(root) / "pyproject.toml"
    if py.is_file():
        spec = tomllib.loads(py.read_text()).get("project", {}).get("requires-python", "")
        for part in spec.split(","):
            part = part.strip()
            if part.startswith(">="):
                return ".".join(part[2:].strip().split(".")[:2])
    return f"{sys.version_info.major}.{sys.version_info.minor}"
