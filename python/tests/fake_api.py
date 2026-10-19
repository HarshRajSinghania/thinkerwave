"""An in-memory fake of the public API v1 (docs/api.md), for offline tests."""

from __future__ import annotations  # lazy annotations

import json
from collections.abc import Iterator
from typing import Optional, Union

import httpx

KEY = "tw_live_" + "k" * 32
ANSWER = {"round": 2, "score": 6.0, "final": True, "answer": "Take the 8% increase now.",
          "confidence": "medium", "text": "Prose.",
          "findings": [{"text": "At 3.1% churn +15% adds revenue", "evidence": "verified", "flagged": False},
                       {"text": "Churn reacts 1.5x", "evidence": "assumption", "flagged": False}]}
EVENTS = [
    ("run.started", {"max_rounds": 2}), ("round.started", {"round": 1}),
    ("round.step", {"round": 1, "step": "work"}), ("round.tool", {"round": 1, "kind": "python", "ok": True}),
    ("round.finished", {"round": 1, "score": 4.0, "change": "refined", "best_so_far": True}),
    ("round.started", {"round": 2}),
    ("round.finished", {"round": 2, "score": 6.0, "change": "rethought", "best_so_far": True}),
    ("future.event", {"x": 1}),
    ("run.finished", {"status": "completed", "stop_reason": "max_rounds", "best_score": 6.0}),
]


def _broken(chunks: list[str]) -> Iterator[bytes]:
    yield "".join(chunks).encode()
    raise httpx.ReadError("connection reset")


def err(status: int, code: str, message: str = "m", headers: Optional[dict] = None) -> httpx.Response:
    return httpx.Response(status, json={"error": {"code": code, "message": message}}, headers=headers or {})


class FakeApi:
    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}
        self.fail_next: list[Union[int, tuple[int, str]]] = []  # status, or (status, error code)
        self.raw_next: list[httpx.Response] = []  # verbatim responses to return first (proxies, redirects)
        self.drop_stream_after: Optional[int] = None  # end the stream cleanly after this event id, once
        self.error_stream_after: Optional[int] = None  # raise a transport error after this event id, once
        self.empty_stream = False  # every events request returns 200 with no events
        self.requests: list[httpx.Request] = []
        self.answer_ready = True
        self.transport_errors = 0  # the next N requests fail with a connection error
        self.me_extra: dict = {}  # extra /me fields (e.g. credit_remaining_usd for a paid plan)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def handle(self, req: httpx.Request) -> httpx.Response:
        self.requests.append(req)
        if self.transport_errors:
            self.transport_errors -= 1
            raise httpx.ConnectError("connection refused", request=req)
        if req.headers.get("authorization") != f"Bearer {KEY}":
            return err(401, "invalid_key", "The API key is missing, invalid or revoked.")
        if self.raw_next:
            return self.raw_next.pop(0)
        if self.fail_next:
            item = self.fail_next.pop(0)
            status, code = item if isinstance(item, tuple) else (item, "rate_limited" if item == 429 else "unavailable")
            return err(status, code, headers={"Retry-After": "0"})
        p, m = req.url.path.removeprefix("/api/v1"), req.method
        if p == "/me":
            return httpx.Response(200, json={"email": "a@b.c", "plan": "trial", "runs_today": 0,
                                             "runs_per_day": 5, "concurrent_runs": 1, "max_rounds": 10,
                                             **self.me_extra})
        if p == "/runs" and m == "POST":
            body = json.loads(req.content)
            if len(body.get("problem", "")) < 20:
                return err(422, "invalid_request", "Invalid field: problem.")
            rid = f"wr_{len(self.runs) + 1:04d}"
            self.runs[rid] = {"id": rid, "status": "completed", "problem": body["problem"], "round": 2,
                              "max_rounds": body.get("max_rounds") or 10, "best_score": 6.0,
                              "started_at": "2026-10-14T10:00:00", "completed_at": "2026-10-14T10:05:00",
                              "elapsed_seconds": 300.0, "stop_reason": "max_rounds", "error": None,
                              "_body": body}
            return httpx.Response(201, json={"id": rid, "status": "running", "queue_position": None})
        if p == "/runs" and m == "GET":
            return httpx.Response(200, json=[{"id": r["id"], "problem_preview": r["problem"][:140], "status": r["status"],
                                              "best_score": 6.0, "rounds_done": 2, "created_at": "2026-10-14T10:00:00",
                                              "elapsed_seconds": 300.0} for r in self.runs.values()])
        parts = p.strip("/").split("/")
        if len(parts) < 2 or parts[0] != "runs" or parts[1] not in self.runs:
            return err(404, "not_found", "Not found.")
        run, rest = self.runs[parts[1]], parts[2:]
        if not rest:
            return httpx.Response(200, json={k: v for k, v in run.items() if not k.startswith("_")})
        if rest == ["stop"]:
            return httpx.Response(200, json={"ok": True})
        if rest == ["answer"]:
            return httpx.Response(200, json=ANSWER) if self.answer_ready else err(404, "not_found", "No answer yet.")
        if rest == ["rounds"]:
            return httpx.Response(200, json=[
                {"round": 1, "score": 4.0, "change": "refined", "answer": None,
                 "tools": {"python": 1, "web_search": 0, "pages_read": 0}},
                {"round": 2, "score": 6.0, "change": "rethought",
                 "answer": {k: ANSWER[k] for k in ("answer", "confidence", "findings", "text")},
                 "tools": {"python": 2, "web_search": 1, "pages_read": 1}}])
        if rest == ["files"]:
            return httpx.Response(200, json=[{"path": "chart.png", "size": 3, "type": "image/png", "kind": "image"},
                                             {"path": "notes.md", "size": 5, "type": "text/markdown", "kind": "text"}])
        if rest[0] == "files":
            path = "/".join(rest[1:])
            body = {"chart.png": b"PNG", "notes.md": b"# Hi\n", "out/a #1?b%.csv": b"x,y\n"}.get(path)
            return httpx.Response(200, content=body) if body is not None else err(404, "not_found")
        if rest == ["events"]:
            after = int(req.headers.get("last-event-id") or 0)
            chunks = []
            fail_at, self.error_stream_after = self.error_stream_after, None
            for i, (name, data) in enumerate(EVENTS, start=1):
                if i <= after or self.empty_stream:
                    continue
                if fail_at is not None and i > fail_at:
                    return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                          content=_broken(chunks))
                if self.drop_stream_after is not None and i > self.drop_stream_after:
                    self.drop_stream_after = None
                    break
                chunks.append(f"id: {i}\nevent: {name}\ndata: {json.dumps(data)}\n\n")
                if i == 3:
                    chunks.append(": keepalive\n\n")
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  content="".join(chunks).encode())
        return err(404, "not_found")
