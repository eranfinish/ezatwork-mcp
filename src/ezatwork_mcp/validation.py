"""Argument checks that run before any backend call.

A failed check raises InvalidInput; the tool turns it into
{"error": "invalid_input", "message": ..., "field": ...} so the agent can fix
the call or ask the user, instead of the backend rejecting (or worse,
accepting) a bad value.
"""
import math
import re
from typing import Any

from .tool_runtime import invalid_input

MAX_LIST_LIMIT = 200
DEFAULT_LIST_LIMIT = 50

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvalidInput(Exception):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.message = message
        self.field = field

    def to_response(self) -> dict:
        return invalid_input(self.message, self.field)


def require_positive_id(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InvalidInput(f"{field} must be a positive integer ID.", field)
    return value


def require_text(value: Any, field: str, max_len: int, *, required: bool = True) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise InvalidInput(f"{field} must be text.", field)
    text = value.strip()
    if required and not text:
        raise InvalidInput(f"{field} must not be empty.", field)
    if len(text) > max_len:
        raise InvalidInput(f"{field} must be at most {max_len} characters.", field)
    return text


def require_number(
    value: Any,
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidInput(f"{field} must be a number.", field)
    number = float(value)
    if not math.isfinite(number):
        raise InvalidInput(f"{field} must be a finite number.", field)
    if minimum is not None:
        if exclusive_minimum and number <= minimum:
            raise InvalidInput(f"{field} must be greater than {_fmt(minimum)}.", field)
        if not exclusive_minimum and number < minimum:
            raise InvalidInput(f"{field} must be at least {_fmt(minimum)}.", field)
    if maximum is not None and number > maximum:
        raise InvalidInput(f"{field} must be at most {_fmt(maximum)}.", field)
    return number


def require_int_range(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidInput(f"{field} must be a whole number.", field)
    if value < minimum or value > maximum:
        raise InvalidInput(f"{field} must be between {minimum} and {maximum}.", field)
    return value


def require_email(value: str, field: str = "email") -> str:
    email = require_text(value, field, 254, required=False)
    if email and not _EMAIL_RE.match(email):
        raise InvalidInput(f"{field} is not a valid email address.", field)
    return email


def require_choice(value: Any, field: str, allowed: tuple[str, ...]) -> str:
    choice = value.strip().lower() if isinstance(value, str) else ""
    if choice not in allowed:
        raise InvalidInput(f"{field} must be one of: {', '.join(allowed)}.", field)
    return choice


def require_limit(value: Any) -> int:
    return require_int_range(value, "limit", 1, MAX_LIST_LIMIT)


def _fmt(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else str(number)
