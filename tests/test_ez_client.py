"""Tests for EzClient."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.ezatwork_mcp.ez_client import EzClient


def test_rejects_missing_token():
    with pytest.raises(ValueError, match="Invalid API token"):
        EzClient("")


def test_rejects_wrong_prefix():
    with pytest.raises(ValueError, match="Invalid API token"):
        EzClient("sk_live_something")


def test_accepts_valid_token():
    client = EzClient("ezw_pat_test123")
    assert client._token == "ezw_pat_test123"


def test_bearer_header_set():
    client = EzClient("ezw_pat_abc")
    assert client._headers["Authorization"] == "Bearer ezw_pat_abc"
    assert client._headers["User-Agent"] == "ezatwork-mcp/0.1.0"


@pytest.mark.asyncio
async def test_get_current_user_calls_me():
    client = EzClient("ezw_pat_test")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "id": 1,
        "email": "test@example.com",
        "preferredCurrency": "USD",
        "preferredLanguage": "en",
        "businessMode": "freelance",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_async_client = AsyncMock()
        mock_async_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_async_client

        result = await client.get_current_user()

    mock_async_client.get.assert_called_once()
    call_args = mock_async_client.get.call_args
    assert "/api/users/me" in call_args[0][0]
    assert result["preferredCurrency"] == "USD"
