# ThinkerWave

[![PyPI](https://img.shields.io/pypi/v/thinkerwave)](https://pypi.org/project/thinkerwave/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://pypi.org/project/thinkerwave/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![MCP server](https://img.shields.io/badge/MCP-server-black)](docs/mcp.md)
[![CI](https://github.com/thinkerwave-ai/thinkerwave/actions/workflows/ci.yml/badge.svg)](https://github.com/thinkerwave-ai/thinkerwave/actions/workflows/ci.yml)

An autonomous research agent for problems without a single right answer — credit risk stress tests, pricing and churn, market entry, due diligence, drug program selection.

You give it the problem and the facts you're sure of. It researches, runs the numbers, checks its own work and tries again, round after round, keeping the best answer. You get the answer, how confident it is, and the evidence behind each claim — **verified**, **assumption** or **guess** — plus any charts and tables it produced.

![A real two-round ThinkerWave run in the terminal](docs/assets/demo.gif)

```bash
pip install thinkerwave
export THINKERWAVE_API_KEY=tw_live_…      # create one at thinkerwave.ai/app → Settings → API keys
tw run "Should we raise prices 15%, 8%, or hold? 1,200 customers at \$85/month, 3.1% monthly churn." \
  --given "last 8% increase spiked churn to 4.6% for three months" --rounds 6 --watch
```

**From Claude Code or Cursor:** `pip install "thinkerwave[mcp]"`, then `claude mcp add thinkerwave -- thinkerwave-mcp` — your coding assistant can now hand ThinkerWave a hard question and read back the evidence.

**From Python:** see `examples/`.

**What's in this repo:** the Python SDK, the `tw` command line, an MCP server, the API reference and the answer/evidence format. ThinkerWave itself runs in ThinkerWave's cloud; this repository is the way in, not the engine.

Free runs are included with every account. Limits: `docs/limits.md`. Found a problem it got wrong? Open an issue with the run id.
