"""Tool schemas, execution dispatch, and response formatting for Apollo MCP."""

import json
from typing import Any, Dict, List

from .api import ApolloClient, ApolloAPIError


def get_tool_schemas() -> List[Dict[str, Any]]:
    """Return MCP tool schema definitions."""
    return [
        {
            "name": "search_people",
            "description": (
                "Search Apollo's people database. FREE — does not consume credits. "
                "Returns names, titles, companies, and LinkedIn URLs but NOT emails or phones. "
                "To get contact details, pass the results to enrich_people. "
                "All parameters are optional — combine to narrow results."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q_keywords": {
                        "type": "string",
                        "description": "Keyword search across name, title, company, etc.",
                    },
                    "q_organization_name": {
                        "type": "string",
                        "description": "Filter by company name, e.g. \"Stripe\"",
                    },
                    "person_titles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Job titles to filter by, e.g. ["CEO", "VP Engineering"]',
                    },
                    "person_seniorities": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "senior",
                                "manager",
                                "director",
                                "vp",
                                "c_suite",
                                "owner",
                                "partner",
                            ],
                        },
                        "description": "Seniority levels to filter by",
                    },
                    "person_locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Person locations, e.g. ["San Francisco, CA"]',
                    },
                    "organization_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Apollo organization IDs to scope search to",
                    },
                    "q_organization_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Company domains, e.g. ["stripe.com"]',
                    },
                    "organization_locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Company HQ locations",
                    },
                    "organization_num_employees_ranges": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Employee count ranges: "1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+"',
                    },
                    "organization_industry_tag_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Industry tag IDs",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default 1, max 500)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 500,
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Results per page (default 25, max 100)",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        },
        {
            "name": "search_organizations",
            "description": (
                "Search Apollo's organization database. COSTS 1 CREDIT PER RESULT. "
                "Returns company name, domain, industry, size, funding, and technologies. "
                "To get full details, pass results to enrich_organizations. "
                "All parameters are optional — combine to narrow results."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q_organization_name": {
                        "type": "string",
                        "description": "Company name search",
                    },
                    "organization_locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Company HQ locations",
                    },
                    "organization_industry_tag_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Industry tag IDs",
                    },
                    "organization_num_employees_ranges": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": 'Employee count ranges: "1-10", "11-50", "51-200", "201-500", "501-1000", "1001-5000", "5001-10000", "10001+"',
                    },
                    "revenue_range": {
                        "type": "object",
                        "properties": {
                            "min": {"type": "number"},
                            "max": {"type": "number"},
                        },
                        "description": "Revenue range filter with min/max in USD",
                    },
                    "organization_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords to search in company descriptions",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default 1, max 500)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 500,
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Results per page (default 25, max 100)",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        },
        {
            "name": "enrich_people",
            "description": (
                "Get full contact details (email, phone, title, company) for 1-10 people. "
                "COSTS 1 CREDIT PER MATCH. Identify each person by name + domain, "
                "LinkedIn URL, or Apollo person ID from search_people results. "
                "Personal emails and phone numbers require reveal flags (additional credits)."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "details": {
                        "type": "array",
                        "description": (
                            "Array of 1-10 people to enrich. Each object should contain "
                            "identifying fields like name + domain, linkedin_url, or Apollo id."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "first_name": {"type": "string", "description": "Person's first name"},
                                "last_name": {"type": "string", "description": "Person's last name"},
                                "name": {"type": "string", "description": "Full name (alternative to first/last)"},
                                "email": {"type": "string", "description": "Known email address"},
                                "organization_name": {"type": "string", "description": "Company name"},
                                "domain": {"type": "string", "description": "Company domain, e.g. stripe.com"},
                                "id": {"type": "string", "description": "Apollo person ID (from search results)"},
                                "linkedin_url": {"type": "string", "description": "LinkedIn profile URL"},
                            },
                        },
                        "minItems": 1,
                        "maxItems": 10,
                    },
                    "reveal_personal_emails": {
                        "type": "boolean",
                        "description": "Retrieve personal emails. May consume additional credits. Default: false",
                        "default": False,
                    },
                    "reveal_phone_number": {
                        "type": "boolean",
                        "description": "Retrieve phone numbers. May consume additional credits. Default: false",
                        "default": False,
                    },
                },
                "required": ["details"],
            },
        },
        {
            "name": "enrich_organizations",
            "description": (
                "Get full company details (industry, size, funding, technologies) for 1-10 orgs. "
                "COSTS 1 CREDIT PER MATCH. Identify each org by domain (best), name, "
                "or Apollo org ID from search_organizations results."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "details": {
                        "type": "array",
                        "description": (
                            "Array of 1-10 organizations to enrich. Each object should contain "
                            "at least one identifying field: domain (best), name, or Apollo id."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "domain": {
                                    "type": "string",
                                    "description": 'Company domain, e.g. "stripe.com" (best identifier)',
                                },
                                "name": {
                                    "type": "string",
                                    "description": "Company name",
                                },
                                "id": {
                                    "type": "string",
                                    "description": "Apollo organization ID (from search results)",
                                },
                            },
                        },
                        "minItems": 1,
                        "maxItems": 10,
                    },
                },
                "required": ["details"],
            },
        },
        {
            "name": "search_contacts",
            "description": (
                "Search your CRM contacts (people you've already added to Apollo). FREE. "
                "Unlike search_people which searches Apollo's global database, this only "
                "searches your team's contacts. Returns contact IDs usable with "
                "update_contacts and update_contact_stages."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "q_keywords": {
                        "type": "string",
                        "description": "Keyword search across name, title, company, email, etc.",
                    },
                    "contact_stage_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by contact stage IDs",
                    },
                    "owner_id": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by contact owner IDs",
                    },
                    "sort_by_field": {
                        "type": "string",
                        "description": 'Sort field, e.g. "contact_updated_at"',
                    },
                    "sort_ascending": {
                        "type": "boolean",
                        "description": "Sort ascending (default false = newest first)",
                        "default": False,
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default 1, max 500)",
                        "default": 1,
                        "minimum": 1,
                        "maximum": 500,
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Results per page (default 25, max 100)",
                        "default": 25,
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
            },
        },
        {
            "name": "create_contacts",
            "description": (
                "Add 1-100 people to your Apollo CRM as contacts. "
                "Existing matches are returned in existing_contacts without modification — "
                "use update_contacts to modify those. "
                "Returns contact IDs needed for update_contacts and update_contact_stages."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contacts": {
                        "type": "array",
                        "description": "Array of 1-100 contacts to create.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "first_name": {"type": "string", "description": "First name"},
                                "last_name": {"type": "string", "description": "Last name"},
                                "email": {"type": "string", "description": "Email address"},
                                "phone_number": {"type": "string", "description": "Phone number"},
                                "title": {"type": "string", "description": "Job title"},
                                "organization_name": {"type": "string", "description": "Company name"},
                                "account_id": {"type": "string", "description": "Apollo account ID to associate with"},
                                "owner_id": {"type": "string", "description": "Apollo user ID for contact owner"},
                                "contact_stage_id": {"type": "string", "description": "Contact stage ID"},
                            },
                        },
                        "minItems": 1,
                        "maxItems": 100,
                    },
                },
                "required": ["contacts"],
            },
        },
        {
            "name": "update_contacts",
            "description": (
                "Update fields on 1-100 existing CRM contacts. Applies the same values "
                "to all specified contacts. Requires contact IDs from create_contacts results. "
                "Note: these are contact IDs, not people IDs from search_people."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contact_ids": {
                        "type": "array",
                        "description": "Apollo contact IDs to update (1-100).",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 100,
                    },
                    "owner_id": {"type": "string", "description": "New contact owner (Apollo user ID)"},
                    "contact_stage_id": {"type": "string", "description": "New contact stage ID"},
                    "title": {"type": "string", "description": "New job title"},
                    "organization_name": {"type": "string", "description": "New company name"},
                    "account_id": {"type": "string", "description": "Apollo account ID to associate with"},
                },
                "required": ["contact_ids"],
            },
        },
        {
            "name": "update_contact_stages",
            "description": (
                "Move 1-100 CRM contacts to a new pipeline stage. "
                "Preferred over update_contacts when only the stage is changing. "
                "Requires contact IDs (not people IDs) and a contact_stage_id."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contact_ids": {
                        "type": "array",
                        "description": "Apollo contact IDs to update (1-100).",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": 100,
                    },
                    "contact_stage_id": {
                        "type": "string",
                        "description": "The new contact stage ID to assign to all specified contacts.",
                    },
                },
                "required": ["contact_ids", "contact_stage_id"],
            },
        },
    ]


