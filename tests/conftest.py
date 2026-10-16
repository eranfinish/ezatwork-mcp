"""Shared fixtures: an in-memory MCP server with the backend client mocked.

No test here touches the network. `fake_backend` replaces the EzClient that
get_client_for_request() would build, so `backend.get` / `backend.post` are
AsyncMocks the test can program and inspect.
"""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastmcp import Client, FastMCP

from ezatwork_mcp import tool_runtime
from ezatwork_mcp.tools import clients, invoices, projects, time_entries


@pytest.fixture
def backend(monkeypatch):
    fake = MagicMock()
    fake.get = AsyncMock(return_value=[])
    fake.post = AsyncMock(return_value={})
    monkeypatch.setattr(
        tool_runtime, "get_client_for_request", AsyncMock(return_value=fake)
    )
    return fake


@pytest.fixture
def mcp_server():
    server = FastMCP(name="test")
    for module in (clients, projects, time_entries, invoices):
        module.register(server)
    return server


@pytest.fixture
def call(mcp_server):
    async def _call(tool: str, args: dict | None = None) -> dict:
        async with Client(mcp_server) as client:
            result = await client.call_tool(tool, args or {})
        return result.structured_content

    return _call


def http_error(status: int, body=None, text: str | None = None) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.example.test/api/x")
    if text is not None:
        response = httpx.Response(status, text=text, request=request)
    else:
        response = httpx.Response(status, json=body, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)
