"""EZ@Work MCP Server — Streamable HTTP transport.

Tested with: fastmcp>=2.0.0
Transport:   streamable-http (not stdio, not legacy SSE)
Auth:        Bearer token per-request via Authorization header
             fastmcp.server.dependencies.get_http_headers()
"""
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from .tools import clients, projects, time_entries, invoices

load_dotenv()

mcp = FastMCP(
    name="ezatwork",
    instructions=(
        "EZ@Work business assistant. Manages clients, projects, time tracking, "
        "and invoices. Every request requires a valid API token "
        "(Authorization: Bearer ezw_pat_...) from https://app.ezatwork.com/settings/api-tokens"
    ),
)

clients.register(mcp)
projects.register(mcp)
time_entries.register(mcp)
invoices.register(mcp)


def main():
    port = int(os.getenv("PORT", "8080"))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        path="/mcp",
    )


if __name__ == "__main__":
    main()
