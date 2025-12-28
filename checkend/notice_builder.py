"""Build Notice objects from exceptions."""

import platform
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from checkend.configuration import Configuration
from checkend.filters.sanitize_filter import SanitizeFilter
from checkend.notice import Notice
from checkend.version import VERSION

MAX_BACKTRACE_LINES = 100
MAX_MESSAGE_LENGTH = 10000


class NoticeBuilder:
    """Builds Notice objects from Python exceptions."""

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.sanitize_filter = SanitizeFilter(configuration.filter_keys)

    def build(
        self,
        exception: BaseException,
        context: Optional[dict[str, Any]] = None,
        user: Optional[dict[str, Any]] = None,
        request: Optional[dict[str, Any]] = None,
        fingerprint: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Notice:
        """Build a Notice from an exception."""
        error_class = self._extract_class_name(exception)
        message = self._extract_message(exception)
        backtrace = self._extract_backtrace(exception)

        # Sanitize context, user, and request data
        sanitized_context = self.sanitize_filter.filter(context or {})
        sanitized_user = self.sanitize_filter.filter(user or {})
        sanitized_request = self.sanitize_filter.filter(request or {})

        return Notice(
            error_class=error_class,
            message=message,
            backtrace=backtrace,
            fingerprint=fingerprint,
            tags=tags or [],
            context=sanitized_context,
            user=sanitized_user,
            request=sanitized_request,
            environment=self.configuration.environment,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            notifier=self._build_notifier(),
        )

    def _extract_class_name(self, exception: BaseException) -> str:
        """Extract the class name from an exception."""
        return type(exception).__name__

    def _extract_message(self, exception: BaseException) -> str:
        """Extract and truncate the message from an exception."""
        message = str(exception)
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH] + "..."
        return message

    def _extract_backtrace(self, exception: BaseException) -> list[str]:
        """Extract the backtrace from an exception."""
        # Get the traceback
        tb = exception.__traceback__
        if tb is None:
            # Try to get from sys.exc_info
            _, _, tb = sys.exc_info()

        if tb is None:
            return []

        # Format the traceback
        frames = traceback.extract_tb(tb)
        backtrace = []

        for frame in frames[:MAX_BACKTRACE_LINES]:
            line = f"{frame.filename}:{frame.lineno} in {frame.name}"
            backtrace.append(line)

        return backtrace

    def _build_notifier(self) -> dict[str, str]:
        """Build the notifier metadata."""
        return {
            "name": "checkend-python",
            "version": VERSION,
            "language": "python",
            "language_version": platform.python_version(),
        }
