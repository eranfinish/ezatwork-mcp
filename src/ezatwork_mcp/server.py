"""EZ@Work MCP Server — Streamable HTTP with optional GoogleProvider OAuth.

Transport: streamable-http  (/mcp endpoint)
Auth:
  - If GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET + MCP_BASE_URL are set:
      FastMCP GoogleProvider OAuth proxy (for Claude Desktop / Claude.ai)
  - Otherwise:
      No server-level auth; tools authenticate via Bearer ezw_pat_... header
      (for Claude Code, Cursor, MCP Inspector — all support custom headers)
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.responses import FileResponse, Response
from .tools import clients, projects, time_entries, invoices

_STATIC_DIR = Path(__file__).parent / "static"
_FAVICON_PATH = _STATIC_DIR / "favicon.png"

load_dotenv()


def _build_auth():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    base_url = os.getenv("MCP_BASE_URL")

    if not (client_id and client_secret and base_url):
        return None

    from fastmcp.server.auth.providers.google import GoogleProvider

    return GoogleProvider(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        required_scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
    )


auth = _build_auth()

mcp = FastMCP(
    name="ezatwork",
    instructions=(
        "EZ@Work business assistant. Manages clients, projects, time tracking, "
        "and invoices for freelancers and small businesses. "
        "Currency, language, and tax rules auto-detect from your EZ@Work profile."
    ),
    auth=auth,
)

clients.register(mcp)
projects.register(mcp)
time_entries.register(mcp)
invoices.register(mcp)


# Serve the EZ@Work logo as favicon so Anthropic's Google favicon fetcher
# and tool-call UI display our brand instead of a generic globe.
@mcp.custom_route("/favicon.ico", methods=["GET"])
async def _favicon_ico(request):
    if _FAVICON_PATH.exists():
        return FileResponse(_FAVICON_PATH, media_type="image/png")
    return Response(status_code=404)


@mcp.custom_route("/favicon.png", methods=["GET"])
async def _favicon_png(request):
    if _FAVICON_PATH.exists():
        return FileResponse(_FAVICON_PATH, media_type="image/png")
    return Response(status_code=404)


def main():
    # Transport selection:
    #   PORT set       → streamable-http on 0.0.0.0:PORT/mcp (Cloud Run, k8s)
    #   PORT not set   → stdio (Claude Desktop local install, Glama scan, dev)
    port = os.getenv("PORT")
    if port:
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=int(port),
            path="/mcp",
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
