"""High-level tests for Apollo MCP tools — schemas, validation, dispatch, formatting."""

import os
import pytest
from unittest.mock import MagicMock

os.environ["APOLLO_API_KEY"] = "test-key"

from apollo_mcp.api import ApolloClient
from apollo_mcp.tools import ApolloTools, get_tool_schemas


# ---- fixtures ----

@pytest.fixture
def client():
    """ApolloClient with mocked _post."""
    c = ApolloClient()
    c._post = MagicMock()
    return c


FAKE_STAGES = [
    {"id": "stage-1", "name": "Cold", "category": "in_progress", "display_order": 0},
    {"id": "stage-2", "name": "Interested", "category": "succeeded", "display_order": 3},
    {"id": "stage-3", "name": "Not Interested", "category": "failed", "display_order": 4},
]


@pytest.fixture
def tools(client):
    t = ApolloTools(client)
    t._stage_cache = FAKE_STAGES
    return t


# ---- schemas ----

def test_all_tools_registered():
    names = [s["name"] for s in get_tool_schemas()]
    assert names == [
        "search_people",
        "search_organizations",
        "enrich_people",
        "enrich_organizations",
        "list_contact_stages",
        "search_contacts",
        "create_contacts",
        "update_contacts",
        "update_contact_stages",
        "search_sequences",
        "list_email_accounts",
        "add_contacts_to_sequence",
        "create_accounts",
        "update_accounts",
        "view_account",
    ]


def test_schemas_have_required_fields():
    for schema in get_tool_schemas():
        assert "name" in schema
        assert "description" in schema
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"


# ---- search_people ----

def test_search_people_formats_results(tools, client):
    client._post.return_value = {
        "people": [
            {
                "id": "p1",
                "first_name": "Jane",
                "last_name": "Doe",
                "title": "CEO",
                "organization": {"name": "Acme", "primary_domain": "acme.com"},
            }
        ],
        "pagination": {"total_entries": 1, "page": 1, "per_page": 25},
    }

    result = tools.execute_tool("search_people", {"q_keywords": "Jane"})

    assert result["total_results"] == 1
    assert len(result["people"]) == 1
    assert result["people"][0]["name"] == "Jane Doe"
    assert result["people"][0]["company"] == "Acme"


def test_search_people_clamps_pagination(tools, client):
    client._post.return_value = {"people": [], "pagination": {}}

    tools.execute_tool("search_people", {"per_page": 9999, "page": -1})

    call_args = client._post.call_args[0][1]
    assert call_args["per_page"] == 100
    assert call_args["page"] == 1


# ---- enrich_people ----

def test_enrich_people_returns_credits(tools, client):
    client._post.return_value = {
        "matches": [
            {
                "id": "p1",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@acme.com",
                "organization": {},
            }
        ],
        "total_requested_enrichments": 1,
        "unique_enriched_records": 1,
        "missing_records": 0,
        "credits_consumed": 1,
    }

    result = tools.execute_tool("enrich_people", {
        "details": [{"first_name": "Jane", "domain": "acme.com"}]
    })

    assert result["credits_consumed"] == 1
    assert result["people"][0]["email"] == "jane@acme.com"


def test_enrich_people_rejects_empty():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="At least 1"):
        t.execute_tool("enrich_people", {"details": []})


def test_enrich_people_rejects_over_limit():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="Maximum 10"):
        t.execute_tool("enrich_people", {"details": [{"name": "x"}] * 11})


def test_enrich_people_rejects_empty_person():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="no identifying fields"):
        t.execute_tool("enrich_people", {"details": [{}]})


# ---- enrich_organizations ----

def test_enrich_organizations_by_domain(tools, client):
    client._post.return_value = {
        "matches": [{"id": "o1", "name": "Stripe", "primary_domain": "stripe.com"}],
        "credits_consumed": 1,
    }

    result = tools.execute_tool("enrich_organizations", {
        "details": [{"domain": "stripe.com"}]
    })

    assert result["credits_consumed"] == 1
    assert result["organizations"][0]["name"] == "Stripe"


def test_enrich_organizations_rejects_no_identifier():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="no identifying fields"):
        t.execute_tool("enrich_organizations", {"details": [{}]})


# ---- list_contact_stages ----

def test_list_contact_stages(tools, client):
    client._get = MagicMock(return_value={
        "contact_stages": FAKE_STAGES,
    })
    tools._stage_cache = None  # force a fetch

    result = tools.execute_tool("list_contact_stages", {})

    assert len(result["stages"]) == 3
    assert result["stages"][0]["name"] == "Cold"
    assert result["stages"][1]["name"] == "Interested"


# ---- search_contacts ----

