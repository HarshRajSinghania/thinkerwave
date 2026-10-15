from __future__ import annotations  # lazy annotations

import json
import os
import pathlib
import time
from typing import Any, Iterator, Optional
from urllib.parse import quote

import httpx

from .errors import InvalidKeyError, RateLimitedError, ThinkerWaveError, UnavailableError, error_for
from .events import parse_sse
from .models import (Answer, Event, File, Me, Round, Run, RunCreated, RunSummary, parse_event)

DEFAULT_BASE_URL = "https://api.thinkerwave.ai/api/v1"
_RETRYABLE = (429, 502, 503, 504)
_MAX_RETRIES = 3
_STREAM_TIMEOUT = httpx.Timeout(30.0, read=60.0)  # the server sends a keepalive comment every 15 s
_sleep = time.sleep  # module-level so tests can patch the backoff
_UNREACHABLE = "ThinkerWave is unreachable right now — try again in a moment."


def _seg(run_id: str) -> str:
    """A run id as one URL path segment (`/`, `?`, `#`, `%` and spaces are escaped)."""
    return quote(str(run_id), safe="")


def _file_path(path: str) -> str:
    """A file path for a URL: segments keep their `/`; `?`, `#`, `%` and spaces are escaped."""
    return quote(str(path), safe="/")


def _backoff(attempt: int) -> float:
    return min(8.0, 0.5 * 2 ** attempt)


def _is_retryable(status: int, err: ThinkerWaveError, retry_5xx: bool = True) -> bool:
    if isinstance(err, RateLimitedError) and err.code == "run_limit":
        return False
    return status == 429 or (retry_5xx and status in _RETRYABLE)


def _retry_wait(headers: httpx.Headers, attempt: int) -> float:
    """Honour a numeric Retry-After header (429 or 503), else back off exponentially."""
    ra = headers.get("retry-after", "")
    if ra.replace(".", "", 1).isdigit():
        return min(float(ra), 60.0)
    return _backoff(attempt)


class Client:
    def __init__(self, api_key: Optional[str] = None, base_url: str = DEFAULT_BASE_URL, timeout: float = 30.0,
                 transport: Optional[httpx.BaseTransport] = None) -> None:
        key = api_key or os.environ.get("THINKERWAVE_API_KEY")
        if not key:
            raise InvalidKeyError("invalid_key", "No API key. Set THINKERWAVE_API_KEY or pass api_key=… "
                                  "(create one at thinkerwave.ai/app → Settings → API keys).")
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, transport=transport,
                                  headers={"Authorization": f"Bearer {key}",
                                           "User-Agent": "thinkerwave-python/0.1.0"})
        self.runs = Runs(self)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, *, retry_5xx: bool = True, **kw: Any) -> httpx.Response:
        for attempt in range(_MAX_RETRIES + 1):
            try:
                res = self._http.request(method, path, **kw)
            except httpx.TransportError as exc:
                # Same policy as a 5xx: retried unless the request may have been accepted (POST /runs).
                if not retry_5xx or attempt == _MAX_RETRIES:
                    raise UnavailableError("unavailable", _UNREACHABLE) from exc
                _sleep(_backoff(attempt))
                continue
            if res.status_code < 300:
                return res
            if res.status_code < 400:
                # A redirect is never part of the API contract: something between us and
                # ThinkerWave (a proxy, a captive portal) answered instead. Say so plainly.
                raise UnavailableError("unavailable", f"Unexpected reply from ThinkerWave (HTTP {res.status_code}) "
                                       "— check the base URL or try again in a moment.")
            try:
                body = res.json()
            except ValueError:
                body = None
            err = error_for(res.status_code, body, dict(res.headers))
            if not _is_retryable(res.status_code, err, retry_5xx) or attempt == _MAX_RETRIES:
                raise err
            _sleep(_retry_wait(res.headers, attempt))
        raise UnavailableError("unavailable", "Unreachable")  # pragma: no cover

    def _json(self, method: str, path: str, **kw: Any) -> Any:
        res = self._request(method, path, **kw)
        try:
            return res.json()
        except ValueError:
            raise UnavailableError("unavailable", "ThinkerWave sent a reply that was not JSON — "
                                   "check the base URL or try again in a moment.") from None

    def me(self) -> Me:
        return Me.model_validate(self._json("GET", "/me"))


