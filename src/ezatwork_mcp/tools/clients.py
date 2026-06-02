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
