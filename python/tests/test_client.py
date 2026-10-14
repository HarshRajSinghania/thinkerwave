import httpx
import pytest

import thinkerwave.client as client_module
from thinkerwave import (Client, InvalidKeyError, NotFoundError, InvalidRequestError, RateLimitedError,
                         RoundFinished, RunFinished, RunLimitError, ThinkerWaveError, UnavailableError)
from fake_api import FakeApi, KEY


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    """Record backoff sleeps instead of waiting."""
    recorded = []
    monkeypatch.setattr(client_module, "_sleep", recorded.append)
    return recorded


@pytest.fixture
def api():
    return FakeApi()


@pytest.fixture
def tw(api):
    return Client(api_key=KEY, base_url="https://api.test/api/v1", transport=api.transport())


def test_key_from_env(monkeypatch, api):
    monkeypatch.setenv("THINKERWAVE_API_KEY", KEY)
    assert Client(base_url="https://api.test/api/v1", transport=api.transport()).me().email == "a@b.c"


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("THINKERWAVE_API_KEY", raising=False)
    with pytest.raises(InvalidKeyError, match="THINKERWAVE_API_KEY"):
        Client()


def test_bad_key(api):
    c = Client(api_key="tw_live_" + "x" * 32, base_url="https://api.test/api/v1", transport=api.transport())
    with pytest.raises(InvalidKeyError) as e:
        c.me()
    assert e.value.status == 401 and e.value.code == "invalid_key"


def test_create_sends_only_public_fields(tw, api):
    run = tw.runs.create("Should we raise prices 15% or hold? Long enough.", given=["1,200 customers"],
                         standards=["Show break-even"], max_rounds=6)
    assert run.id.startswith("wr_") and run.status == "running"
    sent = api.runs[run.id]["_body"]
    assert sent == {"problem": "Should we raise prices 15% or hold? Long enough.", "given": ["1,200 customers"],
                    "standards": ["Show break-even"], "max_rounds": 6}


def test_validation_error(tw):
    with pytest.raises(InvalidRequestError, match="problem"):
        tw.runs.create("short")


def test_get_answer_rounds_files(tw):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    assert tw.runs.get(rid).stop_reason == "max_rounds"
    a = tw.runs.answer(rid)
    assert a.answer.startswith("Take") and [f.evidence for f in a.findings] == ["verified", "assumption"]
    rs = tw.runs.rounds(rid)
    assert rs[0].answer is None and rs[1].tools.web_search == 1
    assert [f.kind for f in tw.runs.files(rid)] == ["image", "text"]
    assert tw.runs.read(rid, "notes.md") == b"# Hi\n"
    assert [r.id for r in tw.runs.list()] == [rid]


def test_no_answer_yet(tw, api):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    api.answer_ready = False
    with pytest.raises(NotFoundError, match="No answer yet"):
        tw.runs.answer(rid)


def test_download(tw, tmp_path):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    out = tw.runs.download(rid, "chart.png", to=tmp_path)
    assert out == tmp_path / "chart.png" and out.read_bytes() == b"PNG"


def test_download_refuses_path_escape(tw, tmp_path):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    with pytest.raises(ValueError):
        tw.runs.download(rid, "../../etc/passwd", to=tmp_path)


def test_download_refuses_absolute_path(tw, tmp_path):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    with pytest.raises(ValueError):
        tw.runs.download(rid, "/etc/passwd", to=tmp_path)


def test_download_refuses_symlink_escape(tw, tmp_path):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    outside = tmp_path / "outside"
    outside.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "link").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        tw.runs.download(rid, "link/chart.png", to=target)
    assert not (outside / "chart.png").exists()


def test_retries_429_then_succeeds(tw, api):
    api.fail_next = [429, 503]
    assert tw.me().plan == "trial"


def test_gives_up_after_three_retries(tw, api):
    api.fail_next = [429, 429, 429, 429]
    with pytest.raises(RateLimitedError):
        tw.me()
    assert len(api.requests) == 4


def test_run_limit_is_not_retried(tw, api):
    api.fail_next = [(429, "run_limit")]
    with pytest.raises(RunLimitError):
        tw.me()
    assert len(api.requests) == 1


def test_500_is_not_retried(tw, api):
    api.fail_next = [500]
    with pytest.raises(ThinkerWaveError):
        tw.me()
    assert len(api.requests) == 1


def test_create_is_not_retried_on_5xx(tw, api):
    api.fail_next = [503]
    with pytest.raises(UnavailableError):
        tw.runs.create("A problem that is long enough to pass.")
    assert len(api.requests) == 1 and not api.runs


def test_create_is_retried_on_429(tw, api):
    api.fail_next = [429]
    assert tw.runs.create("A problem that is long enough to pass.").id.startswith("wr_")
    assert len(api.requests) == 2


def test_retry_after_is_honoured(tw, api, sleeps):
    api.fail_next = [429]
    tw.me()
    assert sleeps == [0.0]


def test_events_typed_unknown_skipped_and_resume(tw, api):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    api.drop_stream_after = 4
    evs = list(tw.runs.events(rid))
    ids = [e.id for e in evs]
    assert ids == sorted(set(ids)), "no duplicates across the reconnect"
    assert isinstance(evs[-1], RunFinished) and evs[-1].stop_reason == "max_rounds"
    assert any(isinstance(e, RoundFinished) and e.round == 2 and e.change == "rethought" for e in evs)
    resumed = [r for r in api.requests if r.url.path.endswith("/events")]
    assert len(resumed) == 2 and resumed[1].headers["last-event-id"] == "4"


