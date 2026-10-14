"""Tests for Dynamic Client Registration redirect URI restrictions."""
import pytest
from fastmcp import FastMCP
from starlette.testclient import TestClient
from src.ezatwork_mcp import server


@pytest.fixture
def oauth_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    monkeypatch.setenv("MCP_BASE_URL", "https://mcp.example.test")
    monkeypatch.setenv("FASTMCP_HOME", str(tmp_path))
    monkeypatch.delenv("MCP_ALLOWED_REDIRECT_URIS", raising=False)


def _register(redirect_uri: str) -> int:
    app = FastMCP(name="test", auth=server._build_auth()).http_app(path="/mcp")
    with TestClient(app, base_url="https://mcp.example.test") as client:
        response = client.post(
            "/register",
            json={"client_name": "probe", "redirect_uris": [redirect_uri]},
        )
    return response.status_code


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://attacker-alpha.example.com/cb",
        "https://claude.ai.evil.example/api/mcp/auth_callback",
        "https://claude.ai/api/mcp/auth_callback/../../steal",
        "http://localhost@evil.example/cb",
    ],
)
def test_register_rejects_foreign_redirect_uri(oauth_env, redirect_uri):
    assert _register(redirect_uri) == 400


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://claude.ai/api/mcp/auth_callback",
        "https://claude.com/api/mcp/auth_callback",
        "http://localhost:51234/callback",
        "http://127.0.0.1:8080/oauth/callback",
    ],
)
def test_register_accepts_known_client_redirect_uri(oauth_env, redirect_uri):
    assert _register(redirect_uri) == 201


def test_allowlist_can_be_overridden_from_env(oauth_env, monkeypatch):
    monkeypatch.setenv(
        "MCP_ALLOWED_REDIRECT_URIS", " https://client.example/cb , http://localhost:* "
    )
    assert server._allowed_redirect_uris() == [
        "https://client.example/cb",
        "http://localhost:*",
    ]
    assert _register("https://client.example/cb") == 201
    assert _register("https://claude.ai/api/mcp/auth_callback") == 400


def test_empty_override_keeps_default_allowlist(oauth_env, monkeypatch):
    monkeypatch.setenv("MCP_ALLOWED_REDIRECT_URIS", " , ")
    assert server._allowed_redirect_uris() == server.DEFAULT_ALLOWED_REDIRECT_URIS
