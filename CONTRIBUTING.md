# Contributing

Issues are welcome: bugs, feature requests, and answers ThinkerWave got wrong (use the "wrong answer" template, include
the run id, and never include your API key).

Pull requests are welcome for the Python SDK, the `tw` command line, the MCP server, the docs and the examples.
The hosted service is not part of this repository.

## Set up

```bash
git clone https://github.com/thinkerwave-ai/thinkerwave
cd thinkerwave/python
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,mcp]"
```

## Before you open a PR

```bash
cd python
pytest -q
ruff check src tests ../examples
```

Tests run against an in-memory fake of the API (`python/tests/fake_api.py`), so they need no key and no network.
If you change the API surface, update `spec/openapi.yaml`, `spec/answer.schema.json` or `spec/events.schema.json`
together with the fake and the docs; `python/tests/test_schemas.py` checks they agree.

Add a line to `CHANGELOG.md` for anything a user would notice.
