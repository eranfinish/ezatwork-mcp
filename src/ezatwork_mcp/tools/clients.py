from ..auth import UserNotMappedError
from ..tool_helpers import get_client_for_request, not_mapped_response


def register(mcp):
    @mcp.tool(annotations={"title": "List Clients", "readOnlyHint": True})
    async def list_clients(status: str = "all") -> dict:
        """List the user's clients/customers.

        Args:
            status: Filter by status — 'all', 'active', 'inactive', 'prospect'
        """
        try:
            client = await get_client_for_request()
        except UserNotMappedError as e:
            return not_mapped_response(e)

        params = {} if status == "all" else {"status": status}
        clients = await client.get("/api/clients", params=params)
        return {
            "count": len(clients) if isinstance(clients, list) else 0,
            "clients": clients,
        }

    @mcp.tool(
        annotations={
            "title": "Create Client",
            "readOnlyHint": False,
            "destructiveHint": False,
        }
    )
    async def create_client(
        name: str,
        email: str = "",
        phone: str = "",
        company_name: str = "",
        vat_number: str = "",
        website: str = "",
        notes: str = "",
        status: str = "active",
        default_hourly_rate: float | None = None,
        payment_terms_days: int | None = None,
    ) -> dict:
        """Create a new client/customer.

        Args:
            name: Client's name (required)
            email: Contact email
            phone: Phone number (international format, e.g. +972501234567)
            company_name: Company/business name
            vat_number: VAT / tax registration number
            website: Website URL
            notes: Free-text notes
            status: 'active', 'inactive', or 'prospect' (default 'active')
            default_hourly_rate: Default billing rate for this client
            payment_terms_days: Default invoice payment terms in days
        """
        try:
            client = await get_client_for_request()
        except UserNotMappedError as e:
            return not_mapped_response(e)

        # Map status string → backend ClientStatusId (matches the web app)
        status_map = {"active": 1, "inactive": 2, "prospect": 3}
        client_status_id = status_map.get(status.lower(), 1)

        result = await client.post(
            "/api/clients",
            json={
                "name": name,
                "companyName": company_name,
                "vatNumber": vat_number,
                "email": email,
                "phoneNumber": phone,
                "website": website,
                "notes": notes,
                "tags": "[]",
                "contacts": "[]",
                "address": {
                    "street": "",
                    "city": "",
                    "state": "",
                    "zipCode": "",
                    "country": "",
                },
                "ClientStatusId": client_status_id,
                "isLargeBusinessClient": False,
                "defaultHourlyRate": default_hourly_rate,
                "paymentTermsDays": payment_terms_days,
            },
        )
        return {"success": True, "client": result}
