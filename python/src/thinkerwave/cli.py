"""`tw` — the ThinkerWave command line."""

from __future__ import annotations  # lazy annotations

import argparse
import getpass
import json
import os
import pathlib
import sys
from typing import Callable, Optional, TextIO

import httpx

from . import Client
from .errors import CreditExhaustedError, InvalidKeyError, NotFoundError, RateLimitedError, ThinkerWaveError
from .models import (RoundFinished, RoundStarted, RoundStep, RoundTool, RunError, RunFinished, RunStarted,
                     RunWentBack)

STEP_WORDS = {"plan": "planning", "work": "working", "check": "checking", "rethink": "rethinking"}
EXIT_OK, EXIT_RUN, EXIT_USAGE, EXIT_AUTH, EXIT_LIMIT = 0, 1, 2, 3, 4


def config_path() -> pathlib.Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(pathlib.Path.home() / ".config")
    return pathlib.Path(base) / "thinkerwave" / "config.toml"


def _stored_key() -> Optional[str]:
    p = config_path()
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip() == "api_key":
            return v.strip().strip('"') or None
    return None


def _default_factory(key: Optional[str] = None) -> Client:
    return Client(api_key=key)


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tw", description="Run ThinkerWave from the terminal.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login", help="store an API key")
    sub.add_parser("me", help="your plan and limits")
    r = sub.add_parser("run", help="start a run")
    r.add_argument("problem")
    r.add_argument("--given", action="append", default=[], help="a fact to keep exactly as written (repeatable)")
    r.add_argument("--standard", action="append", default=[], help="what a good answer must do (repeatable)")
    r.add_argument("--pitfall", action="append", default=[], help="a mistake to avoid (repeatable)")
    r.add_argument("--rounds", type=int, default=None)
    r.add_argument("--watch", action="store_true", help="follow the run live, then print the answer")
    r.add_argument("--json", action="store_true")
    for name, helptext in (("status", "a run's status"), ("watch", "follow a run live"), ("rounds", "round by round"),
                           ("files", "files the run produced"), ("stop", "stop a run")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("id")
    a = sub.add_parser("answer", help="the answer and its evidence")
    a.add_argument("id")
    a.add_argument("--json", action="store_true")
    g = sub.add_parser("get", help="download a file")
    g.add_argument("id")
    g.add_argument("path")
    g.add_argument("-o", "--output", default=None)
    sub.add_parser("runs", help="your recent runs")
    return p


def _print_answer(tw: Client, run_id: str, as_json: bool) -> int:
    a = tw.runs.answer(run_id)
    if as_json:
        print(json.dumps(a.model_dump(), indent=2))
        return EXIT_OK
    print(f"\n{a.answer}\n")
    print(f"Confidence: {a.confidence} · from round {a.round}" + (f" · score {a.score:.1f}" if a.score is not None else ""))
    for f in a.findings:
        tag = f.evidence or "untagged"
        print(f"  [{tag}]{' [flagged]' if f.flagged else ''} {f.text}")
    return EXIT_OK


def _watch(tw: Client, run_id: str, out: Optional[TextIO] = None) -> int:
    """Follow a run, printing progress to `out` (stdout by default; stderr under --json)."""
    out = out or sys.stdout
    max_rounds: Optional[int] = None
    best: Optional[float] = None
    rnd, step, tools = 1, "", {"python": 0, "web_search": 0, "page_read": 0}
    status = "completed"

    def line() -> None:
        t = ", ".join(f"{k.replace('_', ' ')} ×{v}" for k, v in tools.items() if v)
        parts = [f"Round {rnd}" + (f" of {max_rounds}" if max_rounds else "")]
        if step:
            parts.append(STEP_WORDS.get(step, step))
        if t:
            parts.append(t)
        if best is not None:
            parts.append(f"best {best:.1f}")
        print(" · ".join(parts), file=out, flush=True)

    for ev in tw.runs.events(run_id):
        if isinstance(ev, RunStarted):
            max_rounds = ev.max_rounds
        elif isinstance(ev, RoundStarted):
            rnd, step, tools = ev.round, "", {"python": 0, "web_search": 0, "page_read": 0}
            line()
        elif isinstance(ev, RoundStep):
            step = ev.step
            line()
        elif isinstance(ev, RoundTool):
            tools[ev.kind] = tools.get(ev.kind, 0) + 1
        elif isinstance(ev, RoundFinished):
            if ev.score is not None and (best is None or ev.score > best):
                best = ev.score
            step = ""
            line()
        elif isinstance(ev, RunWentBack):
            print(f"Went back to the best answer, from round {ev.to_round}.", file=out)
        elif isinstance(ev, RunFinished):
            status = ev.status
            print(f"Run {ev.status}" + (f" ({ev.stop_reason.replace('_', ' ')})" if ev.stop_reason else "") + ".",
                  file=out)
        elif isinstance(ev, RunError):
            # Not the end: run.finished (status "failed") follows.
            print(ev.message, file=sys.stderr)
            status = "failed"
    return EXIT_OK if status == "completed" else EXIT_RUN


def _login(factory: Callable[..., Client]) -> int:
    key = getpass.getpass("API key (thinkerwave.ai/app → Settings → API keys): ").strip()
    if not key:
        print("No key entered.", file=sys.stderr)
        return EXIT_USAGE
    with factory(key) as tw:
        tw.me()
    p = config_path()
    os.makedirs(p.parent, mode=0o700, exist_ok=True)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(fd, 0o600)  # tighten a pre-existing file before the key lands in it
    with os.fdopen(fd, "w") as fh:
        fh.write(f'api_key = "{key}"\n')
    print(f"Saved to {p}")
    return EXIT_OK


def _run(tw: Client, args: argparse.Namespace) -> int:
    created = tw.runs.create(args.problem, given=args.given or None, standards=args.standard or None,
                             pitfalls=args.pitfall or None, max_rounds=args.rounds)
    if args.json and not args.watch:
        print(json.dumps(created.model_dump()))
        return EXIT_OK
    # With --json, stdout carries only the JSON answer; progress goes to stderr.
    progress = sys.stderr if args.json else sys.stdout
    print(f"Started {created.id}" + (f" (queued, position {created.queue_position})" if created.queue_position else ""),
          file=progress)
    if not args.watch:
        return EXIT_OK
    code = _watch(tw, created.id, progress)
    try:
        _print_answer(tw, created.id, args.json)
    except NotFoundError:
        print("No answer yet.", file=sys.stderr)
        return EXIT_RUN
    return code


def _dispatch(tw: Client, args: argparse.Namespace) -> int:
    if args.cmd == "me":
        m = tw.me()
        print(f"{m.email} · {m.plan} · {m.runs_today}/{m.runs_per_day} runs today · up to {m.max_rounds} rounds")
    elif args.cmd == "run":
        return _run(tw, args)
    elif args.cmd == "status":
        r = tw.runs.get(args.id)
        print(f"{r.id} · {r.status} · round {r.round} of {r.max_rounds} · best {r.best_score:.1f}"
              + (f" · {r.stop_reason.replace('_', ' ')}" if r.stop_reason else ""))
    elif args.cmd == "watch":
        return _watch(tw, args.id)
    elif args.cmd == "answer":
        try:
            return _print_answer(tw, args.id, args.json)
        except NotFoundError:
            print("No answer yet.", file=sys.stderr)
            return EXIT_RUN
    elif args.cmd == "rounds":
        for rd in tw.runs.rounds(args.id):
            change = (rd.change or "").replace("_", " ")
            ans = rd.answer.answer if rd.answer else "—"
            print(f"Round {rd.round} · {rd.score if rd.score is not None else '—'} · {change} · {ans}")
    elif args.cmd == "files":
        for f in tw.runs.files(args.id):
            print(f"{f.path}\t{f.kind}\t{f.size or ''}")
    elif args.cmd == "get":
        data = tw.runs.read(args.id, args.path)
        out = pathlib.Path(args.output or pathlib.Path(args.path).name)
        out.write_bytes(data)
        print(f"Wrote {out}")
    elif args.cmd == "stop":
        tw.runs.stop(args.id)
        print("Stopping.")
    elif args.cmd == "runs":
        for r in tw.runs.list():
            print(f"{r.id}\t{r.status}\t{r.best_score:.1f}\t{r.problem_preview[:60]}")
    return EXIT_OK


def main(argv: Optional[list[str]] = None, *, client_factory: Optional[Callable[..., Client]] = None) -> int:
    factory = client_factory or _default_factory
    try:
        args = _parser().parse_args(argv)
    except SystemExit as e:
        return EXIT_USAGE if e.code else EXIT_OK
    try:
        if args.cmd == "login":
            return _login(factory)
        key = os.environ.get("THINKERWAVE_API_KEY") or _stored_key()
        with factory(key) as tw:
            return _dispatch(tw, args)
    except InvalidKeyError as e:
        print(f"Invalid API key: {e.message}", file=sys.stderr)
        return EXIT_AUTH
    except (RateLimitedError, CreditExhaustedError) as e:
        print(e.message, file=sys.stderr)
        return EXIT_LIMIT
    except ThinkerWaveError as e:
        print(e.message, file=sys.stderr)
        return EXIT_RUN
    except httpx.TransportError as e:
        print(f"Could not reach ThinkerWave: {e}", file=sys.stderr)
        return EXIT_RUN


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
