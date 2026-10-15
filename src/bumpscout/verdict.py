"""What bumpscout concludes about one upgrade."""

from dataclasses import asdict, dataclass, field

VERDICTS = ("safe", "needs-changes", "blocked")


@dataclass
class Verdict:
    package: str
    current: str  # the version installed today
    version: str  # the version the verdict is about
    verdict: str  # one of VERDICTS
    reason: str = ""
    fallback: str = ""  # when blocked: the newest version that does work, if any
    files: list[str] = field(default_factory=list)  # project files that need changes
    evidence: list[str] = field(default_factory=list)  # quoted lines that back the reason
    patch: str = ""  # code changes that made the tests pass, when needs-changes
    new_spec: str = ""  # the requirement to write, e.g. "tablet>=2.0.1,<3"
    notes: list[str] = field(default_factory=list)  # what the checks changed or doubt
    steps: list[str] = field(default_factory=list)  # how it got there

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {', '.join(VERDICTS)}, not {self.verdict!r}")

    def to_dict(self) -> dict:
        return asdict(self)