class ApolloTools:
    """Executes Apollo MCP tools and formats responses."""

    def __init__(self, client: ApolloClient):
        self.client = client

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool call and return formatted result."""
        if name == "search_people":
            return self._search_people(arguments)
        elif name == "search_organizations":
            return self._search_organizations(arguments)
        elif name == "enrich_people":
            return self._enrich_people(arguments)
        elif name == "enrich_organizations":
            return self._enrich_organizations(arguments)
        elif name == "search_contacts":
            return self._search_contacts(arguments)
        elif name == "create_contacts":
            return self._create_contacts(arguments)
        elif name == "update_contacts":
            return self._update_contacts(arguments)
        elif name == "update_contact_stages":
            return self._update_contact_stages(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

    # ---- people ----

    def _search_people(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = _clamp_pagination(_clean_params(args))
        raw = self.client.search_people(params)

        # Apollo returns people under "people" or "contacts" inconsistently
        people_raw = raw.get("people") or raw.get("contacts") or []
        # api_search puts total_entries at top level; search puts it in pagination
        pagination = raw.get("pagination", {})

        people = [_format_person(p) for p in people_raw]

        return {
            "total_results": raw.get("total_entries") or pagination.get("total_entries", len(people)),
            "page": pagination.get("page", params.get("page", 1)),
            "per_page": pagination.get("per_page", params.get("per_page", 25)),
            "people": people,
        }

    # ---- enrichment ----

    def _enrich_people(self, args: Dict[str, Any]) -> Dict[str, Any]:
        details = args.get("details", [])

        # Guardrail: hard cap at 10 (API limit)
        if len(details) > 10:
            raise ValueError("Maximum 10 people per enrichment request (API limit)")
        if len(details) == 0:
            raise ValueError("At least 1 person required in details array")

        # Validate each person has at least one identifying field
        id_fields = {"first_name", "last_name", "name", "email", "organization_name",
                      "domain", "id", "linkedin_url", "hashed_email"}
        for i, person in enumerate(details):
            if not any(person.get(f) for f in id_fields):
                raise ValueError(
                    f"Person at index {i} has no identifying fields. "
                    "Provide at least name + domain, linkedin_url, or Apollo id."
                )

        raw = self.client.enrich_people(
            details=details,
            reveal_personal_emails=args.get("reveal_personal_emails", False),
            reveal_phone_number=args.get("reveal_phone_number", False),
        )

        matches = [_format_enriched_person(m) for m in raw.get("matches", []) if m]

        return {
            "total_requested": raw.get("total_requested_enrichments", len(details)),
            "matched": raw.get("unique_enriched_records", len(matches)),
            "missing": raw.get("missing_records", 0),
            "credits_consumed": raw.get("credits_consumed", 0),
            "people": matches,
        }

    # ---- contacts ----

    def _search_contacts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = _clamp_pagination(_clean_params(args))
        raw = self.client.search_contacts(params)

        contacts = [_format_contact(c) for c in raw.get("contacts") or []]
        pagination = raw.get("pagination", {})

        return {
            "total_results": pagination.get("total_entries", len(contacts)),
            "page": pagination.get("page", params.get("page", 1)),
            "per_page": pagination.get("per_page", params.get("per_page", 25)),
            "contacts": contacts,
        }

    def _create_contacts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        contacts = args.get("contacts", [])

        if len(contacts) > 100:
            raise ValueError("Maximum 100 contacts per request (API limit)")
        if len(contacts) == 0:
            raise ValueError("At least 1 contact required in contacts array")

        for i, c in enumerate(contacts):
            if not any(c.get(f) for f in ("first_name", "last_name", "email")):
                raise ValueError(
                    f"Contact at index {i} needs at least a name or email."
                )

        raw = self.client.create_contacts(contacts=contacts)

        created = [_format_contact(c) for c in raw.get("contacts") or []]
        existing = [_format_contact(c) for c in raw.get("existing_contacts") or []]

        return {
            "total_requested": len(contacts),
            "created": len(created),
            "already_existed": len(existing),
            "new_contacts": created,
            "existing_contacts": existing,
        }

    def _update_contacts(self, args: Dict[str, Any]) -> Dict[str, Any]:
        contact_ids = args.get("contact_ids", [])

        if len(contact_ids) > 100:
            raise ValueError("Maximum 100 contacts per request (API limit)")
        if len(contact_ids) == 0:
            raise ValueError("At least 1 contact_id required")

        fields = {k: v for k, v in args.items()
                  if k != "contact_ids" and v is not None}
        if not fields:
            raise ValueError("Provide at least one field to update")

        raw = self.client.update_contacts(contact_ids, **fields)

        updated = [_format_contact(c) for c in raw.get("contacts") or []]

        return {
            "total_requested": len(contact_ids),
            "updated": len(updated),
            "contacts": updated,
        }

    def _update_contact_stages(self, args: Dict[str, Any]) -> Dict[str, Any]:
        contact_ids = args.get("contact_ids", [])
        contact_stage_id = args.get("contact_stage_id", "")

        if len(contact_ids) > 100:
            raise ValueError("Maximum 100 contacts per request (API limit)")
        if len(contact_ids) == 0:
            raise ValueError("At least 1 contact_id required")
        if not contact_stage_id:
            raise ValueError("contact_stage_id is required")

        raw = self.client.update_contact_stages(contact_ids, contact_stage_id)

        updated = [_format_contact(c) for c in raw.get("contacts") or raw.get("updated_contacts") or []]

        return {
            "total_requested": len(contact_ids),
            "updated": len(updated),
            "contacts": updated,
        }

    # ---- organizations ----

    def _search_organizations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        params = _clamp_pagination(_clean_params(args))
        raw = self.client.search_organizations(params)

        orgs_raw = raw.get("organizations") or raw.get("accounts") or []
        pagination = raw.get("pagination", {})

        organizations = [_format_organization(o) for o in orgs_raw]

        return {
            "total_results": pagination.get("total_entries", len(organizations)),
            "page": pagination.get("page", params.get("page", 1)),
            "per_page": pagination.get("per_page", params.get("per_page", 25)),
            "organizations": organizations,
        }

    def _enrich_organizations(self, args: Dict[str, Any]) -> Dict[str, Any]:
        details = args.get("details", [])

        if len(details) > 10:
            raise ValueError("Maximum 10 organizations per enrichment request (API limit)")
        if len(details) == 0:
            raise ValueError("At least 1 organization required in details array")

        id_fields = {"domain", "name", "id"}
        for i, org in enumerate(details):
            if not any(org.get(f) for f in id_fields):
                raise ValueError(
                    f"Organization at index {i} has no identifying fields. "
                    "Provide at least domain, name, or Apollo id."
                )

        raw = self.client.enrich_organizations(details=details)

        matches = [_format_enriched_organization(m) for m in raw.get("matches", []) if m]

        return {
            "total_requested": raw.get("total_requested_enrichments", len(details)),
            "matched": raw.get("unique_enriched_records", len(matches)),
            "missing": raw.get("missing_records", 0),
            "credits_consumed": raw.get("credits_consumed", 0),
            "organizations": matches,
        }


# ---- helpers ----


def _clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Strip None and empty values before sending to API."""
    return {k: v for k, v in params.items() if v is not None and v != "" and v != []}


