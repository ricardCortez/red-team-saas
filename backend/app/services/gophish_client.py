"""HTTP client for the GoPhish REST API.

Usage:
    client = GoPhishClient(base_url="http://localhost:3333", api_key="...")
    campaigns = client.list_campaigns()
"""
import logging
from typing import Any, Dict, List

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


class GoPhishError(Exception):
    """Raised when GoPhish returns an error response."""


class GoPhishClient:
    def __init__(self, base_url: str, api_key: str):
        self._base = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.get(url, headers=self._headers, timeout=_TIMEOUT, verify=False)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise GoPhishError(f"GET {path} returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise GoPhishError(f"GET {path} failed: {exc}") from exc

    def _post(self, path: str, data: dict) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.post(url, headers=self._headers, json=data, timeout=_TIMEOUT, verify=False)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as exc:
            raise GoPhishError(f"POST {path} returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise GoPhishError(f"POST {path} failed: {exc}") from exc

    def _delete(self, path: str) -> Any:
        url = f"{self._base}{path}"
        try:
            r = httpx.delete(url, headers=self._headers, timeout=_TIMEOUT, verify=False)
            r.raise_for_status()
            return r.json() if r.content else {}
        except httpx.HTTPStatusError as exc:
            raise GoPhishError(f"DELETE {path} returned {exc.response.status_code}: {exc.response.text}") from exc
        except Exception as exc:
            raise GoPhishError(f"DELETE {path} failed: {exc}") from exc

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def list_campaigns(self) -> List[Dict]:
        data = self._get("/api/campaigns/")
        return data if isinstance(data, list) else []

    def create_campaign(self, payload: dict) -> Dict:
        return self._post("/api/campaigns/", payload)

    def get_campaign(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}")

    def get_campaign_results(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}/results")

    def get_campaign_summary(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}/summary")

    def complete_campaign(self, campaign_id: int) -> Dict:
        return self._get(f"/api/campaigns/{campaign_id}/complete")

    def delete_campaign(self, campaign_id: int) -> Dict:
        return self._delete(f"/api/campaigns/{campaign_id}")

    # ── Resources ────────────────────────────────────────────────────────────

    def list_templates(self) -> List[Dict]:
        data = self._get("/api/templates/")
        return data if isinstance(data, list) else []

    def list_pages(self) -> List[Dict]:
        data = self._get("/api/pages/")
        return data if isinstance(data, list) else []

    def list_smtp_profiles(self) -> List[Dict]:
        data = self._get("/api/smtp/")
        return data if isinstance(data, list) else []

    def list_groups(self) -> List[Dict]:
        data = self._get("/api/groups/")
        return data if isinstance(data, list) else []
