from ..auth import UserNotMappedError
from ..tool_helpers import get_client_for_request, not_mapped_response


def register(mcp):
    @mcp.tool(annotations={"title": "List Projects", "readOnlyHint": True})
    async def list_projects(status: str = "") -> dict:
        """List the user's projects (or cases/work orders — label adapts to businessMode).

        Args:
            status: Optional status filter (e.g. 'in_progress', 'completed', 'on_hold')
        """
        try:
            client = await get_client_for_request()
        except UserNotMappedError as e:
            return not_mapped_response(e)

        params = {"status": status} if status else {}
        result = await client.get("/api/projects", params=params)
        return {
            "count": len(result) if isinstance(result, list) else 0,
            "projects": result,
        }
