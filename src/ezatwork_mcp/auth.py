"""Extract the per-request API token from the HTTP Authorization header."""
from fastmcp.server.dependencies import get_http_headers


def get_token() -> str:
    """
    Reads the Bearer token from the Authorization header.
    FastMCP (streamable-http transport) injects request headers via
    get_http_headers() — no Context parameter needed.

    Token format: ezw_pat_...
    Generate at: https://app.ezatwork.com/settings/api-tokens
    """
    headers = get_http_headers()
    auth_header = headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise ValueError(
            "Missing API token. Set Authorization: Bearer ezw_pat_... "
            "Get your token at https://app.ezatwork.com/settings/api-tokens"
        )
    return auth_header[len("bearer "):].strip()
