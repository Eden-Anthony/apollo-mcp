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
        "contacts": [{"id": "c1", "first_name": "Jane", "email": "jane@acme.com"}],
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
