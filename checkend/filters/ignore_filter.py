"""Filter for ignoring certain exceptions."""

import re
from typing import Union


class IgnoreFilter:
    """Filter that determines if an exception should be ignored."""

    def __init__(self, ignored_exceptions: list[Union[type[BaseException], str]]):
        self.ignored_exceptions = ignored_exceptions

    def should_ignore(self, exception: BaseException) -> bool:
        """
        Check if an exception should be ignored.

        Args:
            exception: The exception to check

        Returns:
            True if the exception should be ignored
        """
        exception_class = type(exception)
        exception_name = exception_class.__name__

        for pattern in self.ignored_exceptions:
            if isinstance(pattern, type):
                # Check if exception is an instance of the class
                if isinstance(exception, pattern):
                    return True
            elif isinstance(pattern, str):
                # Check for string match (class name or regex)
                if self._matches_pattern(exception_name, pattern):
                    return True
                # Also check full module path
                full_name = f"{exception_class.__module__}.{exception_name}"
                if self._matches_pattern(full_name, pattern):
                    return True

        return False

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a name matches a pattern."""
        # Exact match
        if name == pattern:
            return True

        # Regex match
        try:
            if re.match(pattern, name):
                return True
        except re.error:
            pass

        return False
