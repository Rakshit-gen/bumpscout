import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from bumpscout.llm import ChatAPI


def fake_api(replies):
    """A local server that answers with (status, body) pairs in order."""
    seen = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            status, body = replies.pop(0)
            data = json.dumps(body).encode()
            self.send_response(status)
            if status == 429:
                self.send_header("retry-after", "0")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1/chat/completions", seen


OK = {"choices": [{"message": {"content": "hi"}}], "usage": {"prompt_tokens": 5}}


def test_retries_rate_limits_and_counts_usage():
    srv, url, seen = fake_api([(429, {"error": "slow down"}), (200, OK)])
    api = ChatAPI("m", url, key="k")
    assert api.complete([{"role": "user", "content": "x"}], [{"name": "t"}]) == {"content": "hi"}
    assert len(seen) == 2 and seen[1]["tools"][0] == {"type": "function", "function": {"name": "t"}}
    assert api.usage == {"prompt_tokens": 5, "completion_tokens": 0, "calls": 1}
    srv.shutdown()


def test_client_errors_are_not_retried():
    srv, url, seen = fake_api([(400, {"error": "bad"})])
    with pytest.raises(RuntimeError, match="returned 400"):
        ChatAPI("m", url, key="k").complete([], [])
    assert len(seen) == 1
    srv.shutdown()


def test_needs_a_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        ChatAPI()
