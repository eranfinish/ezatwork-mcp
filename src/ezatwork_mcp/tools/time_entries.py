from datetime import date, datetime, time, timedelta, timezone

from ..tool_runtime import UNTRUSTED_DATA_NOTE, pick, run_with_client
from ..validation import InvalidInput, require_number, require_positive_id, require_text

_TIME_ENTRY_FIELDS = ("id", "projectId", "hours", "description", "isBillable", "startTime")

# How far from today a work date may be, either way.
MAX_DATE_DISTANCE = timedelta(days=365)
# Start time used for a past or future work date (only the day matters to reports).
_DEFAULT_START = time(9, 0, tzinfo=timezone.utc)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def start_time_for(work_date: str) -> str:
    """ISO-8601 UTC start time for the entry.

    The API's StartTime is a non-nullable DateTime with no default: an entry
    posted without it is stored as 0001-01-01 and drops out of every
    date-range view and report.
    """
    now = _utcnow().replace(microsecond=0)
    today = now.date()
    raw = (work_date or "").strip()
    if not raw:
        day = today
    else:
        try:
            if len(raw) != 10:
                raise ValueError
            day = date.fromisoformat(raw)
        except ValueError:
            raise InvalidInput("date must be an ISO date, YYYY-MM-DD.", "date") from None
        if abs(day - today) > MAX_DATE_DISTANCE:
            raise InvalidInput(
                "date must be within one year of today.", "date"
            )
    start = now if day == today else datetime.combine(day, _DEFAULT_START)
    return start.isoformat().replace("+00:00", "Z")


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
        date: str = "",
    ) -> dict:
        """Log a time entry (billable hours) to a project/case. WRITES DATA to
        the user's EZ@Work account, and billable hours can end up on invoices.

        Before calling, confirm the project, hours, description and billable
        flag with the user and get their explicit go-ahead. Calling twice logs
        the hours twice. Use list_projects to find project_id.

        Pass the day the work was done as `date`. If the user says "yesterday"
        or "last Monday", compute the calendar date (or ask if unsure) and
        confirm it with them; leaving it empty logs the hours for today.

        Args:
            project_id: The project/case ID (positive integer)
            hours: Number of hours, greater than 0 and at most 24 (e.g. 2.5)
            description: What was done (required, max 2000 characters)
            billable: Whether these hours are billable (default true)
            date: Day the work was done, YYYY-MM-DD, within one year of today
                  (default: today, UTC)
        """
        try:
            clean_project_id = require_positive_id(project_id, "project_id")
            clean_hours = require_number(
                hours, "hours", minimum=0, exclusive_minimum=True, maximum=24
            )
            clean_description = require_text(description, "description", 2000)
            start_time = start_time_for(date)
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
                    "startTime": start_time,
                },
            )
            return {
                "success": True,
                "timeEntry": pick(result, _TIME_ENTRY_FIELDS),
                "note": UNTRUSTED_DATA_NOTE,
            }

        return await run_with_client(action)
