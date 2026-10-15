"""Running the scratch copy's tests with a given set of package versions."""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from packaging.utils import canonicalize_name

from .index import FixtureIndex
from .pins import read_pins
from .resolve import ResolutionError, resolve
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


def dev_requirements(root: Path) -> list[str]:
    """Extra packages the tests may need: the dev dependency group and any
    test or dev extras."""
    import tomllib

    py = root / "pyproject.toml"
    if not py.is_file():
        return []
    data = tomllib.loads(py.read_text())
    extras = data.get("project", {}).get("optional-dependencies", {})
    found = data.get("dependency-groups", {}).get("dev", [])
    for k in ("test", "tests", "dev"):
        found += extras.get(k, [])
    return [x for x in found if isinstance(x, str)]


class UvEnv:
    """For real projects: a virtualenv next to the scratch copy, packages
    installed by uv from PyPI, tests run with pytest. The venv goes away with
    the copy; uv's cache keeps repeat installs fast."""

    def __init__(self, python: str | None = None, timeout: float = 600, run=subprocess.run):
        self.python = python or f"{sys.version_info.major}.{sys.version_info.minor}"
        self.timeout = timeout
        self.run = run

    def _run(self, cmd: list[str], cwd: Path, **kw) -> subprocess.CompletedProcess:
        return self.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=self.timeout, **kw)

    def run_tests(self, sb: Sandbox) -> Outcome:
        venv = sb.root.parent / "venv"
        py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if not venv.exists():
            r = self._run(["uv", "venv", "--quiet", "--python", self.python, str(venv)], sb.root)
            if r.returncode:
                raise RuntimeError(f"uv venv failed: {r.stderr.strip()[-500:]}")
        reqs = [p.text for p in read_pins(sb.root)] + dev_requirements(sb.root) + ["pytest"]
        r = self._run(["uv", "pip", "install", "--quiet", "--python", str(py), *reqs], sb.root)
        if r.returncode:
            err = r.stderr.strip()
            if "No solution found" in err:
                raise ResolutionError(err[err.find("No solution found") :][:800])
            raise RuntimeError(f"uv pip install failed: {err[-500:]}")
        freeze = self._run(["uv", "pip", "freeze", "--python", str(py)], sb.root).stdout
        versions = {}
        for line in freeze.splitlines():
            name, sep, version = line.partition("==")
            if sep:
                versions[canonicalize_name(name)] = version.strip()
        path = os.pathsep.join(str(p) for p in (sb.root / "src", sb.root))
        env = {**os.environ, "PYTHONPATH": path, "PYTHONDONTWRITEBYTECODE": "1"}
        cmd = [str(py), "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        try:
            t = self._run(cmd, sb.root, env=env)
        except subprocess.TimeoutExpired:
            return Outcome(versions, TestRun(124, f"tests timed out after {self.timeout:.0f}s"))
        return Outcome(versions, parse(t.stdout + t.stderr, t.returncode))


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
