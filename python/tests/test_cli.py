import json
import os
import stat

import pytest

import thinkerwave.client as client_module
from thinkerwave import Client
from thinkerwave import cli
from fake_api import FakeApi, KEY

PROBLEM = "Should we raise prices 15%, 8%, or hold? Long enough."


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retries must not really sleep."""
    monkeypatch.setattr(client_module, "_sleep", lambda s: None)


@pytest.fixture
def api():
    return FakeApi()


@pytest.fixture
def run_cli(api, monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setenv("THINKERWAVE_API_KEY", KEY)
    def factory(key=None):
        return Client(api_key=key or KEY, base_url="https://api.test/api/v1", transport=api.transport())
    return lambda *argv: cli.main(list(argv), client_factory=factory)


def test_run_prints_id_and_sends_flags(run_cli, api, capsys):
    assert run_cli("run", PROBLEM, "--given", "1,200 customers", "--given", "$85/month",
                   "--standard", "Show break-even", "--pitfall", "Ignore the spike", "--rounds", "6") == 0
    out = capsys.readouterr().out
    rid = next(iter(api.runs))
    assert rid in out
    assert api.runs[rid]["_body"] == {"problem": PROBLEM, "given": ["1,200 customers", "$85/month"],
                                      "standards": ["Show break-even"], "pitfalls": ["Ignore the spike"],
                                      "max_rounds": 6}


def test_run_watch_then_answer(run_cli, capsys):
    assert run_cli("run", PROBLEM, "--watch") == 0
    out = capsys.readouterr().out
    assert "Round 1 of 2" in out and "best 6.0" in out
    assert "Take the 8% increase now." in out and "[verified]" in out and "[assumption]" in out


def test_answer_json(run_cli, api, capsys):
    run_cli("run", PROBLEM)
    rid = next(iter(api.runs))
    capsys.readouterr()
    assert run_cli("answer", rid, "--json") == 0
    assert json.loads(capsys.readouterr().out)["answer"].startswith("Take")


def test_no_answer_yet(run_cli, api, capsys):
    run_cli("run", PROBLEM)
    rid = next(iter(api.runs))
    api.answer_ready = False
    capsys.readouterr()
    assert run_cli("answer", rid) == 1
    assert "No answer yet" in capsys.readouterr().err


def test_files_and_get(run_cli, api, capsys, tmp_path):
    run_cli("run", PROBLEM)
    rid = next(iter(api.runs))
    assert run_cli("files", rid) == 0 and "chart.png" in capsys.readouterr().out
    out = tmp_path / "c.png"
    assert run_cli("get", rid, "chart.png", "-o", str(out)) == 0 and out.read_bytes() == b"PNG"


def test_unknown_run_and_auth_exit_codes(run_cli, monkeypatch, capsys):
    assert run_cli("status", "wr_nope") == 1
    monkeypatch.setenv("THINKERWAVE_API_KEY", "tw_live_" + "x" * 32)
    def bad(key=None):
        return Client(api_key="tw_live_" + "x" * 32, base_url="https://api.test/api/v1", transport=FakeApi().transport())
    assert cli.main(["me"], client_factory=bad) == 3
    assert "invalid" in capsys.readouterr().err.lower()


def test_usage_error(run_cli):
    assert run_cli("run") == 2


def test_login_stores_key_privately(monkeypatch, tmp_path, api):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.delenv("THINKERWAVE_API_KEY", raising=False)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": KEY)

    def factory(key=None):
        return Client(api_key=key, base_url="https://api.test/api/v1", transport=api.transport())

    assert cli.main(["login"], client_factory=factory) == 0
    p = cli.config_path()
    assert KEY in p.read_text() and stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert cli.main(["me"], client_factory=factory) == 0, "stored key is used when the env var is absent"


def test_login_rejects_empty_key(monkeypatch, tmp_path, api, capsys):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "   ")

    def factory(key=None):
        return Client(api_key=key, base_url="https://api.test/api/v1", transport=api.transport())

    assert cli.main(["login"], client_factory=factory) == 2
    assert not cli.config_path().exists()
    assert "No key entered" in capsys.readouterr().err


def test_watch_shows_step_then_tool_counts_on_finish(run_cli, capsys):
    assert run_cli("run", PROBLEM, "--watch") == 0
    lines = capsys.readouterr().out.splitlines()
    i = lines.index("Round 1 of 2")
    # The fake emits round.step(work) then round.tool(python) then round.finished, so the step line
    # shows before the tool, and the tool count appears on the finish line (tool events do not print).
    assert lines[i:i + 3] == ["Round 1 of 2", "Round 1 of 2 · working", "Round 1 of 2 · python ×1 · best 4.0"]


def test_credit_exhausted_exits_4(run_cli, api, capsys):
    api.fail_next.append((402, "credit_exhausted"))
    assert run_cli("run", PROBLEM) == 4
    assert len(api.requests) == 1, "a 402 is not retried"


def test_login_tightens_existing_key_file(monkeypatch, tmp_path, api):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": KEY)
    p = cli.config_path()
    p.parent.mkdir(parents=True)
    p.write_text('api_key = "tw_live_old"\n')
    os.chmod(p, 0o644)

    def factory(key=None):
        return Client(api_key=key, base_url="https://api.test/api/v1", transport=api.transport())

    assert cli.main(["login"], client_factory=factory) == 0
    assert stat.S_IMODE(os.stat(p).st_mode) == 0o600
    assert p.read_text() == f'api_key = "{KEY}"\n'


def test_login_creates_config_dir_private(monkeypatch, tmp_path, api):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr("getpass.getpass", lambda prompt="": KEY)

    def factory(key=None):
        return Client(api_key=key, base_url="https://api.test/api/v1", transport=api.transport())

    assert cli.main(["login"], client_factory=factory) == 0
    assert stat.S_IMODE(os.stat(cli.config_path().parent).st_mode) == 0o700


def test_run_watch_json_keeps_stdout_pure_json(run_cli, capsys):
    assert run_cli("run", PROBLEM, "--watch", "--json") == 0
    cap = capsys.readouterr()
    assert json.loads(cap.out)["answer"].startswith("Take"), "stdout is exactly one JSON document"
    assert "Started wr_" in cap.err and "Round 1 of 2" in cap.err and "Run completed" in cap.err


def test_watch_run_error_then_failed_finish(run_cli, api, capsys, monkeypatch):
    import fake_api
    monkeypatch.setattr(fake_api, "EVENTS", [
        ("run.started", {"max_rounds": 2}), ("round.started", {"round": 1}),
        ("run.error", {"message": "The run hit a problem and stopped."}),
        ("run.finished", {"status": "failed", "stop_reason": "failed", "best_score": None})])
    run_cli("run", PROBLEM)
    rid = next(iter(api.runs))
    capsys.readouterr()
    assert run_cli("watch", rid) == 1
    cap = capsys.readouterr()
    assert "The run hit a problem and stopped." in cap.err
    assert cap.out.splitlines()[-1] == "Run failed (failed).", "the stream continues to run.finished"


def test_rounds_prints_scores_with_one_decimal(run_cli, api, capsys):
    run_cli("run", PROBLEM)
    rid = next(iter(api.runs))
    capsys.readouterr()
    assert run_cli("rounds", rid) == 0
    out = capsys.readouterr().out
    assert "Round 1 · 4.0 ·" in out and "Round 2 · 6.0 ·" in out
    assert "6.699" not in out and "4.0000" not in out


def test_me_shows_credit_left_for_a_paid_plan(run_cli, api, capsys):
    api.me_extra = {"plan": "managed", "credit_remaining_usd": 9.93}
    assert run_cli("me") == 0
    assert "$9.93 credit left" in capsys.readouterr().out


def test_me_trial_shows_no_dollar_figure(run_cli, capsys):
    assert run_cli("me") == 0
    assert "$" not in capsys.readouterr().out
