"""A model that replays fixed replies, so agent tests need no API."""

import json


def call(tool, i=0, **args):
    return {
        "id": f"c{i}",
        "type": "function",
        "function": {"name": tool, "arguments": json.dumps(args)},
    }


class Scripted:
    name = "scripted"

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []  # (messages, tools) per call

    def complete(self, messages, tools):
        self.seen.append((list(messages), tools))
        r = self.replies.pop(0)
        if isinstance(r, str):
            return {"content": r}
        return {"content": "", "tool_calls": r}
