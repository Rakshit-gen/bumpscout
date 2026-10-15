"""The agent: a model that works out an upgrade with tools, then concludes."""

import json
from collections.abc import Callable

from .checks import check
from .llm import Model
from .session import Session
from .tools import SCHEMAS, Tools
from .verdict import VERDICTS, Verdict

SYSTEM = """You check whether a Python project can upgrade one dependency. You work
in a scratch copy of the project; nothing you do touches the real one.

Verdicts:
- safe: the project works on the new version as it is, with no code changes.
- needs-changes: it works after changes to the project's code. Make the changes
  with edit_file, then show they work with try_upgrade.
- blocked: the version can't be installed for this project (Python version,
  another pinned package). Say which newer version does work, if one does.

Passing tests are not proof. Tests may not reach every call site: read the
release notes and search the code for every name they say was removed, renamed
or changed. A name in the notes can also be the project's own, unrelated thing:
read the code before you change it. Skip yanked releases. You can't edit tests or
dependency files.

When you are done, reply with only a JSON object:
{"verdict": "safe" | "needs-changes" | "blocked", "version": "the version judged",
 "fallback": "when blocked, the newest version that works, else empty",
 "files": ["project files that need changes"], "reason": "one or two sentences",
 "evidence": ["exact lines copied from tool answers"]}
"""

# Answers that can't change during a session, so asking twice is a wasted call.
FIXED = {"project_info", "versions", "release_notes"}


def parse_conclusion(text: str, package: str, current: str) -> Verdict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the reply")
    d = json.loads(text[start : end + 1])
    if d.get("verdict") not in VERDICTS:
        raise ValueError(f"verdict must be one of {VERDICTS}")
    if not d.get("version"):
        raise ValueError("version is missing")

    def strings(x):
        return [str(e) for e in x] if isinstance(x, list) else ([str(x)] if x else [])

    return Verdict(
        package,
        current,
        str(d["version"]),
        d["verdict"],
        str(d.get("reason") or ""),
        str(d.get("fallback") or ""),
        strings(d.get("files")),
        strings(d.get("evidence")),
    )


def investigate(
    s: Session,
    package: str,
    model: Model,
    budget: int = 15,
    on_call: Callable[[str, dict], None] | None = None,
) -> Verdict:
    if budget < 1:
        raise ValueError("the budget must allow at least one tool call")
    tools = Tools(s, package)
    pin = s.pin(package)
    current = s.installed(package)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": f"Check upgrading {pin.name}. Start with project_info."},
    ]
    steps: list[str] = []
    seen: set[str] = set()
    fixes = 0
    while True:
        offer = SCHEMAS if len(steps) < budget else []
        if not offer:
            messages.append({"role": "user", "content": "No more tool calls. Conclude now."})
        msg = model.complete(messages, offer)
        calls = msg.get("tool_calls") or []
        messages.append(
            {
                "role": "assistant",
                "content": msg.get("content") or "",
                **({"tool_calls": calls} if calls else {}),
            }
        )
        if calls and offer:
            for c in calls:
                name = c["function"]["name"]
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = None
                key = f"{name}:{json.dumps(args, sort_keys=True)}"
                if args is None:
                    out = "error: arguments were not valid JSON"
                elif name in FIXED and key in seen:
                    out = "already answered above; use that answer"
                else:
                    seen.add(key)
                    steps.append(f"{name}({', '.join(f'{k}={v!r}' for k, v in args.items())})")
                    if on_call:
                        on_call(name, args)
                    out = tools.call(name, args)
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": out})
            continue
        try:
            v = parse_conclusion(msg.get("content") or "", pin.name, current)
        except (ValueError, json.JSONDecodeError) as e:
            if fixes == 1:
                v = Verdict(pin.name, current, current, "unknown", "the model gave no verdict")
                v.notes.append(f"no usable conclusion: {e}")
                v.steps = steps
                return v
            fixes += 1
            messages.append(
                {"role": "user", "content": f"That wasn't valid: {e}. Reply with only the JSON."}
            )
            continue
        v.steps = steps
        return check(v, s, tools.answers)
