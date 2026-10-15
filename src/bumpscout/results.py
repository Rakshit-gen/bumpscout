"""Reading a test run's output: unittest (used by the scenarios) and pytest."""

import re
from dataclasses import dataclass, field

SEP = "=" * 70
UNITTEST_HEAD = re.compile(r"^(FAIL|ERROR): (\S+) \(([^)]+)\)")
UNITTEST_RAN = re.compile(r"^Ran (\d+) tests? in")
PYTEST_LINE = re.compile(r"^(FAILED|ERROR) (\S+)(?: - (.*))?$")
PYTEST_COUNTS = re.compile(r"(\d+) (passed|failed|errors?)\b")


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
    if not run.ran:
        counts = {k.rstrip("s"): int(n) for n, k in PYTEST_COUNTS.findall(output)}
        run.ran = counts.get("passed", 0) + counts.get("failed", 0)
    return run
