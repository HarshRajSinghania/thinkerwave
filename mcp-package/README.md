# thinkerwave-mcp

The ThinkerWave MCP server, packaged so any MCP client can start it with `uvx thinkerwave-mcp`.

ThinkerWave is an autonomous research agent for problems without a single right answer. Your assistant hands it a hard question; it works the problem round after round, checks its own work, and returns an answer where every claim is labelled **verified**, **assumption** or **guess** — plus any charts and tables it produced.

## Use it

Claude Code:

```bash
claude mcp add thinkerwave --env THINKERWAVE_API_KEY=tw_live_… -- uvx thinkerwave-mcp
```

Any MCP client (stdio):

```json
{ "command": "uvx", "args": ["thinkerwave-mcp"], "env": { "THINKERWAVE_API_KEY": "tw_live_…" } }
```

Get an API key at [thinkerwave.ai/app](https://thinkerwave.ai/app) → Settings → API keys. Free runs are included with every account.

Tools: `start_run`, `run_status`, `get_answer`, `list_files`, `read_file`, `stop_run`. Full guide: [docs/mcp.md](https://github.com/thinkerwave-ai/thinkerwave/blob/main/docs/mcp.md). The SDK and the `tw` command line are in the [`thinkerwave`](https://pypi.org/project/thinkerwave/) package.

<!-- mcp-name: io.github.thinkerwave-ai/thinkerwave -->
