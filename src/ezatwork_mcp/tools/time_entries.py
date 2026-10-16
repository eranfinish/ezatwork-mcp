from ..tool_runtime import UNTRUSTED_DATA_NOTE, pick, run_with_client
from ..validation import InvalidInput, require_number, require_positive_id, require_text

_TIME_ENTRY_FIELDS = ("id", "projectId", "hours", "description", "isBillable", "startTime")


def register(mcp):
    @mcp.tool(
        annotations={
            "title": "Log Time Entry",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        }
    )
    async def log_time_entry(
        project_id: int,
        hours: float,
        description: str,
        billable: bool = True,
    ) -> dict:
        """Log a time entry (billable hours) to a project/case. WRITES DATA to
        the user's EZ@Work account, and billable hours can end up on invoices.

        Before calling, confirm the project, hours, description and billable
        flag with the user and get their explicit go-ahead. Calling twice logs
        the hours twice. Use list_projects to find project_id.

        Args:
            project_id: The project/case ID (positive integer)
            hours: Number of hours, greater than 0 and at most 24 (e.g. 2.5)
            description: What was done (required, max 2000 characters)
            billable: Whether these hours are billable (default true)
        """
        try:
            clean_project_id = require_positive_id(project_id, "project_id")
            clean_hours = require_number(
                hours, "hours", minimum=0, exclusive_minimum=True, maximum=24
            )
            clean_description = require_text(description, "description", 2000)
        except InvalidInput as e:
            return e.to_response()

        async def action(client):
            result = await client.post(
                "/api/timeentry",
                json={
                    "projectId": clean_project_id,
                    "hours": clean_hours,
                    "description": clean_description,
                    "isBillable": bool(billable),
                },
            )
            return {
                "success": True,
                "timeEntry": pick(result, _TIME_ENTRY_FIELDS),
                "note": UNTRUSTED_DATA_NOTE,
            }

        return await run_with_client(action)
