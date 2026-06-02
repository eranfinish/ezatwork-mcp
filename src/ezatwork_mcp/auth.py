"""Authentication helpers — supports both OAuth (GoogleProvider) and API token paths.

OAuth path (Claude Desktop / Claude.ai):
  get_access_token() returns an AccessToken with Google email claim.
  get_ez_user_from_oauth() maps that email → EZ@Work user via master token.

API token path (Claude Code / Cursor / MCP Inspector):
  No FastMCP auth configured; Bearer ezw_pat_... is in the Authorization header.
  get_token() extracts it directly from HTTP headers.
"""
import os
import httpx
from fastmcp.server.dependencies import get_http_headers, get_access_token


class UserNotMappedError(Exception):
    """Google identity is authenticated but no matching EZ@Work account exists."""

    def __init__(self, email: str, link_url: str):
        self.email = email
        self.link_url = link_url
        super().__init__(
            f"No EZ@Work account linked to {email}. "
            f"Connect your account at: {link_url}"
        )


async def get_ez_user_from_oauth() -> dict:
    """Return the EZ@Work user for the current Google-authenticated request.

    Uses the master token to look up the user by their Google email address.
    Raises UserNotMappedError if no EZ@Work account matches the Google email.

    Returned dict: id, email, preferredCurrency, preferredLanguage,
                   businessMode, businessModeCountry, fullName
    """
    access_token = get_access_token()
    if access_token is None:
        raise ValueError("Not authenticated via OAuth")

    google_email = access_token.claims.get("email")
    if not google_email:
        raise ValueError("OAuth token has no email claim — openid+email scopes required")

    api_base = os.getenv("EZ_API_BASE", "https://api.ezatwork.com")
    master_token = os.getenv("EZ_MCP_MASTER_TOKEN")
    if not master_token:
        raise RuntimeError(
            "EZ_MCP_MASTER_TOKEN is not configured. "
            "Create a master API token at https://app.ezatwork.com/settings/api-tokens "
            "and set EZ_MCP_MASTER_TOKEN in environment."
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{api_base}/api/internal/users/by-email",
            params={"email": google_email},
            headers={"Authorization": f"Bearer {master_token}"},
        )

        if resp.status_code == 404:
            data = resp.json()
            raise UserNotMappedError(
                email=google_email,
                link_url=data.get(
                    "link_url",
                    "https://app.ezatwork.com/settings/connect-google",
                ),
            )

        resp.raise_for_status()
        return resp.json()


def get_token() -> str:
    """Extract the per-request API token from the HTTP Authorization header.

    Used in the API token path (no OAuth configured).
    """
    headers = get_http_headers()
    auth_header = headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise ValueError(
            "Missing API token. Set Authorization: Bearer ezw_pat_... "
            "Get your token at https://app.ezatwork.com/settings/api-tokens"
        )
    return auth_header[len("bearer "):].strip()
