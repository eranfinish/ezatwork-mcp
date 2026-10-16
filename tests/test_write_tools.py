"""Write tools: input validation, duplicate detection, trimmed results."""
import pytest

pytestmark = pytest.mark.asyncio

GOOD_ITEM = {"description": "Consulting", "quantity": 2, "unitPrice": 100}


# --- log_time_entry -------------------------------------------------------

@pytest.mark.parametrize(
    "args, field",
    [
        ({"project_id": 1, "hours": 0, "description": "x"}, "hours"),
        ({"project_id": 1, "hours": -1, "description": "x"}, "hours"),
        ({"project_id": 1, "hours": 24.5, "description": "x"}, "hours"),
        ({"project_id": 1, "hours": 1, "description": "   "}, "description"),
        ({"project_id": 1, "hours": 1, "description": "x" * 2001}, "description"),
        ({"project_id": 0, "hours": 1, "description": "x"}, "project_id"),
        ({"project_id": -5, "hours": 1, "description": "x"}, "project_id"),
    ],
)
async def test_log_time_entry_rejects_invalid_input(backend, call, args, field):
    result = await call("log_time_entry", args)

    assert result["error"] == "invalid_input"
    assert result["field"] == field
    assert result["message"]
    backend.post.assert_not_awaited()


async def test_log_time_entry_posts_and_trims_result(backend, call):
    backend.post.return_value = {
        "id": 99,
        "projectId": 3,
        "hours": 24,
        "description": "Wrote the report",
        "isBillable": True,
        "user": {"email": "owner@example.test", "passwordHash": "secret"},
        "project": {"name": "P", "description": "private"},
    }

    result = await call(
        "log_time_entry", {"project_id": 3, "hours": 24, "description": "  Wrote the report "}
    )

    backend.post.assert_awaited_once_with(
        "/api/timeentry",
        json={"projectId": 3, "hours": 24.0, "description": "Wrote the report", "isBillable": True},
    )
    assert result["success"] is True
    assert result["timeEntry"]["id"] == 99
    assert "user" not in result["timeEntry"]
    assert "project" not in result["timeEntry"]


# --- create_invoice -------------------------------------------------------

@pytest.mark.parametrize(
    "args, field",
    [
        ({"client_id": 0, "items": [GOOD_ITEM]}, "client_id"),
        ({"client_id": 1, "items": []}, "items"),
        ({"client_id": 1, "items": [GOOD_ITEM] * 51}, "items"),
        ({"client_id": 1, "items": [{**GOOD_ITEM, "description": ""}]}, "items[0].description"),
        ({"client_id": 1, "items": [{**GOOD_ITEM, "description": "d" * 501}]}, "items[0].description"),
        ({"client_id": 1, "items": [GOOD_ITEM, {**GOOD_ITEM, "quantity": 0}]}, "items[1].quantity"),
        ({"client_id": 1, "items": [{**GOOD_ITEM, "unitPrice": -1}]}, "items[0].unitPrice"),
        ({"client_id": 1, "items": [{"description": "x", "quantity": 1}]}, "items[0].unitPrice"),
        ({"client_id": 1, "items": [{**GOOD_ITEM, "quantity": "two"}]}, "items[0].quantity"),
        ({"client_id": 1, "items": [GOOD_ITEM], "due_in_days": -1}, "due_in_days"),
        ({"client_id": 1, "items": [GOOD_ITEM], "due_in_days": 366}, "due_in_days"),
    ],
)
async def test_create_invoice_rejects_invalid_input(backend, call, args, field):
    result = await call("create_invoice", args)

    assert result["error"] == "invalid_input"
    assert result["field"] == field
    backend.post.assert_not_awaited()


async def test_create_invoice_accepts_boundaries_and_trims_result(backend, call):
    backend.post.return_value = {
        "id": 5,
        "invoiceNumber": "INV-0005",
        "clientId": 1,
        "total": 0,
        "client": {"notes": "private notes", "vatNumber": "IL1"},
        "items": [],
    }
    items = [{"description": "Free item", "unitPrice": 0}] + [GOOD_ITEM] * 49

    result = await call("create_invoice", {"client_id": 1, "items": items, "due_in_days": 0})

    assert result["success"] is True
    assert result["invoice"] == {"id": 5, "invoiceNumber": "INV-0005", "clientId": 1, "total": 0}
    payload = backend.post.await_args.kwargs["json"]
    assert len(payload["items"]) == 50
    assert payload["items"][0] == {
        "description": "Free item", "quantity": 1.0, "unitPrice": 0.0, "total": 0.0,
    }
    assert payload["issueDate"] == payload["dueDate"]


