# Runs the ThinkerWave MCP server over stdio (used by Glama and other MCP hosts).
# Built from this repo's own source so it always matches the release.
# The server starts and lists its tools without a key; set THINKERWAVE_API_KEY to run.
FROM python:3.12-slim
WORKDIR /app
COPY python/ /app/python/
RUN pip install --no-cache-dir "/app/python[mcp]"
ENTRYPOINT ["thinkerwave-mcp"]
