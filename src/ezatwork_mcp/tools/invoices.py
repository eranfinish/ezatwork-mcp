from datetime import date, timedelta
from typing import Any

from ..tool_runtime import UNTRUSTED_DATA_NOTE, pick, run_with_client
from ..validation import (
    InvalidInput,
    require_int_range,
    require_number,
    require_positive_id,
    require_text,
)

MAX_ITEMS = 50

_INVOICE_FIELDS = (
    "id",
    "invoiceNumber",
    "clientId",
    "status",
    "issueDate",
    "dueDate",
    "subtotal",
    "taxAmount",
    "total",
    "currency",
)


def _validate_items(items: Any) -> list[dict]:
    if not isinstance(items, list) or not items:
        raise InvalidInput("items must contain at least one line item.", "items")
    if len(items) > MAX_ITEMS:
        raise InvalidInput(f"items can contain at most {MAX_ITEMS} line items.", "items")

    normalized = []
    for index, item in enumerate(items):
        where = f"items[{index}]"
        if not isinstance(item, dict):
            raise InvalidInput(
                f'{where} must be an object {{"description", "quantity", "unitPrice"}}.',
                where,
            )
        description = require_text(item.get("description"), f"{where}.description", 500)
        quantity = require_number(
            item.get("quantity", 1), f"{where}.quantity", minimum=0, exclusive_minimum=True
        )
        if "unitPrice" not in item:
            raise InvalidInput(f"{where}.unitPrice is required.", f"{where}.unitPrice")
        unit_price = require_number(item["unitPrice"], f"{where}.unitPrice", minimum=0)
        normalized.append(
            {
                "description": description,
                "quantity": quantity,
                "unitPrice": unit_price,
                "total": round(quantity * unit_price, 2),
            }
        )
    return normalized


def register(mcp):
    @mcp.tool(
        annotations={
            "title": "Create Invoice",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    async def create_invoice(
        client_id: int,
        items: list[dict],
        due_in_days: int = 30,
    ) -> dict:
        """Create a draft invoice. WRITES DATA to the user's EZ@Work account.

        Before calling, show the user the client, every line item (description,
        quantity, unit price) and the due date, and get their explicit
        confirmation. Calling twice creates two invoices. The invoice is created
        as a draft and is not sent to the client. Currency, language, and
        VAT/tax rate are auto-detected from the user's EZ@Work profile — no
        need to specify. Use list_clients to find client_id.

        Args:
            client_id: The client to invoice (positive integer)
            items: 1-50 line items, each {"description": str (max 500 chars),
                   "quantity": number > 0 (default 1), "unitPrice": number >= 0}
            due_in_days: Payment terms in days, 0-365 (default 30)
        """
        try:
            clean_client_id = require_positive_id(client_id, "client_id")
            normalized_items = _validate_items(items)
            days = require_int_range(due_in_days, "due_in_days", 0, 365)
        except InvalidInput as e:
            return e.to_response()

        today = date.today()
        due_date = today + timedelta(days=days)

        async def action(client):
            result = await client.post(
                "/api/invoices",
                json={
                    "clientId": clean_client_id,
                    "items": normalized_items,
                    "issueDate": today.isoformat(),
                    "dueDate": due_date.isoformat(),
                    "status": "draft",
                },
            )
            return {
                "success": True,
                "invoice": pick(result, _INVOICE_FIELDS),
                "note": UNTRUSTED_DATA_NOTE,
            }

        return await run_with_client(action)
