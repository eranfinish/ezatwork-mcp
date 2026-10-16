"""Backend / auth failures become small structured dicts, never exceptions."""
from unittest.mock import AsyncMock

import httpx
import pytest

from ezatwork_mcp import tool_runtime
from ezatwork_mcp.auth import UserNotMappedError
from tests.conftest import http_error

pytestmark = pytest.mark.asyncio

INVOICE_ARGS = {"client_id": 1, "items": [{"description": "x", "quantity": 1, "unitPrice": 1}]}


async def test_plan_limit_402_passes_code_and_message(backend, call):
    backend.post.side_effect = http_error(
        402,
        {
            "code": "PLAN_LIMIT_REACHED",
            "message": "You have reached the maximum number of invoices for your plan this month",
            "limitType": "invoices",
            "currentCount": 5,
            "maxAllowed": 5,
            "currentPlan": 0,
            "upgradeUrl": "/pricing",
        },
    )

    result = await call("create_invoice", INVOICE_ARGS)

    assert result["error"] == "plan_limit_reached"
    assert result["status"] == 402
    assert result["code"] == "PLAN_LIMIT_REACHED"
    assert result["message"].startswith("You have reached the maximum number of invoices")
    assert result["limitType"] == "invoices"
    assert result["currentCount"] == 5
    assert result["maxAllowed"] == 5
    assert result["upgradeUrl"] == "/pricing"
    assert "hint" in result


async def test_bad_request_drops_exception_details(backend, call):
    backend.post.side_effect = http_error(
        400,
        {
            "message": "Failed to add time entry",
            "error": "Npgsql.PostgresException: 23503: insert violates foreign key",
            "details": "   at EZatWork.Services.TimeEntryService.Add() in /src/x.cs:line 42",
        },
    )

    result = await call("log_time_entry", {"project_id": 1, "hours": 1, "description": "x"})

    assert result == {"error": "bad_request", "status": 400, "message": "Failed to add time entry"}


async def test_plain_text_body_is_not_forwarded(backend, call):
    backend.get.side_effect = http_error(
        400, text="System.NullReferenceException: Object reference not set\n   at Foo.Bar()"
    )

    result = await call("list_clients")

    assert result["error"] == "bad_request"
    assert result["status"] == 400
    assert "NullReference" not in result["message"]


async def test_validation_problem_details_lists_fields(backend, call):
    backend.post.side_effect = http_error(
        400,
        {
            "title": "One or more validation errors occurred.",
            "status": 400,
            "errors": {"$.status": ["The JSON value could not be converted."]},
        },
    )

    result = await call("create_invoice", INVOICE_ARGS)

    assert result["message"] == "One or more validation errors occurred."
    assert result["fields"] == {"$.status": "The JSON value could not be converted."}


@pytest.mark.parametrize(
    "status, error",
    [(401, "unauthorized"), (403, "forbidden"), (404, "not_found"), (429, "rate_limited")],
)
async def test_client_errors_get_friendly_defaults(backend, call, status, error):
    backend.get.side_effect = http_error(status, text="")

    result = await call("list_projects")

    assert result["error"] == error
    assert result["status"] == status
    assert result["message"]


async def test_server_error_hides_backend_message(backend, call):
    backend.get.side_effect = http_error(500, {"message": "Connection string Host=db;Password=x"})

    result = await call("list_clients")

    assert result["error"] == "backend_error"
    assert result["status"] == 500
    assert "Password" not in result["message"]


async def test_duplicate_check_failure_is_mapped_and_nothing_is_created(backend, call):
    backend.get.side_effect = http_error(401, text="")

    result = await call("create_client", {"name": "Dana"})

    assert result["error"] == "unauthorized"
    backend.post.assert_not_awaited()


async def test_network_error_is_mapped(backend, call):
    backend.get.side_effect = httpx.ConnectError("refused")

    result = await call("list_clients")

    assert result["error"] == "backend_unreachable"


async def test_unexpected_exception_is_mapped(backend, call):
    backend.get.side_effect = KeyError("boom")

    result = await call("list_clients")

    assert result["error"] == "internal_error"
    assert "KeyError" not in result["message"]


async def test_missing_token_is_mapped(monkeypatch, call):
    monkeypatch.setattr(
        tool_runtime,
        "get_client_for_request",
        AsyncMock(side_effect=ValueError("Missing API token. Set Authorization: Bearer ezw_pat_...")),
    )

    result = await call("list_clients")

    assert result["error"] == "authentication_required"
    assert "Missing API token" in result["message"]


async def test_unlinked_google_account_is_mapped(monkeypatch, call):
    monkeypatch.setattr(
        tool_runtime,
        "get_client_for_request",
        AsyncMock(side_effect=UserNotMappedError("a@example.test", "https://app.example/link")),
    )

    result = await call("list_projects")

    assert result["error"] == "account_not_linked"
    assert result["link_url"] == "https://app.example/link"
