"""Scoring a check against a scenario's known answer."""

from collections.abc import Callable
from dataclasses import dataclass

from . import scenarios
from .session import Session
from .verdict import Verdict

Checker = Callable[[Session, str], Verdict]


@dataclass
class Score:
    name: str
    verdict: bool  # right call
    version: bool  # about the right version (and the right fallback when blocked)
    files: bool  # the files that need changes, no more, no fewer
    harmful: bool  # called it safe when it isn't
    result: Verdict | None = None

    @property
    def solved(self) -> bool:
        return self.verdict and self.version and self.files


def score(answer: dict, v: Verdict, name: str = "") -> Score:
    version = v.version == answer["version"]
    if answer["verdict"] == "blocked":
        version = version and v.fallback == answer.get("fallback", "")
    return Score(
        name,
        v.verdict == answer["verdict"],
        version,
        set(v.files) == set(answer.get("files", [])),
        v.verdict == "safe" and answer["verdict"] != "safe",
        v,
    )


def run(checker: Checker, names: list[str] | None = None) -> list[Score]:
    out = []
    for name in names or scenarios.names():
        sc = scenarios.load(name)
        s = sc.session()
        try:
            out.append(score(sc.answer, checker(s, sc.package), name))
        finally:
            s.close()
    return out


def table(scores: list[Score]) -> str:
    mark = {True: "yes", False: "-"}
    w = max([len("scenario")] + [len(s.name) for s in scores])
    lines = [f"{'scenario':<{w}}  verdict  version  files  harmful"]
    for s in scores:
        lines.append(
            f"{s.name:<{w}}  {mark[s.verdict]:<7}  {mark[s.version]:<7}  {mark[s.files]:<5}"
            f"  {'YES' if s.harmful else '-'}"
        )
    solved = sum(s.solved for s in scores)
    harmful = sum(s.harmful for s in scores)
    lines.append(f"solved {solved}/{len(scores)}, harmful {harmful}")
    return "\n".join(lines)
