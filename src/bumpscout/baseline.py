"""The rules-only check, no model: try the newest release; if the tests pass
call it safe; if they fail, look for names the notes say went away and point
at the files that use them. It is the bar the agent has to beat."""

from .edit import proposed_spec, requirement_text
from .notes import changed_names, combined
from .search import search
from .session import Session
from .verdict import Verdict


def check(session: Session, package: str) -> Verdict:
    pin = session.pin(package)
    current = session.installed(package)
    newer = session.newer(package)
    if not newer:
        return Verdict(pin.name, current, current, "safe", f"{current} is the newest release")

    def verdict(version, kind, reason, **kw):
        spec = requirement_text(pin, proposed_spec(pin.spec, version))
        steps = [
            f"try {a.version}: {a.blocked or a.outcome.tests.describe().splitlines()[0]}"
            for a in session.attempts
        ]
        return Verdict(pin.name, current, version, kind, reason, new_spec=spec, steps=steps, **kw)

    latest = newer[-1].version
    a = session.try_version(package, latest)
    if a.blocked:
        for r in reversed(newer[:-1]):
            b = session.try_version(package, r.version)
            if not b.blocked and b.outcome.tests.ok:
                return verdict(
                    latest, "blocked", a.blocked, fallback=r.version, evidence=[a.blocked]
                )
        return verdict(latest, "blocked", a.blocked, evidence=[a.blocked])
    if a.outcome.tests.ok:
        return verdict(latest, "safe", f"the tests pass on {latest}")

    names = changed_names(combined(newer))
    hits = [h for n in names for h in search(session.sandbox.root, n) if not h.in_tests]
    files = sorted({h.path for h in hits})
    failing = [f"{t}: {m}" for t, m in a.outcome.tests.failures[:3]]
    reason = f"the tests fail on {latest}"
    if names:
        reason += f"; the notes change {', '.join(names)}"
    return verdict(
        latest, "needs-changes", reason, files=files, evidence=failing + [str(h) for h in hits[:5]]
    )
