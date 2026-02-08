# CLAUDE.md

## Project Overview

Apollo MCP is a lean MCP server that exposes Apollo.io search, enrichment, and contact management to AI agents via STDIO JSON-RPC 2.0. Zero external dependencies.

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

- `search_people` — POST `/v1/mixed_people/api_search`. Free. No emails/phones.
- `search_organizations` — POST `/v1/mixed_companies/search`. 1 credit/result.
- `enrich_people` — POST `/v1/people/bulk_match`. 1 credit/match. 1-10 people.
- `enrich_organizations` — POST `/v1/organizations/bulk_enrich`. 1 credit/match. 1-10 orgs.
- `list_contact_stages` — GET `/v1/contact_stages`. Free. Returns stage names/IDs.
- `search_contacts` — POST `/v1/contacts/search`. Free. Searches your CRM contacts. Accepts stage names.
- `create_contacts` — POST `/v1/contacts/bulk_create`. 1-100 contacts. Deduplicates.
- `update_contacts` — POST `/v1/contacts/bulk_update`. 1-100 contacts. Same fields to all.
- `update_contact_stages` — POST `/v1/contacts/update_stages`. 1-100 contacts. Accepts stage name or ID.

## Adding New Functionality

When adding a new tool or changing behavior:
1. Add the API method in `api.py`, schema + dispatch + execution in `tools.py`
2. Add a test in `tests/` — at minimum cover the happy path and key validation
3. Update the Tools list in this file and the corresponding section in `README.md`
4. Run `pytest tests/` before considering it done

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
