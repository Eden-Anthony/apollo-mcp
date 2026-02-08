# Apollo.io MCP Server

Lean MCP server exposing Apollo.io people and organization search to AI agents via STDIO JSON-RPC 2.0. Zero external dependencies.

## Setup

```bash
pip install -e .
```

Set your API key:

```bash
export APOLLO_API_KEY=your_key
```

## Usage

### Run directly

```bash
python -m apollo_mcp          # production
python -m apollo_mcp --debug  # debug logging to stderr
```

### Claude Desktop / Claude Code

Add to your MCP config:

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

## Tools

### `search_people`

Search for people in Apollo.io's database. **Does NOT consume credits.** Does not return emails or phone numbers.

Parameters (all optional):
- `q_keywords` — keyword search
- `person_titles` — e.g. `["CEO", "VP Engineering"]`
- `person_seniorities` — `senior`, `manager`, `director`, `vp`, `c_suite`, `owner`, `partner`
- `person_locations` — e.g. `["San Francisco, CA"]`
- `organization_ids` — Apollo org IDs
- `q_organization_domains` — e.g. `["stripe.com"]`
- `organization_locations` — company HQ locations
- `organization_num_employees_ranges` — `"1-10"`, `"11-50"`, etc.
- `organization_industry_tag_ids` — industry tags
- `page` (default 1) / `per_page` (default 25, max 100)

### `search_organizations`

Search for companies. **Consumes credits.**

Parameters (all optional):
- `q_organization_name` — name search
- `organization_locations`
- `organization_industry_tag_ids`
- `organization_num_employees_ranges`
- `revenue_range` — `{"min": number, "max": number}`
- `organization_keywords`
- `page` (default 1) / `per_page` (default 25, max 100)

## Response Format

Results are flattened to scannable records:

**People:** `{id, name, title, seniority, city, state, country, linkedin_url, company, company_domain, company_industry, company_size}`

**Organizations:** `{id, name, domain, linkedin_url, industry, estimated_employees, founded_year, city, state, country, annual_revenue, total_funding, latest_funding_stage, keywords, technologies}`