def test_search_contacts_resolves_stage_names(tools, client):
    client._post.return_value = {
        "contacts": [{"id": "c1", "first_name": "Jane", "contact_stage_id": "stage-1"}],
        "pagination": {"total_entries": 1},
    }

    tools.execute_tool("search_contacts", {"contact_stages": ["Cold"]})

    payload = client._post.call_args[0][1]
    assert payload["contact_stage_ids"] == ["stage-1"]


def test_search_contacts_returns_crm_contacts(tools, client):
    client._post.return_value = {
        "contacts": [
            {"id": "c1", "first_name": "Jane", "last_name": "Doe", "email": "jane@acme.com",
             "title": "CEO", "contact_stage_id": "stage-1"},
        ],
        "pagination": {"total_entries": 1, "page": 1, "per_page": 25},
    }

    result = tools.execute_tool("search_contacts", {"q_keywords": "Jane"})

    assert result["total_results"] == 1
    assert result["contacts"][0]["id"] == "c1"
    assert result["contacts"][0]["email"] == "jane@acme.com"


# ---- create_contacts ----

def test_create_contacts_separates_new_and_existing(tools, client):
    client._post.return_value = {
        "created_contacts": [{"id": "c1", "first_name": "Jane", "email": "jane@acme.com"}],
        "existing_contacts": [{"id": "c2", "first_name": "Bob", "email": "bob@acme.com"}],
    }

    result = tools.execute_tool("create_contacts", {
        "contacts": [
            {"first_name": "Jane", "email": "jane@acme.com"},
            {"first_name": "Bob", "email": "bob@acme.com"},
        ]
    })

    assert result["created"] == 1
    assert result["already_existed"] == 1
    assert result["new_contacts"][0]["id"] == "c1"
    assert result["existing_contacts"][0]["id"] == "c2"


def test_create_contacts_rejects_no_name_or_email():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="needs at least a name or email"):
        t.execute_tool("create_contacts", {"contacts": [{"title": "CEO"}]})


# ---- update_contacts ----

def test_update_contacts_passes_fields(tools, client):
    client._post.return_value = {
        "contacts": [{"id": "c1", "title": "CTO"}],
    }

    result = tools.execute_tool("update_contacts", {
        "contact_ids": ["c1"],
        "title": "CTO",
    })

    assert result["updated"] == 1
    payload = client._post.call_args[0][1]
    assert payload["contact_ids"] == ["c1"]
    assert payload["title"] == "CTO"


def test_update_contacts_rejects_no_fields():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="at least one field"):
        t.execute_tool("update_contacts", {"contact_ids": ["c1"]})


# ---- update_contact_stages ----

def test_update_contact_stages_by_name(tools, client):
    client._post.return_value = {
        "contacts": [{"id": "c1", "contact_stage_id": "stage-2"}],
    }

    result = tools.execute_tool("update_contact_stages", {
        "contact_ids": ["c1"],
        "contact_stage": "Interested",
    })

    assert result["updated"] == 1
    payload = client._post.call_args[0][1]
    assert payload["contact_stage_id"] == "stage-2"


def test_update_contact_stages_by_id(tools, client):
    client._post.return_value = {
        "contacts": [{"id": "c1", "contact_stage_id": "stage-2"}],
    }

    result = tools.execute_tool("update_contact_stages", {
        "contact_ids": ["c1"],
        "contact_stage": "stage-2",
    })

    payload = client._post.call_args[0][1]
    assert payload["contact_stage_id"] == "stage-2"


def test_update_contact_stages_coerces_string_array(tools, client):
    """MCP clients sometimes pass JSON arrays as strings."""
    client._post.return_value = {
        "contacts": [{"id": "c1", "contact_stage_id": "stage-2"}],
    }

    result = tools.execute_tool("update_contact_stages", {
        "contact_ids": '["c1", "c2"]',
        "contact_stage": "Interested",
    })

    payload = client._post.call_args[0][1]
    assert payload["contact_ids"] == ["c1", "c2"]


def test_update_contact_stages_coerces_single_string(tools, client):
    """A single string ID should be wrapped in a list."""
    client._post.return_value = {
        "contacts": [{"id": "c1", "contact_stage_id": "stage-2"}],
    }

    result = tools.execute_tool("update_contact_stages", {
        "contact_ids": "c1",
        "contact_stage": "Interested",
    })

    payload = client._post.call_args[0][1]
    assert payload["contact_ids"] == ["c1"]


def test_create_contacts_coerces_string_array(tools, client):
    """MCP clients sometimes pass JSON arrays as strings."""
    import json
    contacts = [{"first_name": "Jane", "email": "jane@acme.com"}]
    client._post.return_value = {
        "created_contacts": [{"id": "c1", "first_name": "Jane", "email": "jane@acme.com"}],
        "existing_contacts": [],
    }

    result = tools.execute_tool("create_contacts", {
        "contacts": json.dumps(contacts),
    })

    assert result["created"] == 1


