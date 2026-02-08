"""Apollo.io HTTP client using only urllib.request."""

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict


class ApolloAPIError(Exception):
    """Apollo API error with status code and response body."""

    def __init__(self, message: str, status_code: int = 0, body: str = ""):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class ApolloClient:
    """Minimal Apollo.io API client."""

    BASE_URL = "https://api.apollo.io"
    TIMEOUT = 30

    def __init__(self):
        self.api_key = os.environ.get("APOLLO_API_KEY", "").strip()
        if not self.api_key:
            raise ApolloAPIError(
                "APOLLO_API_KEY environment variable is not set. "
                "Get your key at https://app.apollo.io/#/settings/integrations/api"
            )

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST JSON to Apollo API and return parsed response."""
        url = f"{self.BASE_URL}{path}"
        data = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "User-Agent": "apollo-mcp/0.1.0",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass

            if e.code == 401:
                raise ApolloAPIError("Invalid API key", status_code=401, body=body)
            elif e.code == 422:
                raise ApolloAPIError(
                    f"Invalid parameters: {body}", status_code=422, body=body
                )
            elif e.code == 429:
                raise ApolloAPIError("Rate limited — try again later", status_code=429, body=body)
            else:
                raise ApolloAPIError(
                    f"HTTP {e.code}: {body}", status_code=e.code, body=body
                )
        except urllib.error.URLError as e:
            raise ApolloAPIError(f"Network error: {e.reason}")
        except TimeoutError:
            raise ApolloAPIError("Request timed out after 30s")

    def _get(self, path: str) -> Dict[str, Any]:
        """GET from Apollo API and return parsed response."""
        url = f"{self.BASE_URL}{path}"

        req = urllib.request.Request(
            url,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "User-Agent": "apollo-mcp/0.1.0",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8")
            except Exception:
                pass

            if e.code == 401:
                raise ApolloAPIError("Invalid API key", status_code=401, body=body)
            elif e.code == 429:
                raise ApolloAPIError("Rate limited — try again later", status_code=429, body=body)
            else:
                raise ApolloAPIError(
                    f"HTTP {e.code}: {body}", status_code=e.code, body=body
                )
        except urllib.error.URLError as e:
            raise ApolloAPIError(f"Network error: {e.reason}")
        except TimeoutError:
            raise ApolloAPIError("Request timed out after 30s")

    def list_contact_stages(self) -> Dict[str, Any]:
        """List all contact stages for the team."""
        return self._get("/api/v1/contact_stages")

    def search_people(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search people via mixed_people/search. Does NOT consume credits."""
        return self._post("/api/v1/mixed_people/api_search", params)

    def search_organizations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search organizations via mixed_companies/search. DOES consume credits."""
        return self._post("/api/v1/mixed_companies/search", params)

    def enrich_people(self, details: list, reveal_personal_emails: bool = False,
                      reveal_phone_number: bool = False) -> Dict[str, Any]:
        """Bulk enrich people via people/bulk_match. DOES consume credits."""
        payload: Dict[str, Any] = {"details": details}
        if reveal_personal_emails:
            payload["reveal_personal_emails"] = True
        if reveal_phone_number:
            payload["reveal_phone_number"] = True
        return self._post("/api/v1/people/bulk_match", payload)

    def enrich_organizations(self, details: list) -> Dict[str, Any]:
        """Bulk enrich organizations via organizations/bulk_enrich. DOES consume credits."""
        return self._post("/api/v1/organizations/bulk_enrich", {"details": details})

    def search_contacts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search contacts in your CRM via contacts/search."""
        return self._post("/api/v1/contacts/search", params)

    def create_contacts(self, contacts: list) -> Dict[str, Any]:
        """Bulk create contacts via contacts/bulk_create. Does NOT update existing."""
        return self._post("/api/v1/contacts/bulk_create", {"contacts": contacts})

    def update_contacts(self, contact_ids: list, **fields) -> Dict[str, Any]:
        """Bulk update contacts via contacts/bulk_update."""
        payload: Dict[str, Any] = {"contact_ids": contact_ids}
        payload.update(fields)
        return self._post("/api/v1/contacts/bulk_update", payload)

    def update_contact_stages(self, contact_ids: list, contact_stage_id: str) -> Dict[str, Any]:
        """Update contact stage for multiple contacts."""
        return self._post("/api/v1/contacts/update_stages", {
            "contact_ids": contact_ids,
            "contact_stage_id": contact_stage_id,
        })
