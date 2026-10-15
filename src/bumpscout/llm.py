"""A chat client for OpenAI-compatible APIs (Groq by default), stdlib only."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Protocol

DEFAULT_MODEL = "openai/gpt-oss-120b"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class Model(Protocol):
    name: str

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        """Return the assistant message: {"content": ..., "tool_calls": [...]}"""


class ChatAPI:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        url: str = GROQ_URL,
        key: str | None = None,
        retries: int = 4,
        timeout: float = 60.0,
    ):
        self.name = model
        self.url = url
        self.key = key if key is not None else os.environ.get("GROQ_API_KEY", "")
        if not self.key:
            raise ValueError("set GROQ_API_KEY to use a model, or leave --model out for rules")
        self.retries, self.timeout = retries, timeout
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}

    def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        body = {"model": self.name, "messages": messages, "temperature": 0}
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
        data = json.dumps(body).encode()
        for attempt in range(self.retries + 1):
            req = urllib.request.Request(
                self.url,
                data,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "User-Agent": "bumpscout",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    out = json.loads(r.read())
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:300]
                if e.code not in (429, 500, 502, 503) or attempt == self.retries:
                    raise RuntimeError(f"model API returned {e.code}: {detail}") from None
                wait = float(e.headers.get("retry-after") or 2**attempt)
                time.sleep(min(wait, 30))
        usage = out.get("usage") or {}
        self.usage["calls"] += 1
        for k in ("prompt_tokens", "completion_tokens"):
            self.usage[k] += usage.get(k, 0)
        return out["choices"][0]["message"]
