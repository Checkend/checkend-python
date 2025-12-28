"""
Checkend - Python SDK for error monitoring.

A lightweight, zero-dependency error monitoring SDK for Python applications.
"""

import atexit
import contextvars
from typing import Any, Optional

from checkend.client import Client
from checkend.configuration import Configuration
from checkend.notice import Notice
from checkend.testing import Testing
from checkend.version import VERSION
from checkend.worker import Worker

__version__ = VERSION
__all__ = [
    "configure",
    "notify",
    "notify_sync",
    "set_context",
    "get_context",
    "set_user",
    "get_user",
    "set_request",
    "get_request",
    "clear",
    "flush",
    "stop",
    "reset",
    "Configuration",
    "Testing",
]

# Context variables for request-scoped data (use None as default, not mutable {})
_context_var: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "checkend_context", default=None
)
_user_var: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "checkend_user", default=None
)
_request_var: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "checkend_request", default=None
)

# Global state
_configuration: Optional[Configuration] = None
_worker: Optional[Worker] = None
_initialized: bool = False


def configure(**options) -> Configuration:
    """
    Configure the Checkend SDK.

    Args:
        api_key: Your Checkend ingestion API key (required)
        endpoint: API endpoint URL (default: https://app.checkend.com)
        environment: Environment name (auto-detected if not provided)
        enabled: Whether error reporting is enabled (default: True in production)
        async_send: Whether to send errors asynchronously (default: True)
        max_queue_size: Maximum queue size for async sending (default: 1000)
        timeout: HTTP request timeout in seconds (default: 15)
        filter_keys: List of keys to filter from payloads
        ignored_exceptions: List of exception classes or patterns to ignore
        before_notify: List of callbacks to run before sending (return False to skip)
        logger: Custom logger instance
        debug: Enable debug logging (default: False)

    Returns:
        Configuration instance
    """
    global _configuration, _worker, _initialized

    _configuration = Configuration(**options)

    if _configuration.async_send and _configuration.enabled:
        _worker = Worker(_configuration)
        _worker.start()

    _initialized = True

    # Register shutdown handler
    atexit.register(_shutdown)

    return _configuration


def get_configuration() -> Optional[Configuration]:
    """Get the current configuration."""
    return _configuration


