"""What the agent can do. Each tool returns text, capped in length, and every
answer is kept so the conclusion's evidence can be checked against it. All
changes happen in the scratch copy."""

from packaging.version import Version

from .notes import combined
from .search import search
from .session import Session

CAP = 1500


def _cap(text: str) -> str:
    return text if len(text) <= CAP else text[:CAP] + f"\n[... {len(text) - CAP} more characters]"


def _schema(tool: str, description: str, **props) -> dict:
    required = [k for k, v in props.items() if not v.pop("optional", False)]
    return {
        "name": tool,
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
    _schema(
        "release_notes",
        "Release notes for every release after the installed one up to `version` "
        "(default: the newest), newest first.",
        version={"type": "string", "optional": True},
    ),
    _schema(
        "search_code",
        "Lines in the project's Python files, tests included, that use a name as a whole word. "
        "At most 30.",
        name={"type": "string", "description": "e.g. render_table or tablet.render_table"},
    ),
    _schema(
        "read_file",
        "Numbered lines of a project file in the scratch copy.",
        path={"type": "string"},
        start={"type": "integer", "optional": True},
        end={"type": "integer", "optional": True},
    ),
    _schema(
        "try_upgrade",
        "Pin the package to exactly `version` in the scratch copy, install and run the tests. "
        "Code edits made so far stay in place.",
        version={"type": "string"},
    ),
    _schema(
        "edit_file",
        "Replace one exact piece of text in a project file in the scratch copy. `old` must "
        "appear exactly once. Tests and dependency files can't be edited: change the code, "
        "and use try_upgrade for versions.",
        path={"type": "string"},
        old={"type": "string"},
        new={"type": "string"},
    ),
    _schema("show_patch", "Your code edits so far, as a unified diff."),
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

    def tool_release_notes(self, version: str | None = None) -> str:
        releases = self.s.newer(self.package, yanked=True)
        if version:
            releases = [r for r in releases if Version(r.version) <= Version(version)]
        if not releases:
            return "no releases in that range"
        return combined(releases)

    def tool_search_code(self, name: str) -> str:
        hits = search(self.s.sandbox.root, name, limit=30)
        return "\n".join(str(h) for h in hits) or f"{name!r} doesn't appear in the project"

    def tool_read_file(self, path: str, start: int = 1, end: int | None = None) -> str:
        lines = self.s.sandbox.path(path).read_text().splitlines()
        lo = max(1, int(start))
        hi = min(len(lines), int(end) if end else lo + 79)
        return "\n".join(f"{i}: {lines[i - 1]}" for i in range(lo, hi + 1)) or "(empty)"

    def tool_try_upgrade(self, version: str) -> str:
        a = self.s.try_version(self.package, version)
        installed = ", ".join(f"{k} {v}" for k, v in sorted(a.outcome.versions.items()))
        if a.blocked:
            return f"{version} can't be installed: {a.blocked}"
        edits = "with your code edits" if a.patched else "no code edits"
        return f"installed: {installed} ({edits})\n{a.outcome.tests.describe()}"

    def tool_edit_file(self, path: str, old: str, new: str) -> str:
        target = self.s.sandbox.path(path)
        rel = target.relative_to(self.s.sandbox.root).as_posix()
        if rel.startswith("tests/") or "/tests/" in rel or target.name.startswith("test_"):
            raise ValueError("tests can't be edited; make the code pass them")
        if rel in {p.source for p in self.s.pins}:
            raise ValueError(f"{rel} holds the dependencies; use try_upgrade to change versions")
        text = target.read_text()
        n = text.count(old) if old else 0
        if n != 1:
            raise ValueError(f"`old` appears {n} times in {rel}; it must appear exactly once")
        target.write_text(text.replace(old, new, 1))
        return f"edited {rel}"

    def tool_show_patch(self) -> str:
        return self.s.code_patch() or "no code edits yet"
