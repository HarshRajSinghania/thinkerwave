"""The SDK, the thinkerwave-mcp launcher and the MCP Registry server.json must
release in lock-step — a mismatch publishes a launcher pinned to a missing SDK."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _version(pyproject: Path) -> str:
    return re.search(r'^version = "([^"]+)"', pyproject.read_text(), re.M).group(1)


def test_versions_move_together():
    sdk = _version(ROOT / "python" / "pyproject.toml")
    launcher = _version(ROOT / "mcp-package" / "pyproject.toml")
    pin = re.search(r'"thinkerwave\[mcp\]==([^"]+)"', (ROOT / "mcp-package" / "pyproject.toml").read_text()).group(1)
    server = json.loads((ROOT / "server.json").read_text())
    from thinkerwave import __version__
    assert sdk == launcher == pin == server["version"] == server["packages"][0]["version"] == __version__


def test_registry_ownership_marker_matches_server_name():
    server = json.loads((ROOT / "server.json").read_text())
    readme = (ROOT / "mcp-package" / "README.md").read_text()
    assert f"<!-- mcp-name: {server['name']} -->" in readme
    assert server["packages"][0]["identifier"] == "thinkerwave-mcp"


def test_registry_description_fits():
    # The MCP Registry rejects descriptions over 100 characters (422 on publish).
    server = json.loads((ROOT / "server.json").read_text())
    assert len(server["description"]) <= 100