def _clamp_pagination(params: Dict[str, Any]) -> Dict[str, Any]:
    """Enforce server-side pagination limits regardless of what the LLM sends."""
    params["per_page"] = max(1, min(int(params.get("per_page", 25)), 100))
    params["page"] = max(1, min(int(params.get("page", 1)), 500))
    return params


def _format_person(p: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten an Apollo person record to a scannable dict.

    Handles both full records (from enrichment) and limited records
    from api_search (obfuscated last names, has_* booleans).
    """
    org = p.get("organization") or {}

    # Build name: api_search returns first_name + last_name_obfuscated
    name = p.get("name")
    if not name:
        first = p.get("first_name", "")
        last = p.get("last_name") or p.get("last_name_obfuscated", "")
        name = f"{first} {last}".strip() or None

    result = {
        "id": p.get("id"),
        "name": name,
        "title": p.get("title"),
        "seniority": p.get("seniority"),
        "city": p.get("city"),
        "state": p.get("state"),
        "country": p.get("country"),
        "linkedin_url": p.get("linkedin_url"),
        "company": org.get("name") or p.get("organization_name"),
        "company_domain": org.get("primary_domain"),
        "company_industry": org.get("industry"),
        "company_size": org.get("estimated_num_employees"),
    }

    # Strip None values for cleaner output
    return {k: v for k, v in result.items() if v is not None}


def _format_enriched_person(p: Dict[str, Any]) -> Dict[str, Any]:
    """Format a fully enriched person record with contact details."""
    org = p.get("organization") or {}

    name = p.get("name")
    if not name:
        first = p.get("first_name", "")
        last = p.get("last_name", "")
        name = f"{first} {last}".strip() or None

    result = {
        "id": p.get("id"),
        "name": name,
        "title": p.get("title"),
        "seniority": p.get("seniority"),
        "email": p.get("email"),
        "email_status": p.get("email_status"),
        "phone": (p.get("phone_numbers") or [{}])[0].get("sanitized_number") if p.get("phone_numbers") else None,
        "city": p.get("city"),
        "state": p.get("state"),
        "country": p.get("country"),
        "linkedin_url": p.get("linkedin_url"),
        "company": org.get("name") or p.get("organization_name"),
        "company_domain": org.get("primary_domain"),
        "company_industry": org.get("industry"),
        "company_size": org.get("estimated_num_employees"),
        "departments": p.get("departments"),
    }

    return {k: v for k, v in result.items() if v is not None}


def _format_organization(o: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten an Apollo organization record to a scannable dict."""
    return {
        "id": o.get("id"),
        "name": o.get("name"),
        "domain": o.get("primary_domain") or o.get("website_url"),
        "linkedin_url": o.get("linkedin_url"),
        "industry": o.get("industry"),
        "estimated_employees": o.get("estimated_num_employees"),
        "founded_year": o.get("founded_year"),
        "city": o.get("city"),
        "state": o.get("state"),
        "country": o.get("country"),
        "annual_revenue": o.get("annual_revenue"),
        "total_funding": o.get("total_funding"),
        "latest_funding_stage": o.get("latest_funding_stage"),
        "keywords": o.get("keywords"),
        "technologies": o.get("technologies"),
    }


def _format_enriched_organization(o: Dict[str, Any]) -> Dict[str, Any]:
    """Format a fully enriched organization record."""
    result = _format_organization(o)
    result["phone"] = o.get("phone")
    result["website_url"] = o.get("website_url")
    return {k: v for k, v in result.items() if v is not None}


def _format_contact(c: Dict[str, Any]) -> Dict[str, Any]:
    """Format a contact record from bulk_create response."""
    result = {
        "id": c.get("id"),
        "first_name": c.get("first_name"),
        "last_name": c.get("last_name"),
        "email": c.get("email"),
        "phone_number": c.get("phone_number"),
        "title": c.get("title"),
        "organization_name": c.get("organization_name"),
        "account_id": c.get("account_id"),
        "owner_id": c.get("owner_id"),
        "contact_stage_id": c.get("contact_stage_id"),
    }
    return {k: v for k, v in result.items() if v is not None}