class Runs:
    def __init__(self, client: Client) -> None:
        self._c = client

    def create(self, problem: str, *, given: Optional[list[str]] = None, standards: Optional[list[str]] = None,
               pitfalls: Optional[list[str]] = None, max_rounds: Optional[int] = None) -> RunCreated:
        body: dict[str, Any] = {"problem": problem}
        if given:
            body["given"] = list(given)
        if standards:
            body["standards"] = list(standards)
        if pitfalls:
            body["pitfalls"] = list(pitfalls)
        if max_rounds is not None:
            body["max_rounds"] = max_rounds
        # A 5xx may arrive after the server accepted the run; retrying would create a duplicate.
        return RunCreated.model_validate(self._c._json("POST", "/runs", retry_5xx=False, json=body))

    def get(self, run_id: str) -> Run:
        return Run.model_validate(self._c._json("GET", f"/runs/{_seg(run_id)}"))

    def list(self, limit: int = 20) -> list[RunSummary]:
        return [RunSummary.model_validate(x) for x in self._c._json("GET", "/runs", params={"limit": limit})]

    def stop(self, run_id: str) -> None:
        self._c._request("POST", f"/runs/{_seg(run_id)}/stop")

    def answer(self, run_id: str) -> Answer:
        return Answer.model_validate(self._c._json("GET", f"/runs/{_seg(run_id)}/answer"))

    def rounds(self, run_id: str) -> list[Round]:
        return [Round.model_validate(x) for x in self._c._json("GET", f"/runs/{_seg(run_id)}/rounds")]

    def files(self, run_id: str) -> list[File]:
        return [File.model_validate(x) for x in self._c._json("GET", f"/runs/{_seg(run_id)}/files")]

    def read(self, run_id: str, path: str) -> bytes:
        return self._c._request("GET", f"/runs/{_seg(run_id)}/files/{_file_path(path)}").content

    def download(self, run_id: str, path: str, to: "str | os.PathLike[str]" = ".") -> pathlib.Path:
        dest_dir = pathlib.Path(to).resolve()
        dest = (dest_dir / path).resolve()
        if dest_dir not in dest.parents:
            raise ValueError(f"Refusing to write outside {dest_dir}: {path}")
        folder = dest.parent
        folder.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.read(run_id, path))
        return dest

    def events(self, run_id: str, max_reconnects: int = 5) -> Iterator[Event]:
        """Typed events until the run finishes; resumes with Last-Event-ID after a drop.

        `max_reconnects` bounds *consecutive* failures: it resets whenever a new event arrives.
        """
        last: Optional[int] = None
        failures = 0
        while True:
            headers = {"Accept": "text/event-stream"}
            if last is not None:
                headers["Last-Event-ID"] = str(last)
            finished = False
            wait: Optional[float] = None
            try:
                with self._c._http.stream("GET", f"/runs/{_seg(run_id)}/events", headers=headers,
                                          timeout=_STREAM_TIMEOUT) as res:
                    if res.status_code >= 400:
                        res.read()
                        try:
                            body = res.json()
                        except ValueError:
                            body = None
                        err = error_for(res.status_code, body, dict(res.headers))
                        if not _is_retryable(res.status_code, err) or failures >= max_reconnects:
                            raise err
                        wait = _retry_wait(res.headers, failures)
                    else:
                        for eid, name, data in parse_sse(res.iter_lines()):
                            try:
                                payload = json.loads(data)
                            except ValueError:
                                continue
                            num = int(eid) if eid and eid.isdigit() else None
                            if num is not None:
                                if last is not None and num <= last:
                                    continue
                                last = num
                                failures = 0
                            ev = parse_event(name, payload, num)
                            if ev is None:
                                continue
                            yield ev
                            if name == "run.finished":  # run.error is followed by run.finished
                                finished = True
            except httpx.TransportError:
                pass  # a dropped or timed-out connection: treated like a clean end without run.finished
            if finished:
                return
            if wait is None:
                if failures >= max_reconnects:
                    raise ThinkerWaveError("stream_lost", "The event stream kept dropping.")
                wait = _backoff(failures)
            failures += 1
            _sleep(wait)

    def wait(self, run_id: str, timeout: float = 1800, poll: float = 5.0) -> Run:
        deadline = time.monotonic() + timeout
        while True:
            run = self.get(run_id)
            if run.finished:
                return run
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Run {run_id} still {run.status} after {timeout:.0f}s")
            time.sleep(poll)
