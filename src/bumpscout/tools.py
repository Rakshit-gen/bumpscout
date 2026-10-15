"""What the agent can do. Each tool returns text, capped in length, and every
answer is kept so the conclusion's evidence can be checked against it. All
changes happen in the scratch copy."""

from .session import Session

CAP = 1500


def _cap(text: str) -> str:
    return text if len(text) <= CAP else text[:CAP] + f"\n[... {len(text) - CAP} more characters]"


def _schema(name: str, description: str, **props) -> dict:
    required = [k for k, v in props.items() if not v.pop("optional", False)]
    return {
        "name": name,
        "description": description,
        "parameters": {"type": "object", "properties": props, "required": required},
    }


SCHEMAS = [
    _schema(
        "project_info",
        "The project's Python version, its direct dependencies, the installed version of the "
        "package being upgraded, and how its tests do today. Start here.",
    ),
    _schema(
        "versions",
        "Releases of the package newer than the installed one, with the Python they need, "
        "what they depend on and whether they were yanked.",
    ),
]


class Tools:
    def __init__(self, session: Session, package: str):
        self.s = session
        self.package = package
        self.answers: list[str] = []

    def call(self, name: str, args: dict) -> str:
        fn = getattr(self, "tool_" + name, None)
        if fn is None:
            out = f"error: no tool named {name!r}"
        else:
            try:
                out = _cap(fn(**args))
            except (TypeError, ValueError, OSError) as e:
                out = f"error: {e}"
        self.answers.append(out)
        return out

    def tool_project_info(self) -> str:
        s = self.s
        out = [f"python: {s.python}", "dependencies:"]
        out += [f"  {p.text}  ({p.source})" for p in s.pins]
        out.append(f"upgrading: {self.package}, installed {s.installed(self.package)}")
        out.append(f"tests today: {s.before.tests.describe()}")
        return "\n".join(out)

    def tool_versions(self) -> str:
        rows = []
        for r in self.s.newer(self.package, yanked=True):
            bits = [r.version]
            if r.requires_python:
                bits.append(f"python {r.requires_python}")
            if r.requires:
                bits.append("needs " + ", ".join(r.requires))
            if r.yanked:
                bits.append("YANKED")
            rows.append("  ".join(bits))
        return "\n".join(rows) or "no newer releases"
