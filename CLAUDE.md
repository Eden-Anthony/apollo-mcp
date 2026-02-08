# CLAUDE.md

## Project Overview

Apollo MCP is a lean MCP server that exposes Apollo.io people and organization search to AI agents via STDIO JSON-RPC 2.0. Zero external dependencies.

## Quick Start

```bash
pip install -e .
APOLLO_API_KEY=your_key python -m apollo_mcp --debug
```

## Architecture

- `apollo_mcp/api.py` — HTTP client (urllib.request only, no deps). `ApolloClient` validates `APOLLO_API_KEY` at construction.
- `apollo_mcp/tools.py` — Tool schemas (`get_tool_schemas()`) and execution (`ApolloTools.execute_tool()`). Flattens verbose Apollo responses to scannable records.
- `apollo_mcp/server.py` — STDIO JSON-RPC 2.0 MCP server. Handles `initialize`, `tools/list`, `tools/call`, `ping`, and notifications.
- `apollo_mcp/__main__.py` — Entry point for `python -m apollo_mcp`.

## Tools

- `search_people` — POST `/v1/mixed_people/search`. Free (no credits). No emails/phones returned.
- `search_organizations` — POST `/v1/mixed_companies/search`. Consumes credits.

## Error Handling

- API errors → tool result with `isError: true` (LLM-visible, retryable)
- Missing API key → fails at `initialize` with clear message
- JSON-RPC errors: -32700 (parse), -32602 (params), -32601 (method), -32603 (internal), -32002 (not initialized)

## Configuration for Claude Desktop

```json
{
  "mcpServers": {
    "apollo": {
      "command": "python",
      "args": ["-m", "apollo_mcp"],
      "env": {
        "APOLLO_API_KEY": "your_key"
      }
    }
  }
}
```
