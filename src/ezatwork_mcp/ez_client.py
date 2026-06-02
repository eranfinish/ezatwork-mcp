"""HTTP client wrapper around EZ@Work API.

Two modes:
  - API token mode: used when no OAuth is configured (Claude Code / Cursor / local).
    The client authenticates directly with the user's own API token.

  - Impersonation mode: used with GoogleProvider OAuth (Claude Desktop / Claude.ai).
    The client authenticates with a master token and impersonates a specific user.
    Security: the EZ@Work API verifies that X-Impersonate-UserId email matches
    X-Impersonate-Verified-Email before allowing the request.
"""
import os
import httpx
from typing import Any


class EzClient:
    """Async HTTP client for the EZ@Work API, bound to one user's identity."""

    def __init__(
        self,
        *,
        api_token: str | None = None,
        impersonate_user_id: int | None = None,
        verified_email: str | None = None,
    ):
        api_base = os.getenv("EZ_API_BASE", "https://api.ezatwork.com")
        self._base = api_base

        if api_token:
            if not api_token.startswith("ezw_pat_"):
                raise ValueError("Invalid API token format — must start with ezw_pat_")
            self._headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "User-Agent": "ezatwork-mcp/0.2.0",
            }
        elif impersonate_user_id is not None and verified_email:
            master_token = os.getenv("EZ_MCP_MASTER_TOKEN")
            if not master_token:
                raise RuntimeError("EZ_MCP_MASTER_TOKEN not configured")
            self._headers = {
                "Authorization": f"Bearer {master_token}",
                "X-Impersonate-UserId": str(impersonate_user_id),
                "X-Impersonate-Verified-Email": verified_email,
                "Content-Type": "application/json",
                "User-Agent": "ezatwork-mcp/0.2.0",
            }
        else:
            raise ValueError(
                "EzClient requires either api_token or both impersonate_user_id+verified_email"
            )

    async def get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self._base}{path}", headers=self._headers, params=params
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json: dict) -> Any:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._base}{path}", headers=self._headers, json=json
            )
            resp.raise_for_status()
            return resp.json()

    async def get_current_user(self) -> dict:
        """Returns user profile (preferredCurrency, preferredLanguage, businessMode…)."""
        return await self.get("/api/users/me")
