"""Writing a verdict out for a person."""

from .verdict import Verdict

HEADLINE = {
    "safe": "safe to upgrade",
    "needs-changes": "upgrade needs code changes",
    "blocked": "can't upgrade",
    "unknown": "no verdict",
}


def code(text: str) -> str:
    """An inline code span that survives backticks inside the text."""
    return f"`` {text} ``" if "`" in text else f"`{text}`"


def markdown(v: Verdict, verbose: bool = False) -> str:
    out = [f"# {v.package} {v.current} to {v.version}: {HEADLINE[v.verdict]}", ""]
    if v.reason:
        out += [v.reason, ""]
    if v.verdict == "blocked":
        if v.fallback:
            out += [f"Newest version that works: {v.fallback}.", ""]
        else:
            out += ["No newer version works.", ""]
    if v.new_spec:
        out += [f"Requirement: `{v.new_spec}`", ""]
    if v.files:
        out += ["## Files to change", ""] + [f"- {f}" for f in v.files] + [""]
    if v.patch:
        out += ["## Patch", "", "```diff", v.patch.rstrip("\n"), "```", ""]
    if v.evidence:
        out += ["## Evidence", ""] + [f"- {code(e)}" for e in v.evidence] + [""]
    if v.notes:
        out += ["## Notes", ""] + [f"- {n}" for n in v.notes] + [""]
    if verbose and v.steps:
        out += [f"## How it got there ({len(v.steps)} steps)", ""]
        out += [f"{i}. {s}" for i, s in enumerate(v.steps, 1)] + [""]
    return "\n".join(out).rstrip("\n") + "\n"