def test_events_resume_after_transport_error(tw, api):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    api.error_stream_after = 4
    evs = list(tw.runs.events(rid))
    ids = [e.id for e in evs]
    assert ids == sorted(set(ids)), "no duplicates across the reconnect"
    assert isinstance(evs[-1], RunFinished)
    reqs = [r for r in api.requests if r.url.path.endswith("/events")]
    assert len(reqs) == 2 and reqs[1].headers["last-event-id"] == "4"


def test_events_retries_503_on_connect_then_streams(tw, api, sleeps):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    api.fail_next = [503]
    assert isinstance(list(tw.runs.events(rid))[-1], RunFinished)
    assert sleeps == [0.0]


def test_events_stream_lost_after_bounded_attempts(tw, api, sleeps):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    api.empty_stream = True
    with pytest.raises(ThinkerWaveError) as e:
        list(tw.runs.events(rid, max_reconnects=2))
    assert e.value.code == "stream_lost"
    assert len([r for r in api.requests if r.url.path.endswith("/events")]) == 3
    assert sleeps == [0.5, 1.0]


def test_events_budget_resets_after_progress(tw, api):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    # Each drop is followed by a connection that delivers new events, so one reconnect allowed is enough.
    api.drop_stream_after = 2
    assert isinstance(list(tw.runs.events(rid, max_reconnects=1))[-1], RunFinished)


def test_events_api_error_not_retryable_raises(tw, api):
    with pytest.raises(NotFoundError):
        list(tw.runs.events("wr_missing"))


def test_run_id_and_file_path_are_url_quoted(tw, api, tmp_path):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    assert tw.runs.read(rid, "out/a #1?b%.csv") == b"x,y\n"
    req = api.requests[-1]
    assert req.url.raw_path == f"/api/v1/runs/{rid}/files/out/a%20%231%3Fb%25.csv".encode()
    assert req.url.query == b""
    assert tw.runs.download(rid, "out/a #1?b%.csv", to=tmp_path).read_bytes() == b"x,y\n"
    with pytest.raises(NotFoundError):
        tw.runs.get("wr_1/../me?x=#y")
    assert api.requests[-1].url.raw_path == b"/api/v1/runs/wr_1%2F..%2Fme%3Fx%3D%23y"


def test_transport_error_on_get_is_retried_then_unavailable(tw, api, sleeps):
    api.transport_errors = 2
    assert tw.me().plan == "trial"
    assert len(api.requests) == 3 and sleeps == [0.5, 1.0]
    api.requests.clear()
    api.transport_errors = 10
    with pytest.raises(UnavailableError) as e:
        tw.me()
    assert e.value.code == "unavailable"
    assert e.value.message == "ThinkerWave is unreachable right now — try again in a moment."
    assert len(api.requests) == 4


def test_transport_error_on_create_is_not_retried(tw, api):
    api.transport_errors = 1
    with pytest.raises(UnavailableError):
        tw.runs.create("A problem that is long enough to pass.")
    assert len(api.requests) == 1


def test_events_continue_past_run_error_to_run_finished(tw, api, monkeypatch):
    import fake_api
    rid = tw.runs.create("A problem that is long enough to pass.").id
    monkeypatch.setattr(fake_api, "EVENTS", [
        ("run.started", {"max_rounds": None}), ("run.error", {"message": "The run hit a problem and stopped."}),
        ("run.finished", {"status": "failed", "stop_reason": "failed", "best_score": None})])
    api.drop_stream_after = 2  # the connection ends right after run.error
    evs = list(tw.runs.events(rid))
    assert [type(e).__name__ for e in evs] == ["RunStarted", "RunError", "RunFinished"]
    assert evs[0].max_rounds is None and evs[-1].status == "failed"
    reqs = [r for r in api.requests if r.url.path.endswith("/events")]
    assert len(reqs) == 2 and reqs[1].headers["last-event-id"] == "2", "run.error is not the end of the stream"


def test_events_accept_a_final_run_finished_without_an_id(tw, api, monkeypatch):
    """A run interrupted by maintenance ends on a run.finished the server synthesizes (no id)."""
    import fake_api
    rid = tw.runs.create("A problem that is long enough to pass.").id
    real = api.handle

    def handle(req):
        res = real(req)
        if req.url.path.endswith("/events"):
            body = res.read() + b'event: run.finished\ndata: {"status": "failed", "stop_reason": "failed", "best_score": 4.0}\n\n'
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)
        return res

    monkeypatch.setattr(fake_api, "EVENTS", [("run.started", {"max_rounds": 2})])
    tw2 = Client(api_key=KEY, base_url="https://api.test/api/v1", transport=httpx.MockTransport(handle))
    evs = list(tw2.runs.events(rid))
    assert isinstance(evs[-1], RunFinished) and evs[-1].id is None and evs[-1].best_score == 4.0


def test_wait_returns_finished_run(tw):
    rid = tw.runs.create("A problem that is long enough to pass.").id
    assert tw.runs.wait(rid, timeout=5, poll=0).status == "completed"