async def test_create_invoice_sends_numeric_draft_status(backend, call):
    backend.post.return_value = {"id": 1}

    await call("create_invoice", {"client_id": 3, "items": [GOOD_ITEM], "due_in_days": 14})

    path = backend.post.await_args.args[0]
    payload = backend.post.await_args.kwargs["json"]
    assert path == "/api/invoices"
    # InvoiceStatus.Draft == 1; the API has no string enum converter.
    assert payload["status"] == 1
    assert payload["clientId"] == 3
    assert payload["items"] == [
        {"description": "Consulting", "quantity": 2.0, "unitPrice": 100.0, "total": 200.0}
    ]


# --- create_client --------------------------------------------------------

@pytest.mark.parametrize(
    "args, field",
    [
        ({"name": "  "}, "name"),
        ({"name": "n" * 201}, "name"),
        ({"name": "Dana", "email": "not-an-email"}, "email"),
        ({"name": "Dana", "email": "a@b"}, "email"),
        ({"name": "Dana", "status": "vip"}, "status"),
        ({"name": "Dana", "default_hourly_rate": -0.01}, "default_hourly_rate"),
        ({"name": "Dana", "payment_terms_days": -1}, "payment_terms_days"),
        ({"name": "Dana", "payment_terms_days": 366}, "payment_terms_days"),
    ],
)
async def test_create_client_rejects_invalid_input(backend, call, args, field):
    result = await call("create_client", args)

    assert result["error"] == "invalid_input"
    assert result["field"] == field
    backend.get.assert_not_awaited()
    backend.post.assert_not_awaited()


async def test_create_client_unknown_status_is_rejected_not_defaulted(backend, call):
    result = await call("create_client", {"name": "Dana", "status": "suspended"})

    assert result["error"] == "invalid_input"
    assert "active, inactive, prospect" in result["message"]


async def test_create_client_flags_duplicate_email(backend, call):
    backend.get.return_value = [
        {"id": 4, "name": "Dana L.", "companyName": "", "email": "Dana@Example.test",
         "clientStatusId": 1, "notes": "private", "phoneNumber": "+1555"},
    ]

    result = await call("create_client", {"name": "Dana Levi", "email": " dana@example.TEST"})

    assert result["error"] == "possible_duplicate"
    assert result["matched_on"] == "email"
    assert result["existing"] == {
        "id": 4, "name": "Dana L.", "companyName": "", "status": "active",
        "email": "Dana@Example.test",
    }
    backend.post.assert_not_awaited()


async def test_create_client_flags_duplicate_name_when_no_email(backend, call):
    backend.get.return_value = [
        {"id": 8, "name": "  Dana   LEVI ", "email": "other@example.test", "clientStatusId": 2},
    ]

    result = await call("create_client", {"name": "dana levi"})

    assert result["error"] == "possible_duplicate"
    assert result["matched_on"] == "name"
    assert result["existing"]["id"] == 8
    backend.post.assert_not_awaited()


async def test_create_client_same_name_different_email_is_not_duplicate(backend, call):
    backend.get.return_value = [{"id": 8, "name": "Dana Levi", "email": "a@example.test"}]
    backend.post.return_value = {"id": 9, "name": "Dana Levi", "email": "b@example.test",
                                 "clientStatusId": 1}

    result = await call("create_client", {"name": "Dana Levi", "email": "b@example.test"})

    assert result["success"] is True
    backend.post.assert_awaited_once()


async def test_create_client_allow_duplicate_skips_check(backend, call):
    backend.post.return_value = {"id": 9, "name": "Dana", "clientStatusId": 3}

    result = await call(
        "create_client", {"name": "Dana", "status": "Prospect", "allow_duplicate": True}
    )

    backend.get.assert_not_awaited()
    assert result["success"] is True
    assert backend.post.await_args.kwargs["json"]["ClientStatusId"] == 3


async def test_create_client_posts_clean_payload_and_trims_result(backend, call):
    backend.get.return_value = []
    backend.post.return_value = {
        "id": 12, "name": "Dana Levi", "companyName": "Levi Ltd", "email": "dana@example.test",
        "clientStatusId": 1, "notes": "VIP", "vatNumber": "IL9", "defaultHourlyRate": 0,
    }

    result = await call(
        "create_client",
        {"name": " Dana Levi ", "email": "dana@example.test", "company_name": "Levi Ltd",
         "notes": "VIP", "default_hourly_rate": 0, "payment_terms_days": 0},
    )

    payload = backend.post.await_args.kwargs["json"]
    assert payload["name"] == "Dana Levi"
    assert payload["ClientStatusId"] == 1
    assert payload["defaultHourlyRate"] == 0
    assert payload["paymentTermsDays"] == 0
    assert result["client"] == {
        "id": 12, "name": "Dana Levi", "companyName": "Levi Ltd", "status": "active",
        "email": "dana@example.test", "defaultHourlyRate": 0,
    }
