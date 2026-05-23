from ..ez_client import EzClient
from ..auth import get_token


def register(mcp):
    @mcp.tool(
        annotations={
            "title": "List Clients",
            "readOnlyHint": True,
        }
    )
    async def list_clients(status: str = "all") -> dict:
        """List the user's clients/customers.

        Args:
            status: Filter by status — 'all', 'active', 'inactive', 'prospect'
        """
        token = get_token()
        client = EzClient(token)
        params = {} if status == "all" else {"status": status}
        clients = await client.get("/api/clients", params=params)
        return {
            "count": len(clients) if isinstance(clients, list) else 0,
            "clients": clients,
        }