def test_update_contact_stages_rejects_missing_stage():
    t = ApolloTools(ApolloClient())
    t._stage_cache = FAKE_STAGES
    with pytest.raises(ValueError, match="contact_stage is required"):
        t.execute_tool("update_contact_stages", {
            "contact_ids": ["c1"],
            "contact_stage": "",
        })


# ---- dispatch ----

def test_unknown_tool_raises():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="Unknown tool"):
        t.execute_tool("nonexistent", {})


# ---- formatting ----

def test_none_values_stripped_from_person(tools, client):
    client._post.return_value = {
        "people": [{"id": "p1", "first_name": "Jane", "title": None, "organization": {}}],
        "pagination": {},
    }

    result = tools.execute_tool("search_people", {})
    person = result["people"][0]
    assert "title" not in person


def test_none_values_stripped_from_enriched_org(tools, client):
    client._post.return_value = {
        "matches": [{"id": "o1", "name": "Acme", "phone": None, "primary_domain": None}],
    }

    result = tools.execute_tool("enrich_organizations", {
        "details": [{"name": "Acme"}]
    })

    org = result["organizations"][0]
    assert "phone" not in org
    assert "domain" not in org


def test_contact_stage_name_in_output(tools, client):
    client._post.return_value = {
        "contacts": [{"id": "c1", "first_name": "Jane", "contact_stage_id": "stage-2"}],
        "pagination": {},
    }

    result = tools.execute_tool("search_contacts", {})
    assert result["contacts"][0]["contact_stage"] == "Interested"
    assert result["contacts"][0]["contact_stage_id"] == "stage-2"


def test_null_matches_filtered(tools, client):
    client._post.return_value = {
        "matches": [None, {"id": "p1", "first_name": "Jane", "organization": {}}, None],
        "credits_consumed": 1,
    }

    result = tools.execute_tool("enrich_people", {
        "details": [{"name": "Jane", "domain": "acme.com"}]
    })

    assert len(result["people"]) == 1


# ---- search_sequences ----

def test_search_sequences_formats_results(tools, client):
    client._post.return_value = {
        "emailer_campaigns": [
            {
                "id": "seq1",
                "name": "Outbound Q1",
                "active": True,
                "num_steps": 5,
                "created_at": "2025-01-01T00:00:00Z",
            }
        ],
        "pagination": {"total_entries": 1, "page": 1, "per_page": 25},
    }

    result = tools.execute_tool("search_sequences", {"q_keywords": "Outbound"})

    assert result["total_results"] == 1
    assert len(result["sequences"]) == 1
    assert result["sequences"][0]["name"] == "Outbound Q1"
    assert result["sequences"][0]["active"] is True
    assert result["sequences"][0]["num_steps"] == 5


# ---- list_email_accounts ----

def test_list_email_accounts(tools, client):
    client._get = MagicMock(return_value={
        "email_accounts": [
            {"id": "ea1", "email": "alice@acme.com", "default": True},
            {"id": "ea2", "email": "bob@acme.com", "default": False},
        ],
    })

    result = tools.execute_tool("list_email_accounts", {})
    assert result["total"] == 2
    assert result["email_accounts"][0]["id"] == "ea1"


# ---- add_contacts_to_sequence ----

def test_add_contacts_to_sequence_passes_ids(tools, client):
    client._post.return_value = {
        "contacts": [{"id": "c1", "first_name": "Jane", "email": "jane@acme.com"}],
    }

    result = tools.execute_tool("add_contacts_to_sequence", {
        "sequence_id": "seq1",
        "contact_ids": ["c1"],
        "email_account_id": "ea1",
    })

    assert result["sequence_id"] == "seq1"
    assert result["contacts_added"] == 1
    payload = client._post.call_args[0][1]
    assert payload["contact_ids"] == ["c1"]
    assert payload["send_email_from_email_account_id"] == "ea1"


def test_add_contacts_to_sequence_rejects_empty_ids():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="At least 1"):
        t.execute_tool("add_contacts_to_sequence", {
            "sequence_id": "seq1",
            "contact_ids": [],
            "email_account_id": "ea1",
        })


def test_add_contacts_to_sequence_rejects_missing_sequence_id():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="sequence_id is required"):
        t.execute_tool("add_contacts_to_sequence", {
            "sequence_id": "",
            "contact_ids": ["c1"],
            "email_account_id": "ea1",
        })


# ---- create_accounts ----

