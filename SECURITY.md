# Security

## Reporting a vulnerability

Email **security@thinkerwave.ai** with what you found and how to reproduce it. Please do not open a public issue for a
security problem. We will acknowledge your report and keep you informed.

## API keys

- Treat your API key like a password. **Never paste a key into an issue, a pull request, a chat or a commit.**
- Keep it in an environment variable (`THINKERWAVE_API_KEY`) or in a secrets manager, not in code.
- If a key may have leaked, revoke it right away in thinkerwave.ai/app → Settings → API keys and create a new one.
- `tw login` stores your key in a file readable only by you. Do not copy that file around.

## Scope

This repository holds the Python SDK, the command line, the MCP server, the API reference and the answer/evidence format.
Problems with ThinkerWave's hosted service itself can be reported to the same address.
