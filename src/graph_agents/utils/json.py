import functools
import json
from typing import Any


def to_json(f):
    """A function wrapper that ensures the return value is JSON serializable."""

    def is_json_serializable(v: Any) -> bool:
        try:
            json.dumps(v)
            return True
        except (TypeError, OverflowError):
            return False

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        result = f(*args, **kwargs)
        return (
            result
            if is_json_serializable(result)
            else json.dumps(result, default=str, indent=1)
        )

    return wrapper
