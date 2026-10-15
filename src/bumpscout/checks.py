"""Checks on the agent's verdict before anyone acts on it. The tests are run
once more here, at the claimed version with the copy as the agent left it,
rather than trusting the transcript.

- Evidence lines have to appear in something a tool returned; others are
  dropped.
- blocked: the version must fail to install. A fallback must install and pass.
- safe: the tests must pass with no code edits. Edits make it needs-changes,
  failing tests make it needs-changes with no patch.
- needs-changes: the patch is whatever the copy holds, and only counts if the
  tests pass with it. The files are the ones the patch touches.
"""

import re

from .edit import proposed_spec, requirement_text
from .session import Session
from .verdict import Verdict


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def patched_files(patch: str) -> list[str]:
    return sorted({line[6:].strip() for line in patch.splitlines() if line.startswith("--- a/")})


def check(v: Verdict, s: Session, answers: list[str]) -> Verdict:
    seen = _norm("\n".join(answers))
    kept = []
    for e in v.evidence:
        if _norm(e) and _norm(e) in seen:
            kept.append(e)
        else:
            v.notes.append(f"evidence not found in any tool answer: {e!r}")
    v.evidence = kept

    a = s.try_version(v.package, v.version)
    v.steps.append(f"check: try {v.version}")
    if a.blocked:
        if v.verdict != "blocked":
            v.notes.append(f"{v.version} can't be installed, so it's blocked, not {v.verdict}")
            v.verdict = "blocked"
    elif v.verdict == "blocked":
        v.notes.append(f"{v.version} installs fine, so it isn't blocked")
        v.verdict, v.fallback = "safe", ""

    if v.verdict == "blocked":
        v.patch, v.files = "", []
        if v.fallback:
            b = s.try_version(v.package, v.fallback)
            v.steps.append(f"check: try {v.fallback}")
            if b.blocked or not b.outcome.tests.ok:
                v.notes.append(f"the fallback {v.fallback} doesn't work either; dropped it")
                v.fallback = ""
    else:
        v.fallback = ""
        patch = s.code_patch()
        if not a.outcome.tests.ok:
            first = a.outcome.tests.describe().splitlines()[0]
            v.notes.append(f"with the copy as left, {first} on {v.version}")
            if v.verdict == "safe":
                v.verdict = "needs-changes"
            v.patch = ""
        elif patch:
            if v.verdict == "safe":
                v.notes.append("called safe, but the tests only pass with code edits")
                v.verdict = "needs-changes"
            v.patch = patch
            if sorted(v.files) != patched_files(patch):
                if v.files:
                    v.notes.append(f"files named {v.files}, but the patch touches others")
                v.files = patched_files(patch)
        elif v.verdict == "needs-changes":
            v.notes.append("the tests pass, but no patch was made to go with needs-changes")

    target = v.fallback if v.verdict == "blocked" else v.version
    if target:
        pin = s.pin(v.package)
        v.new_spec = requirement_text(pin, proposed_spec(pin.spec, target))
    return v
