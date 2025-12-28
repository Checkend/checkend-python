"""Testing utilities for Checkend SDK."""

from typing import Optional

from checkend.notice import Notice


class Testing:
    """
    Testing mode for capturing notices without sending them.

    Usage:
        # In your test setup
        Testing.setup()

        # In your tests
        checkend.notify(exception)
        assert Testing.has_notices()
        assert Testing.last_notice.error_class == 'ValueError'

        # In your test teardown
        Testing.teardown()
    """

    _enabled: bool = False
    _notices: list[Notice] = []

    @classmethod
    def setup(cls) -> None:
        """Enable testing mode."""
        cls._enabled = True
        cls._notices = []

    @classmethod
    def teardown(cls) -> None:
        """Disable testing mode and clear notices."""
        cls._enabled = False
        cls._notices = []

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if testing mode is enabled."""
        return cls._enabled

    @classmethod
    def notices(cls) -> list[Notice]:
        """Get all captured notices."""
        return cls._notices.copy()

    @classmethod
    @property
    def last_notice(cls) -> Optional[Notice]:
        """Get the last captured notice."""
        return cls._notices[-1] if cls._notices else None

    @classmethod
    @property
    def first_notice(cls) -> Optional[Notice]:
        """Get the first captured notice."""
        return cls._notices[0] if cls._notices else None

    @classmethod
    def notice_count(cls) -> int:
        """Get the number of captured notices."""
        return len(cls._notices)

    @classmethod
    def has_notices(cls) -> bool:
        """Check if any notices have been captured."""
        return len(cls._notices) > 0

    @classmethod
    def clear_notices(cls) -> None:
        """Clear all captured notices."""
        cls._notices = []

    @classmethod
    def _add_notice(cls, notice: Notice) -> None:
        """Add a notice (internal use only)."""
        cls._notices.append(notice)
