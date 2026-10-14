# Claude Code, Cursor and other MCP clients

The `thinkerwave-mcp` server lets an AI assistant start ThinkerWave runs and read their results.
Runs take minutes, so the assistant starts a run, checks back on its status, then reads the answer.

## Install

```bash
pip install "thinkerwave[mcp]"
```

Create an API key at thinkerwave.ai/app → Settings → API keys. The server reads it from `THINKERWAVE_API_KEY`.

## Claude Code

```bash
claude mcp add thinkerwave --env THINKERWAVE_API_KEY=tw_live_… -- thinkerwave-mcp
```

Then ask in plain words:

> Use ThinkerWave to stress-test our credit portfolio against a 3-point rise in unemployment. Start the run, and when it finishes, summarise the answer and tell me which findings are verified.

## Cursor

Add this to `~/.cursor/mcp.json` (or the project's `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "thinkerwave": {
      "command": "thinkerwave-mcp",
      "env": { "THINKERWAVE_API_KEY": "tw_live_…" }
    }
  }
}
```

Any client that can launch a stdio MCP server works the same way: command `thinkerwave-mcp`, environment variable
`THINKERWAVE_API_KEY`.

Keep the key out of files you commit.

## Tools

| Tool | What it does |
|---|---|
| `start_run` | Start a run: `problem`, optional `given`, `standards`, `pitfalls`, `max_rounds`. Returns the run id. |
| `run_status` | Status, round, best score so far, and why it stopped once finished. |
| `get_answer` | The best answer so far (or the final one), its confidence, and findings tagged verified / assumption / guess. |
| `list_files` | Files the run produced. |
| `read_file` | Read one produced file: text as text (up to 200 KB), images as images (up to 1 MB). Larger files are not shown; download them with `tw get`. |
| `stop_run` | Stop a run. |

Problems are reported back to the assistant as plain messages (for example a limit being reached), so it can tell you.
