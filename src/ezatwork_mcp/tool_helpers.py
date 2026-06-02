"""Shared helpers for MCP tools.

get_client_for_request() is the single entry-point every tool calls.
It detects which auth mode is active and returns a ready EzClient.
"""
from fastmcp.server.dependencies import get_access_token
from .auth import get_ez_user_from_oauth, get_token, UserNotMappedError
from .ez_client import EzClient


async def get_client_for_request() -> EzClient:
    """Return an EzClient authenticated for the current request.

    OAuth mode  (GOOGLE_CLIENT_ID set, Claude Desktop / Claude.ai):
        Reads Google identity from FastMCP's access token context,
        looks up the EZ@Work user via master token.

    API token mode  (no OAuth, Claude Code / Cursor / MCP Inspector):
        Reads Bearer ezw_pat_... from the Authorization HTTP header.
    """
    access_token = get_access_token()
    if access_token is not None:
        # OAuth path — get the EZ@Work user for this Google identity
        user = await get_ez_user_from_oauth()
        return EzClient(
            impersonate_user_id=user["id"],
            verified_email=user["email"],
        )

    # API token path
    token = get_token()
    return EzClient(api_token=token)


def not_mapped_response(e: UserNotMappedError) -> dict:
    """Standard error response when a Google account has no EZ@Work user."""
    return {
        "error": "account_not_linked",
        "message": str(e),
        "action_required": "Visit the link below to connect your Google account to EZ@Work",
        "link_url": e.link_url,
    }
