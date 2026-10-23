# Changelog

## Unreleased

- Add `py.typed` marker so type checkers (mypy, pyright) can discover the package's type information.

## 0.1.2 — 2026-10-21

- MCP server publishes instructions (when to use ThinkerWave, how runs work, keep the evidence labels), plus its title, website and version.
- `Dockerfile` for MCP hosts (e.g. Glama) — starts and lists tools without a key.

## 0.1.1 — 2026-10-20

- New `thinkerwave-mcp` package: run the MCP server with `uvx thinkerwave-mcp` (MCP Registry listing `io.github.thinkerwave-ai/thinkerwave`).
- `tw me` shows the credit left on paid plans.
- Licence is now Apache-2.0.

## 0.1.0 — 2026-10-19

- Python SDK: start runs, read answers, rounds and files, follow events with automatic reconnect.
- `tw` command line.
- `thinkerwave-mcp` server for Claude Code, Cursor and other MCP clients.
- API reference, OpenAPI description and JSON Schemas for the answer and the event stream.