def test_create_accounts_deduplicates_by_domain(tools, client):
    """Accounts with a matching domain in CRM are returned as existing, not created."""
    def mock_post(path, payload):
        if "accounts/search" in path:
            domains = payload.get("q_organization_domains", [])
            if "globex.com" in domains:
                return {"accounts": [{"id": "a2", "name": "Globex", "domain": "globex.com"}]}
            return {"accounts": []}
        if "accounts/bulk_create" in path:
            return {"newly_created_accounts": [{"id": "a1", "name": "Acme Corp", "domain": "acme.com"}]}
        return {}

    client._post = MagicMock(side_effect=mock_post)

    result = tools.execute_tool("create_accounts", {
        "accounts": [
            {"name": "Acme Corp", "domain": "acme.com"},
            {"name": "Globex", "domain": "globex.com"},
        ]
    })

    assert result["created"] == 1
    assert result["already_existed"] == 1
    assert result["new_accounts"][0]["id"] == "a1"
    assert result["existing_accounts"][0]["id"] == "a2"


def test_create_accounts_deduplicates_by_name(tools, client):
    """Accounts with a matching name (no domain) are returned as existing."""
    def mock_post(path, payload):
        if "accounts/search" in path:
            if payload.get("q_organization_name"):
                return {"accounts": [{"id": "a1", "name": "Acme Corp"}]}
            return {"accounts": []}
        return {}

    client._post = MagicMock(side_effect=mock_post)

    result = tools.execute_tool("create_accounts", {
        "accounts": [{"name": "Acme Corp"}]
    })

    assert result["created"] == 0
    assert result["already_existed"] == 1
    assert result["existing_accounts"][0]["id"] == "a1"


def test_create_accounts_name_match_is_exact(tools, client):
    """Name search only dedupes on exact match, not partial."""
    def mock_post(path, payload):
        if "accounts/search" in path:
            # Search returns a partial match — different name
            if payload.get("q_organization_name"):
                return {"accounts": [{"id": "a99", "name": "Acme Corp International"}]}
            return {"accounts": []}
        if "accounts/bulk_create" in path:
            return {"newly_created_accounts": [{"id": "a1", "name": "Acme Corp"}]}
        return {}

    client._post = MagicMock(side_effect=mock_post)

    result = tools.execute_tool("create_accounts", {
        "accounts": [{"name": "Acme Corp"}]
    })

    # Should NOT match the partial name — creates a new account
    assert result["created"] == 1
    assert result["already_existed"] == 0


def test_create_accounts_rejects_missing_name():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="missing a name"):
        t.execute_tool("create_accounts", {"accounts": [{"domain": "acme.com"}]})


def test_create_accounts_rejects_over_100():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="Maximum 100"):
        t.execute_tool("create_accounts", {"accounts": [{"name": "x"}] * 101})


# ---- update_accounts ----

def test_update_accounts_passes_fields(tools, client):
    client._post.return_value = {
        "accounts": [{"id": "a1", "name": "Acme Inc", "domain": "acme.com"}],
    }

    result = tools.execute_tool("update_accounts", {
        "account_ids": ["a1"],
        "name": "Acme Inc",
    })

    assert result["updated"] == 1
    payload = client._post.call_args[0][1]
    assert payload["account_ids"] == ["a1"]
    assert payload["name"] == "Acme Inc"


def test_update_accounts_rejects_no_fields():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="at least one field"):
        t.execute_tool("update_accounts", {"account_ids": ["a1"]})


def test_update_accounts_coerces_string_array(tools, client):
    """MCP clients sometimes pass JSON arrays as strings."""
    client._post.return_value = {
        "accounts": [{"id": "a1", "name": "Acme"}],
    }

    tools.execute_tool("update_accounts", {
        "account_ids": '["a1", "a2"]',
        "name": "Updated",
    })

    payload = client._post.call_args[0][1]
    assert payload["account_ids"] == ["a1", "a2"]


# ---- view_account ----

def test_view_account_returns_formatted(tools, client):
    client._get = MagicMock(return_value={
        "account": {
            "id": "a1",
            "name": "Acme Corp",
            "domain": "acme.com",
            "phone": "555-1234",
            "industry": "Technology",
            "owner_id": "u1",
            "city": "San Francisco",
            "state": "California",
            "country": "United States",
            "annual_revenue": None,
            "founded_year": None,
        },
    })

    result = tools.execute_tool("view_account", {"account_id": "a1"})

    account = result["account"]
    assert account["id"] == "a1"
    assert account["name"] == "Acme Corp"
    assert account["domain"] == "acme.com"
    assert account["city"] == "San Francisco"
    # None values should be stripped
    assert "annual_revenue" not in account
    assert "founded_year" not in account


def test_view_account_rejects_missing_id():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="account_id is required"):
        t.execute_tool("view_account", {"account_id": ""})


def test_add_contacts_to_sequence_rejects_missing_email_account_id():
    t = ApolloTools(ApolloClient())
    with pytest.raises(ValueError, match="email_account_id is required"):
        t.execute_tool("add_contacts_to_sequence", {
            "sequence_id": "seq1",
            "contact_ids": ["c1"],
        })
