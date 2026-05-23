"""HTTP client wrapper around EZ@Work API."""
import os
import httpx
from typing import Any
from datetime import date, timedelta

API_BASE = os.getenv("EZ_API_BASE", "https://api.ezat.work")


class EzClient:
    """Thin async HTTP client bound to one user's API token."""

    def __init__(self, api_token: str):
        if not api_token or not api_token.startswith("ezw_pat_"):
            raise ValueError("Invalid API token format")
        self._token = api_token
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "ezatwork-mcp/0.1.0",
        }

    async def get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{API_BASE}{path}", headers=self._headers, params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json: dict) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{API_BASE}{path}", headers=self._headers, json=json
            )
            resp.raise_for_status()
            return resp.json()

    async def get_current_user(self) -> dict:
        """Returns user profile incl. preferredCurrency, preferredLanguage,
        businessMode, businessModeCountry from GET /api/users/me."""
        return await self.get("/api/users/me")
