from ..ez_client import EzClient
from ..auth import get_token


def register(mcp):
    @mcp.tool(
        annotations={
            "title": "List Projects",
            "readOnlyHint": True,
        }
    )
    async def list_projects(status: str = "") -> dict:
        """List the user's projects (or cases/work orders, depending on
        business type — labels adapt automatically via businessMode).

        Args:
            status: Optional status filter (e.g. 'in_progress', 'completed', 'on_hold')
        """
        token = get_token()
        client = EzClient(token)
        params = {"status": status} if status else {}
        projects = await client.get("/api/projects", params=params)
        return {
            "count": len(projects) if isinstance(projects, list) else 0,
            "projects": projects,
        }
