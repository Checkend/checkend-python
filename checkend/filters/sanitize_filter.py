"""Filter for sanitizing sensitive data."""

from typing import Any, Union

FILTERED_VALUE = "[FILTERED]"
MAX_DEPTH = 10
MAX_STRING_LENGTH = 10000


class SanitizeFilter:
    """Filter that removes sensitive data from payloads."""

    def __init__(self, filter_keys: list[str]):
        self.filter_keys = [key.lower() for key in filter_keys]
        self._seen: set[int] = set()

    def filter(self, data: Any) -> Any:
        """
        Recursively filter sensitive data from an object.

        Args:
            data: The data to filter

        Returns:
            The filtered data
        """
        self._seen = set()
        return self._filter_value(data, depth=0)

    def _filter_value(self, value: Any, depth: int = 0) -> Any:
        """Recursively filter a value."""
        # Prevent infinite recursion
        if depth > MAX_DEPTH:
            return "[MAX DEPTH EXCEEDED]"

        # Handle circular references
        if isinstance(value, (dict, list)):
            obj_id = id(value)
            if obj_id in self._seen:
                return "[CIRCULAR]"
            self._seen.add(obj_id)

        # Filter based on type
        if isinstance(value, dict):
            return self._filter_dict(value, depth)
        elif isinstance(value, (list, tuple)):
            return self._filter_list(value, depth)
        elif isinstance(value, str):
            return self._truncate_string(value)
        elif isinstance(value, (int, float, bool, type(None))):
            return value
        else:
            # Convert other types to string
            return self._truncate_string(str(value))

    def _filter_dict(self, data: dict[str, Any], depth: int) -> dict[str, Any]:
        """Filter a dictionary."""
        result = {}
        for key, value in data.items():
            if self._should_filter_key(key):
                result[key] = FILTERED_VALUE
            else:
                result[key] = self._filter_value(value, depth + 1)
        return result

    def _filter_list(self, data: Union[list, tuple], depth: int) -> list[Any]:
        """Filter a list or tuple."""
        return [self._filter_value(item, depth + 1) for item in data]

    def _should_filter_key(self, key: str) -> bool:
        """Check if a key should be filtered."""
        if not isinstance(key, str):
            return False

        key_lower = key.lower()

        for filter_key in self.filter_keys:
            # Exact match or contains match
            if filter_key in key_lower:
                return True

        return False

    def _truncate_string(self, value: str) -> str:
        """Truncate a string if it's too long."""
        if len(value) > MAX_STRING_LENGTH:
            return value[:MAX_STRING_LENGTH] + "..."
        return value
