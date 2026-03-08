"""High-level tests for the MCP JSON-RPC server layer."""

import os
import json
import pytest
from unittest.mock import patch, MagicMock

os.environ["APOLLO_API_KEY"] = "test-key"

from apollo_mcp.server import MCPServer


def send_and_capture(server, message):
    """Send a JSON-RPC message and capture the response."""
    captured = []

    def mock_print(*args, **kwargs):
        captured.append(args[0])

    with patch("builtins.print", mock_print):
        server._handle_request(message)

    assert captured, "No response sent"
    return json.loads(captured[0])


@pytest.fixture
def server():
    s = MCPServer()
    resp = send_and_capture(s, {"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert "result" in resp
    assert s.initialized
    return s


def test_initialize_returns_capabilities(server):
    assert server.tools is not None


def test_tools_list_returns_all_tools(server):
    resp = send_and_capture(server, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [t["name"] for t in resp["result"]["tools"]]
    assert len(names) == 15
    assert "search_people" in names
    assert "create_contacts" in names


def test_tools_call_dispatches(server):
    server.tools.client._post = MagicMock(return_value={
        "people": [{"id": "p1", "name": "Test", "organization": {}}],
        "pagination": {"total_entries": 1},
    })

    resp = send_and_capture(server, {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "search_people", "arguments": {"q_keywords": "test"}},
    })

    content = json.loads(resp["result"]["content"][0]["text"])
    assert content["total_results"] == 1


def test_tools_call_validation_error(server):
    resp = send_and_capture(server, {
        "jsonrpc": "2.0", "id": 4, "method": "tools/call",
        "params": {"name": "enrich_people", "arguments": {"details": []}},
    })

    assert resp["error"]["code"] == -32602


def test_tools_call_api_error(server):
    from apollo_mcp.api import ApolloAPIError
    server.tools.client._post = MagicMock(side_effect=ApolloAPIError("Rate limited", 429))

    resp = send_and_capture(server, {
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "search_people", "arguments": {}},
    })

    assert resp["result"]["isError"] is True


def test_unknown_method(server):
    resp = send_and_capture(server, {"jsonrpc": "2.0", "id": 6, "method": "foo/bar"})
    assert resp["error"]["code"] == -32601


def test_tools_call_before_init():
    s = MCPServer()
    resp = send_and_capture(s, {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search_people", "arguments": {}},
    })
    assert resp["error"]["code"] == -32002


def test_ping(server):
    resp = send_and_capture(server, {"jsonrpc": "2.0", "id": 7, "method": "ping"})
    assert resp["result"] == {}
