"""`thinkerwave-mcp` — ThinkerWave as MCP tools (docs/mcp.md). Runs take minutes:
start_run returns at once, and the assistant checks back with run_status."""

from __future__ import annotations  # lazy annotations

import json
from typing import Any, Callable
from typing import Optional

import httpx
from mcp.server.mcpserver import Image, MCPServer

from . import Client, __version__
from .errors import NotFoundError, ThinkerWaveError

# Shown to the assistant ahead of the tool list (and by MCP directories).
INSTRUCTIONS = (
    "ThinkerWave is an autonomous research agent for hard, open-ended questions "
    "(pricing, risk, market entry, due diligence, candidate selection). Use it when "
    "a careful, evidence-backed answer matters more than a fast one; for simple "
    "lookups, answer directly instead. Runs take minutes: call start_run with the "
    "problem (put facts the user is sure of in `given`), then check back with "
    "run_status every minute or so, and call get_answer when it has finished. "
    "Every claim in the answer is labelled verified, assumption or guess: keep "
    "those labels when you report back. list_files and read_file return the "
    "charts and tables it produced; stop_run ends a run early."
)

TEXT_LIMIT = 200_000
IMAGE_LIMIT = 1_000_000
_TEXT_EXTENSIONS = ("md", "txt", "csv", "tsv", "json")
_IMAGE_FORMATS = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "gif": "gif", "webp": "webp"}


def build_server(client_factory: Callable[[], Client]) -> MCPServer:
    mcp = MCPServer(
        "thinkerwave",
        title="ThinkerWave",
        website_url="https://thinkerwave.ai",
        version=__version__,
        instructions=INSTRUCTIONS,
    )
    state: dict[str, Client] = {}

    def tw() -> Client:
        if "c" not in state:
            state["c"] = client_factory()
        return state["c"]

    def guard(fn: Callable[[], Any]) -> Any:
        try:
            return fn()
        except NotFoundError as e:
            return e.message
        except ThinkerWaveError as e:
            return f"ThinkerWave error ({e.code}): {e.message}"
        except httpx.HTTPError:
            return "ThinkerWave is unreachable right now — try again in a moment."

    @mcp.tool()
    def start_run(problem: str, given: Optional[list[str]] = None, standards: Optional[list[str]] = None,
                  pitfalls: Optional[list[str]] = None, max_rounds: Optional[int] = None) -> str:
        """Start a ThinkerWave run on a hard, open-ended problem. `given`: facts to keep exactly as written.
        `standards`: what a good answer must do. `pitfalls`: mistakes to avoid. Returns the run id; runs take
        several minutes — check back with run_status, then get_answer."""
        def go() -> str:
            r = tw().runs.create(problem, given=given, standards=standards, pitfalls=pitfalls, max_rounds=max_rounds)
            return json.dumps({"id": r.id, "status": r.status, "queue_position": r.queue_position,
                               "next": "Call run_status with this id in a minute or two."})
        return guard(go)

    @mcp.tool()
    def run_status(id: str) -> str:
        """Status of a run: round, best score so far, and why it stopped once finished."""
        def go() -> str:
            r = tw().runs.get(id)
            return json.dumps({"id": r.id, "status": r.status, "round": r.round, "max_rounds": r.max_rounds,
                               "best_score": r.best_score, "stop_reason": r.stop_reason, "error": r.error})
        return guard(go)

    @mcp.tool()
    def get_answer(id: str) -> str:
        """The best answer so far (or the final one), its confidence, and each finding tagged
        verified / assumption / guess."""
        return guard(lambda: json.dumps(tw().runs.answer(id).model_dump()))

    @mcp.tool()
    def list_files(id: str) -> str:
        """Files the run produced (charts, tables, notes)."""
        return guard(lambda: json.dumps([f.model_dump() for f in tw().runs.files(id)]))

    @mcp.tool()
    def read_file(id: str, path: str):
        """Read one produced file: text files as text (up to 200 KB), images as images (up to 1 MB)."""
        def go():
            ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
            is_image, is_text = ext in _IMAGE_FORMATS, ext in _TEXT_EXTENSIONS
            too_big = f"{path} is not shown here — download it with `tw get {id} {path}`."
            if not (is_image or is_text):
                return too_big
            limit = IMAGE_LIMIT if is_image else TEXT_LIMIT
            entry = next((f for f in tw().runs.files(id) if f.path == path), None)
            if entry is None:
                return f"No file {path} in this run. Use list_files to see what it produced."
            if entry.size is not None and entry.size > limit:
                return too_big
            data = tw().runs.read(id, path)
            if len(data) > limit:
                return too_big
            if is_image:
                return Image(data=data, format=_IMAGE_FORMATS[ext])
            return data.decode("utf-8", errors="replace")
        return guard(go)

    @mcp.tool()
    def stop_run(id: str) -> str:
        """Stop a run. The best answer so far is kept."""
        return guard(lambda: (tw().runs.stop(id), json.dumps({"ok": True}))[1])

    return mcp


def main() -> None:
    build_server(lambda: Client()).run()


if __name__ == "__main__":  # pragma: no cover
    main()