def notify(
    exception: BaseException,
    context: Optional[dict[str, Any]] = None,
    user: Optional[dict[str, Any]] = None,
    request: Optional[dict[str, Any]] = None,
    fingerprint: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[int]:
    """
    Report an exception to Checkend asynchronously.

    Args:
        exception: The exception to report
        context: Additional context data
        user: User information
        request: Request information
        fingerprint: Custom fingerprint for grouping
        tags: List of tags for the error

    Returns:
        Notice ID if sent synchronously, None if queued or skipped
    """
    if not _initialized or not _configuration or not _configuration.enabled:
        return None

    # Check if exception should be ignored
    if _should_ignore(exception):
        return None

    # Build notice
    notice = _build_notice(
        exception,
        context=context,
        user=user,
        request=request,
        fingerprint=fingerprint,
        tags=tags,
    )

    # Run before_notify callbacks
    if not _run_before_notify(notice):
        return None

    # Handle testing mode
    if Testing.is_enabled():
        Testing._add_notice(notice)
        return None

    # Send asynchronously or synchronously
    if _configuration.async_send and _worker:
        _worker.push(notice)
        return None
    else:
        client = Client(_configuration)
        response = client.send(notice)
        return response.get("id") if response else None


def notify_sync(
    exception: BaseException,
    context: Optional[dict[str, Any]] = None,
    user: Optional[dict[str, Any]] = None,
    request: Optional[dict[str, Any]] = None,
    fingerprint: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[dict[str, Any]]:
    """
    Report an exception to Checkend synchronously.

    Args:
        exception: The exception to report
        context: Additional context data
        user: User information
        request: Request information
        fingerprint: Custom fingerprint for grouping
        tags: List of tags for the error

    Returns:
        API response dict with 'id' and 'problem_id', or None if skipped
    """
    if not _initialized or not _configuration or not _configuration.enabled:
        return None

    # Check if exception should be ignored
    if _should_ignore(exception):
        return None

    # Build notice
    notice = _build_notice(
        exception,
        context=context,
        user=user,
        request=request,
        fingerprint=fingerprint,
        tags=tags,
    )

    # Run before_notify callbacks
    if not _run_before_notify(notice):
        return None

    # Handle testing mode
    if Testing.is_enabled():
        Testing._add_notice(notice)
        return {"id": 0, "problem_id": 0}

    client = Client(_configuration)
    return client.send(notice)


def set_context(context: dict[str, Any]) -> None:
    """Set context data for the current request/task."""
    current = _context_var.get() or {}
    updated = current.copy()
    updated.update(context)
    _context_var.set(updated)


def get_context() -> dict[str, Any]:
    """Get the current context data."""
    value = _context_var.get()
    return value.copy() if value else {}


def set_user(user: dict[str, Any]) -> None:
    """Set user information for the current request/task."""
    _user_var.set(user)


def get_user() -> dict[str, Any]:
    """Get the current user information."""
    value = _user_var.get()
    return value.copy() if value else {}


def set_request(request: dict[str, Any]) -> None:
    """Set request information for the current request."""
    _request_var.set(request)


def get_request() -> dict[str, Any]:
    """Get the current request information."""
    value = _request_var.get()
    return value.copy() if value else {}


def clear() -> None:
    """Clear all context, user, and request data."""
    _context_var.set(None)
    _user_var.set(None)
    _request_var.set(None)


def flush(timeout: Optional[float] = None) -> None:
    """
    Wait for all queued notices to be sent.

    Args:
        timeout: Maximum time to wait in seconds (default: 5)
    """
    if _worker:
        _worker.flush(timeout or 5.0)


def stop(timeout: Optional[float] = None) -> None:
    """
    Stop the worker and wait for pending notices.

    Args:
        timeout: Maximum time to wait in seconds (default: 5)
    """
    global _worker
    if _worker:
        _worker.stop(timeout or 5.0)
        _worker = None


def reset() -> None:
    """Reset all state (useful for testing)."""
    global _configuration, _worker, _initialized

    stop()
    _configuration = None
    _initialized = False
    clear()
    Testing.teardown()


def _shutdown() -> None:
    """Shutdown handler called on program exit."""
    stop(timeout=5.0)


def _should_ignore(exception: BaseException) -> bool:
    """Check if an exception should be ignored."""
    if not _configuration:
        return False

    from checkend.filters.ignore_filter import IgnoreFilter

    ignore_filter = IgnoreFilter(_configuration.ignored_exceptions)
    return ignore_filter.should_ignore(exception)


def _build_notice(
    exception: BaseException,
    context: Optional[dict[str, Any]] = None,
    user: Optional[dict[str, Any]] = None,
    request: Optional[dict[str, Any]] = None,
    fingerprint: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Notice:
    """Build a Notice from an exception."""
    from checkend.notice_builder import NoticeBuilder

    # Merge context from various sources
    merged_context = get_context()
    if context:
        merged_context.update(context)

    # Merge user from various sources
    merged_user = get_user()
    if user:
        merged_user.update(user)

    # Merge request from various sources
    merged_request = get_request()
    if request:
        merged_request.update(request)

    builder = NoticeBuilder(_configuration)
    return builder.build(
        exception,
        context=merged_context,
        user=merged_user,
        request=merged_request,
        fingerprint=fingerprint,
        tags=tags,
    )


def _run_before_notify(notice: Notice) -> bool:
    """Run before_notify callbacks. Returns False if notice should be skipped."""
    if not _configuration or not _configuration.before_notify:
        return True

    for callback in _configuration.before_notify:
        try:
            result = callback(notice)
            if result is False:
                return False
        except Exception:
            # Ignore callback errors
            pass

    return True
