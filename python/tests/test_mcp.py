import asyncio
import json

import httpx
import pytest

pytest.importorskip("mcp")

import thinkerwave.client as client_module
from thinkerwave import Client
from thinkerwave.mcp_server import build_server
from fake_api import FakeApi, KEY


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retries must not really sleep."""
    monkeypatch.setattr(client_module, "_sleep", lambda s: None)


def call(server, name, args):
    """Call a tool and return its content blocks (mcp 2.x: a CallToolResult with .content)."""
    res = asyncio.run(server.call_tool(name, args))
    return list(res.content)


@pytest.fixture
def server():
    api = FakeApi()
    srv = build_server(lambda: Client(api_key=KEY, base_url="https://api.test/api/v1", transport=api.transport()))
    srv._fake = api
    return srv


def text_of(blocks):
    return "".join(getattr(b, "text", "") for b in blocks)


def test_lists_six_tools(server):
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"start_run", "run_status", "get_answer", "list_files", "read_file", "stop_run"}


def test_start_status_answer(server):
    out = json.loads(text_of(call(server, "start_run", {"problem": "A problem that is long enough to pass.",
                                                         "given": ["1,200 customers"], "max_rounds": 3})))
    assert out["id"].startswith("wr_") and "run_status" in out["next"]
    st = json.loads(text_of(call(server, "run_status", {"id": out["id"]})))
    assert st["status"] == "completed" and st["stop_reason"] == "max_rounds"
    ans = json.loads(text_of(call(server, "get_answer", {"id": out["id"]})))
    assert ans["answer"].startswith("Take") and ans["findings"][0]["evidence"] == "verified"


def test_no_answer_yet_is_a_message_not_a_crash(server):
    rid = json.loads(text_of(call(server, "start_run", {"problem": "A problem that is long enough to pass."})))["id"]
    server._fake.answer_ready = False
    assert "No answer yet" in text_of(call(server, "get_answer", {"id": rid}))


def test_read_file_text_and_image(server):
    rid = json.loads(text_of(call(server, "start_run", {"problem": "A problem that is long enough to pass."})))["id"]
    assert text_of(call(server, "read_file", {"id": rid, "path": "notes.md"})) == "# Hi\n"
    img = call(server, "read_file", {"id": rid, "path": "chart.png"})
    assert any(getattr(b, "type", "") == "image" for b in img)


def _start(server):
    return json.loads(text_of(call(server, "start_run", {"problem": "A problem that is long enough to pass."})))["id"]


def test_list_files_and_stop(server):
    rid = _start(server)
    files = json.loads(text_of(call(server, "list_files", {"id": rid})))
    assert {f["path"] for f in files} == {"chart.png", "notes.md"}
    assert json.loads(text_of(call(server, "stop_run", {"id": rid}))) == {"ok": True}


def test_read_file_too_big_or_unknown_points_to_tw_get(server, monkeypatch):
    import thinkerwave.mcp_server as mod
    rid = _start(server)
    monkeypatch.setattr(mod, "TEXT_LIMIT", 2)
    out = text_of(call(server, "read_file", {"id": rid, "path": "notes.md"}))
    assert "tw get" in out and "notes.md" in out


def test_missing_file_is_a_message(server):
    rid = _start(server)
    assert text_of(call(server, "read_file", {"id": rid, "path": "nope.md"}))


def test_api_errors_become_text_not_exceptions():
    api = FakeApi()
    srv = build_server(lambda: Client(api_key="wrong", base_url="https://api.test/api/v1", transport=api.transport()))
    out = text_of(call(srv, "run_status", {"id": "wr_x"}))
    assert "ThinkerWave error" in out


def _downloads(api):
    return [r.url.path for r in api.requests if "/files/" in r.url.path]


def test_oversize_image_is_refused_before_download(server, monkeypatch):
    import thinkerwave.mcp_server as mod
    rid = _start(server)
    monkeypatch.setattr(mod, "IMAGE_LIMIT", 2)  # chart.png is 3 bytes
    out = call(server, "read_file", {"id": rid, "path": "chart.png"})
    assert not any(getattr(b, "type", "") == "image" for b in out)
    assert f"tw get {rid} chart.png" in text_of(out)
    assert _downloads(server._fake) == []


def test_non_previewable_file_is_never_downloaded(server):
    rid = _start(server)
    out = text_of(call(server, "read_file", {"id": rid, "path": "model.xlsx"}))
    assert f"tw get {rid} model.xlsx" in out
    assert _downloads(server._fake) == []


def test_unknown_path_is_not_downloaded(server):
    rid = _start(server)
    assert "No file nope.md" in text_of(call(server, "read_file", {"id": rid, "path": "nope.md"}))
    assert _downloads(server._fake) == []


def test_missing_size_still_enforces_cap_on_received_bytes(monkeypatch):
    import thinkerwave.mcp_server as mod
    api = FakeApi()
    real = api.handle

    def no_sizes(req):
        res = real(req)
        if req.url.path.endswith("/files") and res.status_code == 200:
            return httpx.Response(200, json=[{k: v for k, v in f.items() if k != "size"} for f in res.json()])
        return res

    srv = build_server(lambda: Client(api_key=KEY, base_url="https://api.test/api/v1",
                                      transport=httpx.MockTransport(no_sizes)))
    rid = _start(srv)
    monkeypatch.setattr(mod, "IMAGE_LIMIT", 2)
    out = call(srv, "read_file", {"id": rid, "path": "chart.png"})
    assert f"tw get {rid} chart.png" in text_of(out)
    assert not any(getattr(b, "type", "") == "image" for b in out)


def test_transport_failure_is_a_message_for_every_tool():
    def boom(req):
        raise httpx.ConnectError("down", request=req)

    srv = build_server(lambda: Client(api_key=KEY, base_url="https://api.test/api/v1",
                                      transport=httpx.MockTransport(boom)))
    calls = {"start_run": {"problem": "A problem that is long enough to pass."}, "run_status": {"id": "wr_x"},
             "get_answer": {"id": "wr_x"}, "list_files": {"id": "wr_x"},
             "read_file": {"id": "wr_x", "path": "notes.md"}, "stop_run": {"id": "wr_x"}}
    for name, args in calls.items():
        assert "unreachable" in text_of(call(srv, name, args)), name


def test_publishes_instructions_for_the_assistant(server):
    # MCP clients put these ahead of the tool list; directories (e.g. Glama) show them.
    text = server.instructions or ""
    assert "start_run" in text and "run_status" in text
    assert "minutes" in text
    assert "verified" in text and "assumption" in text and "guess" in text
