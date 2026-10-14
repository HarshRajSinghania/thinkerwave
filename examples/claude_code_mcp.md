# Using ThinkerWave from Claude Code

## Install

```bash
pip install "thinkerwave[mcp]"
```

Create an API key at thinkerwave.ai/app → Settings → API keys.

## Add the server

```bash
claude mcp add thinkerwave --env THINKERWAVE_API_KEY=tw_live_… -- thinkerwave-mcp
```

Check it is connected with `/mcp` inside Claude Code.

## A sample prompt

> Use ThinkerWave to stress-test our consumer loan portfolio against a recession where unemployment rises 4 points and house prices fall 15%. Facts to keep exactly: 40,000 loans, 1.8 billion outstanding, 55% unsecured, current default rate 2.4%, Tier 1 capital 9.5% of risk-weighted assets. Start the run, check on it until it finishes, then give me the answer and list which findings are verified and which are assumptions or guesses.

Claude Code will call `start_run`, check `run_status` every minute or two (a run takes minutes), then call `get_answer`
and, if the run made charts, `list_files` and `read_file`.

See [docs/mcp.md](../docs/mcp.md) for the full tool list and for Cursor.
