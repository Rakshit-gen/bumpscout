"""One upgrade attempt on one project: the scratch copy, the index, the test
results before any change, and every try since."""

from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import Version

from .edit import set_pin
from .env import Outcome, python_of
from .index import Index, Release
from .pins import Pin, find, read_pins
from .resolve import ResolutionError
from .results import TestRun
from .sandbox import Sandbox


@dataclass
class Attempt:
    package: str
    version: str
    outcome: Outcome
    patched: bool  # did the copy have code changes beyond the pin?
    blocked: str = ""  # why it couldn't be installed, if it couldn't


@dataclass
class Session:
    project: Path
    index: Index
    env: object  # has run_tests(Sandbox) -> Outcome
    sandbox: Sandbox = field(init=False)
    before: Outcome = field(init=False)
    attempts: list[Attempt] = field(default_factory=list, init=False)

    def __post_init__(self):
        self.project = Path(self.project)
        self.python = python_of(self.project)
        self.sandbox = Sandbox(self.project)
        self.pins = read_pins(self.project)
        self.before = self.env.run_tests(self.sandbox)

    def close(self) -> None:
        self.sandbox.close()

    def pin(self, package: str) -> Pin:
        return find(self.pins, package)

    def installed(self, package: str) -> str:
        """The version the project gets today."""
        p = self.pin(package)
        if p.name not in self.before.versions:
            raise ValueError(f"{package} isn't installed for Python {self.python}")
        return self.before.versions[p.name]

    def newer(self, package: str, yanked: bool = False) -> list[Release]:
        """Releases after the installed one, oldest first; yanked ones only if asked."""
        now = Version(self.installed(package))
        return [
            r
            for r in self.index.releases(package)
            if Version(r.version) > now and (yanked or not r.yanked)
        ]

    def code_patch(self) -> str:
        """Changes to the copy other than dependency files."""
        sources = {p.source for p in self.pins}
        out, keep = [], True
        for line in self.sandbox.patch().splitlines(keepends=True):
            if line.startswith("--- a/"):
                keep = line[6:].strip() not in sources
            if keep:
                out.append(line)
        return "".join(out)

    def try_version(self, package: str, version: str) -> Attempt:
        """Pin `package` to exactly `version` in the copy and run the tests.
        Code edits already made in the copy stay."""
        p = self.pin(package)
        current = find(read_pins(self.sandbox.root), p.name)
        set_pin(self.sandbox.root, current, f"=={version}")
        try:
            outcome, blocked = self.env.run_tests(self.sandbox), ""
        except ResolutionError as e:
            blocked = str(e)
            outcome = Outcome({}, TestRun(1, f"not installed: {blocked}"))
        a = Attempt(p.name, version, outcome, bool(self.code_patch()), blocked)
        self.attempts.append(a)
        return a
