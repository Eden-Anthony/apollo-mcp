# Apollo.io MCP Server

Lean MCP server exposing Apollo.io search, enrichment, and contact management to AI agents via STDIO JSON-RPC 2.0. Zero external dependencies.

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

### Search

#### `search_people` — FREE

Search Apollo's people database. Returns names, titles, companies, LinkedIn URLs — but not emails or phones (use `enrich_people` for that).

Parameters (all optional):
- `q_keywords` — keyword search
- `q_organization_name` — filter by company name
- `person_titles` — e.g. `["CEO", "VP Engineering"]`
- `person_seniorities` — `senior`, `manager`, `director`, `vp`, `c_suite`, `owner`, `partner`
- `person_locations` — e.g. `["San Francisco, CA"]`
- `organization_ids` — Apollo org IDs
- `q_organization_domains` — e.g. `["stripe.com"]`
- `organization_locations` — company HQ locations
- `organization_num_employees_ranges` — `"1-10"`, `"11-50"`, etc.
- `organization_industry_tag_ids` — industry tags
- `page` (default 1) / `per_page` (default 25, max 100)

#### `search_organizations` — 1 credit/result

Search Apollo's organization database.

Parameters (all optional):
- `q_organization_name` — name search
- `organization_locations`
- `organization_industry_tag_ids`
- `organization_num_employees_ranges`
- `revenue_range` — `{"min": number, "max": number}`
- `organization_keywords`
- `page` (default 1) / `per_page` (default 25, max 100)

### Enrichment

#### `enrich_people` — 1 credit/match

Get full contact details (email, phone, title, company) for 1-10 people. Identify each person by name + domain, LinkedIn URL, or Apollo person ID from `search_people`.

- `details` (required) — array of objects with: `first_name`, `last_name`, `name`, `email`, `organization_name`, `domain`, `id`, `linkedin_url`
- `reveal_personal_emails` — default false, may cost additional credits
- `reveal_phone_number` — default false, may cost additional credits

#### `enrich_organizations` — 1 credit/match

Get full company details (industry, size, funding, technologies) for 1-10 orgs. Identify by domain (best), name, or Apollo org ID from `search_organizations`.

- `details` (required) — array of objects with: `domain`, `name`, `id`

### Contact Management

Contacts are your CRM records. These tools use **contact IDs**, not people/org IDs from search.

Stage names (e.g. "Cold", "Interested") are resolved automatically — no need to look up IDs manually.

#### `list_contact_stages` — FREE

List all pipeline stages for your team. Returns stage names, IDs, and categories.

#### `search_contacts` — FREE

Search your team's CRM contacts. Unlike `search_people`, this only returns contacts you've already added to Apollo.

Parameters (all optional):
- `q_keywords` — keyword search across name, title, company, email
- `contact_stages` — filter by stage names or IDs, e.g. `["Cold", "Interested"]`
- `owner_id` — filter by contact owner IDs
- `sort_by_field` — e.g. `"contact_updated_at"`
- `sort_ascending` — default false (newest first)
- `page` (default 1) / `per_page` (default 25, max 100)

#### `create_contacts`

Add 1-100 people to your CRM. Duplicates are returned separately in `existing_contacts`.

- `contacts` (required) — array of objects with: `first_name`, `last_name`, `email`, `phone_number`, `title`, `organization_name`, `account_id`, `owner_id`, `contact_stage_id`

#### `update_contacts`

Update fields on 1-100 existing CRM contacts. Applies the same values to all specified contacts.

- `contact_ids` (required) — array of contact IDs
- `owner_id`, `contact_stage_id`, `title`, `organization_name`, `account_id` — fields to update

#### `update_contact_stages`

Move 1-100 contacts to a new pipeline stage. Preferred over `update_contacts` when only the stage is changing.

- `contact_ids` (required) — array of contact IDs
- `contact_stage` (required) — stage name (e.g. "Interested") or stage ID

## Typical Workflow

```
search_people → enrich_people → create_contacts → update_contacts / update_contact_stages
```

1. **Search** to find people or orgs (free for people, credits for orgs)
2. **Enrich** to get full contact details (1 credit each)
3. **Create contacts** to add them to your CRM
4. **Update** contacts or move them through pipeline stages
