"""Celery integration for Checkend error monitoring."""

from typing import Any

import checkend


def init_celery(app: Any) -> None:
    """
    Initialize Checkend for Celery.

    This registers signal handlers for task lifecycle events to automatically
    capture exceptions and set context.

    Args:
        app: Celery application instance

    Example:
        from celery import Celery
        import checkend
        from checkend.integrations.celery import init_celery

        app = Celery('tasks')
        checkend.configure(api_key='your-key')
        init_celery(app)
    """
    try:
        from celery import signals
    except ImportError as err:
        raise ImportError(
            "Celery is required for the Celery integration. Install it with: pip install celery"
        ) from err

    @signals.task_prerun.connect
    def on_task_prerun(
        task_id: str,
        task: Any,
        args: tuple,
        kwargs: dict,
        **signal_kwargs: Any,
    ) -> None:
        """Called before a task is executed."""
        checkend.clear()

        # Build task context
        context: dict[str, Any] = {
            "task_id": task_id,
            "task_name": task.name,
        }

        # Add queue info if available
        if hasattr(task.request, "delivery_info"):
            delivery_info = task.request.delivery_info or {}
            if "routing_key" in delivery_info:
                context["queue"] = delivery_info.get("routing_key")

        # Add retry info
        if hasattr(task.request, "retries"):
            context["retry_count"] = task.request.retries

        # Add worker hostname if available
        if hasattr(task.request, "hostname"):
            context["worker"] = task.request.hostname

        checkend.set_context(context)

    @signals.task_failure.connect
    def on_task_failure(
        task_id: str,
        exception: BaseException,
        args: tuple,
        kwargs: dict,
        traceback: Any,
        einfo: Any,
        **signal_kwargs: Any,
    ) -> None:
        """Called when a task fails with an exception."""
        # Get additional context
        context = checkend.get_context() or {}

        # Add sanitized args/kwargs (limited to avoid large payloads)
        sanitized_args = _sanitize_task_args(args)
        sanitized_kwargs = _sanitize_task_kwargs(kwargs)

        if sanitized_args:
            context["task_args"] = sanitized_args
        if sanitized_kwargs:
            context["task_kwargs"] = sanitized_kwargs

        checkend.set_context(context)

        # Notify Checkend
        checkend.notify(exception)

    @signals.task_postrun.connect
    def on_task_postrun(
        task_id: str,
        task: Any,
        args: tuple,
        kwargs: dict,
        retval: Any,
        state: str,
        **signal_kwargs: Any,
    ) -> None:
        """Called after a task completes (success or failure)."""
        checkend.clear()


def _sanitize_task_args(args: tuple, max_items: int = 10) -> list:
    """Sanitize task arguments for safe logging."""
    result = []
    for _i, arg in enumerate(args[:max_items]):
        try:
            # Convert to string and truncate
            str_arg = str(arg)
            if len(str_arg) > 200:
                str_arg = str_arg[:200] + "..."
            result.append(str_arg)
        except Exception:
            result.append("<unserializable>")

    if len(args) > max_items:
        result.append(f"... ({len(args) - max_items} more)")

    return result


def _sanitize_task_kwargs(kwargs: dict, max_items: int = 10) -> dict:
    """Sanitize task keyword arguments for safe logging."""
    result = {}
    items = list(kwargs.items())[:max_items]

    for key, value in items:
        try:
            # Convert to string and truncate
            str_value = str(value)
            if len(str_value) > 200:
                str_value = str_value[:200] + "..."
            result[str(key)] = str_value
        except Exception:
            result[str(key)] = "<unserializable>"

    if len(kwargs) > max_items:
        result["_truncated"] = f"{len(kwargs) - max_items} more items"

    return result


class CheckendTask:
    """
    Mixin for Celery tasks that automatically reports errors to Checkend.

    Example:
        from celery import Task
        from checkend.integrations.celery import CheckendTask

        class MyTask(CheckendTask, Task):
            def run(self, *args, **kwargs):
                # Your task logic
                pass
    """

    def on_failure(
        self,
        exc: BaseException,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Called when the task fails."""
        context: dict[str, Any] = {
            "task_id": task_id,
            "task_name": self.name,
        }

        # Add retry info
        if hasattr(self.request, "retries"):
            context["retry_count"] = self.request.retries

        # Add sanitized args/kwargs
        sanitized_args = _sanitize_task_args(args)
        sanitized_kwargs = _sanitize_task_kwargs(kwargs)

        if sanitized_args:
            context["task_args"] = sanitized_args
        if sanitized_kwargs:
            context["task_kwargs"] = sanitized_kwargs

        checkend.set_context(context)
        checkend.notify(exc)
        checkend.clear()

        # Call parent if it exists
        super_method = getattr(super(), "on_failure", None)
        if super_method:
            super_method(exc, task_id, args, kwargs, einfo)
