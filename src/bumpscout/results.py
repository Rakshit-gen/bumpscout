"""Reading a test run's output: unittest (used by the scenarios) and pytest."""

import re
from dataclasses import dataclass, field

SEP = "=" * 70
UNITTEST_HEAD = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)")
UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in")
PYTEST_LINE = re.compile(r"^(FAILED|ERROR) (?!\()(\S+)(?: - (.*))?$")  # not "FAILED (errors=1)"
PYTEST_COUNTS = re.compile(r"(\d+) (passed|failed|errors?)\b")
PYTEST_SECTION = re.compile(r"^_{3,} (.+?) _{3,}$")


@dataclass
class TestRun:
    exit_code: int
    output: str
    ran: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)  # (test, message)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    def describe(self, limit: int = 8) -> str:
        if self.ok:
            return f"tests passed ({self.ran} ran)"
        head = f"tests failed: {len(self.failures)} of {self.ran} ran, exit code {self.exit_code}"
        lines = [head] + [f"  {t}: {m}" for t, m in self.failures[:limit]]
        if not self.failures:
            tail = [x for x in self.output.strip().splitlines() if x.strip()][-6:]
            lines += ["  last lines of output:"] + [f"    {x}" for x in tail]
        return "\n".join(lines)


def parse(output: str, exit_code: int) -> TestRun:
    run = TestRun(exit_code, output)
    lines = output.splitlines()
    for i, line in enumerate(lines):
        if m := UNITTEST_HEAD.match(line):
            message = ""
            for nxt in lines[i + 2 :]:
                if nxt.startswith(("=" * 20, "-" * 20)):
                    break
                if nxt.strip():
                    message = nxt.strip()
            test = m.group(3).split(".")
            run.failures.append((".".join(test[-2:]) if len(test) > 1 else m.group(2), message))
        elif m := UNITTEST_RAN.match(line):
            run.ran = int(m.group(1))
        elif m := PYTEST_LINE.match(line):
            run.failures.append((m.group(2), (m.group(3) or "").strip()))
    _fill_pytest_messages(run, lines)
    if not run.ran:
        counts = {k.rstrip("s"): int(n) for n, k in PYTEST_COUNTS.findall(output)}
        run.ran = counts.get("passed", 0) + counts.get("failed", 0)
    return run


def _fill_pytest_messages(run: TestRun, lines: list[str]) -> None:
    """pytest's summary line has no message for collection errors (and with
    some options, none at all); take the last `E   ` line of the matching
    section instead."""
    sections: dict[str, str] = {}
    title = None
    for line in lines:
        if m := PYTEST_SECTION.match(line):
            title = m.group(1)
        elif title and line.startswith("E   "):
            sections[title] = line[4:].strip()
    for i, (test, message) in enumerate(run.failures):
        if message:
            continue
        tail = test.split("::")[-1]
        for title, last in sections.items():
            if title.endswith(tail) or title.endswith(test):
                run.failures[i] = (test, last)
                break
