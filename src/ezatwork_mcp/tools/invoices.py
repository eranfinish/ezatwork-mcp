from datetime import date, timedelta
from ..auth import UserNotMappedError
from ..tool_helpers import get_client_for_request, not_mapped_response


def register(mcp):
    @mcp.tool(
        annotations={
            "title": "Create Invoice",
            "readOnlyHint": False,
            "destructiveHint": False,
        }
    )
    async def create_invoice(
        client_id: int,
        items: list[dict],
        due_in_days: int = 30,
    ) -> dict:
        """Create a draft invoice. Currency, language, and VAT/tax rate are
        auto-detected from the user's EZ@Work profile — no need to specify.

        Args:
            client_id: The client to invoice
            items: List of line items, each {"description": str,
                   "quantity": float, "unitPrice": float}
            due_in_days: Payment terms in days (default 30)
        """
        try:
            client = await get_client_for_request()
        except UserNotMappedError as e:
            return not_mapped_response(e)

        today = date.today()
        due_date = today + timedelta(days=due_in_days)

        normalized_items = [
            {
                "description": item.get("description", ""),
                "quantity": float(item.get("quantity", 1)),
                "unitPrice": float(item.get("unitPrice", 0)),
                "total": round(
                    float(item.get("quantity", 1)) * float(item.get("unitPrice", 0)), 2
                ),
            }
            for item in items
        ]

        result = await client.post(
            "/api/invoices",
            json={
                "clientId": client_id,
                "items": normalized_items,
                "issueDate": today.isoformat(),
                "dueDate": due_date.isoformat(),
                "status": "draft",
            },
        )
        return {"success": True, "invoice": result}
