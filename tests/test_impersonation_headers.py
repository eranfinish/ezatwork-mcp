"""Impersonation must carry the Google token the user signed in with."""
import pytest
from src.ezatwork_mcp.ez_client import EzClient


@pytest.fixture(autouse=True)
def master_token(monkeypatch):
    monkeypatch.setenv("EZ_MCP_MASTER_TOKEN", "ezw_pat_master")


def test_impersonation_forwards_the_google_token():
    client = EzClient(impersonate_user_id=7, verified_email="a@example.com", google_token="ya29.abc")
    assert client._headers["X-Impersonate-Google-Token"] == "ya29.abc"
    assert client._headers["X-Impersonate-UserId"] == "7"
    # Still sent for API versions that predate the token check.
    assert client._headers["X-Impersonate-Verified-Email"] == "a@example.com"


def test_impersonation_without_a_google_token_is_refused():
    with pytest.raises(ValueError):
        EzClient(impersonate_user_id=7, verified_email="a@example.com")
