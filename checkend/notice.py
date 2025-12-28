"""Notice data structure for error reports."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class Notice:
    """Represents an error notice to be sent to Checkend."""

    error_class: str
    message: str
    backtrace: list[str]
    fingerprint: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    request: dict[str, Any] = field(default_factory=dict)
    user: dict[str, Any] = field(default_factory=dict)
    environment: str = "development"
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notifier: dict[str, str] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        """Convert the notice to an API payload."""
        payload: dict[str, Any] = {
            "error": {
                "class": self.error_class,
                "message": self.message,
                "backtrace": self.backtrace,
                "occurred_at": self.occurred_at,
            },
            "context": {
                "environment": self.environment,
                **self.context,
            },
            "notifier": self.notifier,
        }

        if self.fingerprint:
            payload["error"]["fingerprint"] = self.fingerprint

        if self.tags:
            payload["error"]["tags"] = self.tags

        if self.request:
            payload["request"] = self.request

        if self.user:
            payload["user"] = self.user

        return payload
