"""Run the real agent loop and checks on one scenario with a scripted model.

The model's replies are fixed (no API key needed). The tools, the tests and
the checks are real. In this scenario the tests pass on the new version, so
the rules call it safe; the scripted model reads the notes, finds the call
site no test reaches and fixes it. One evidence line in its conclusion was
never returned by a tool, so the checks drop it.

    uv run python examples/scripted_run.py
"""

import json

from bumpscout import scenarios
from bumpscout.agent import investigate
from bumpscout.report import markdown


def call(i, tool, **args):
    return {
        "id": f"c{i}",
        "type": "function",
        "function": {"name": tool, "arguments": json.dumps(args)},
    }


class ScriptedModel:
    name = "a scripted model"

    def __init__(self, replies):
        self.replies = replies

    def complete(self, messages, tools):
        r = self.replies.pop(0)
        return {"content": r} if isinstance(r, str) else {"content": "", "tool_calls": r}


CONCLUSION = {
    "verdict": "needs-changes",
    "version": "2.0.0",
    "files": ["src/app/alerts.py"],
    "reason": "send_mail is renamed to send_email in 2.0. The tests pass anyway because "
    "nothing calls page(), which still uses the old name.",
    "evidence": [
        "- `send_mail` is renamed to `send_email`.",
        'src/app/alerts.py:12: notifykit.send_mail(ONCALL, subject("critical", text))',
        "page() is called from the alerting cron job",
    ],
}

model = ScriptedModel(
    [
        [call(0, "project_info")],
        [call(1, "try_upgrade", version="2.0.0"), call(2, "release_notes")],
        [call(3, "search_code", name="send_mail")],
        [
            call(
                4,
                "edit_file",
                path="src/app/alerts.py",
                old="notifykit.send_mail(",
                new="notifykit.send_email(",
            )
        ],
        [call(5, "try_upgrade", version="2.0.0")],
        json.dumps(CONCLUSION),
    ]
)
sc = scenarios.load("untested-call-site")
s = sc.session()
try:
    v = investigate(s, sc.package, model)
finally:
    s.close()
print(markdown(v, verbose=True), end="")
