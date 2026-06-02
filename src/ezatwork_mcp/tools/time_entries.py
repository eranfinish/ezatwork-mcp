from ..auth import UserNotMappedError
from ..tool_helpers import get_client_for_request, not_mapped_response


def register(mcp):
    @mcp.tool(
        annotations={
            "title": "Log Time Entry",
            "readOnlyHint": False,
            "destructiveHint": False,
        }
    )
    async def log_time_entry(
        project_id: int,
        hours: float,
        description: str,
        billable: bool = True,
    ) -> dict:
        """Log a time entry (billable hours) to a project/case.

        Args:
            project_id: The project/case ID
            hours: Number of hours (e.g. 2.5)
            description: What was done
            billable: Whether these hours are billable (default true)
        """
        try:
            client = await get_client_for_request()
        except UserNotMappedError as e:
            return not_mapped_response(e)

        result = await client.post(
            "/api/timeentry",
            json={
                "projectId": project_id,
                "hours": hours,
                "description": description,
                "isBillable": billable,
            },
        )
        return {"success": True, "timeEntry": result}
