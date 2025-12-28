"""RQ (Redis Queue) integration for Checkend error monitoring."""

from typing import Any

import checkend


def init_rq() -> None:
    """
    Initialize Checkend for RQ.

    This function doesn't need to do anything special as RQ uses exception handlers
    that are passed to the worker. Use the rq_exception_handler function directly.

    Example:
        from rq import Worker
        import checkend
        from checkend.integrations.rq import rq_exception_handler

        checkend.configure(api_key='your-key')

        worker = Worker(['default'], exception_handlers=[rq_exception_handler])
        worker.work()
    """
    pass


def rq_exception_handler(
    job: Any,
    exc_type: type[BaseException],
    exc_value: BaseException,
    traceback: Any,
) -> None:
    """
    RQ exception handler that reports errors to Checkend.

    Use this as an exception handler when creating an RQ worker.

    Args:
        job: The RQ job that failed
        exc_type: The type of the exception
        exc_value: The exception instance
        traceback: The traceback object

    Example:
        from rq import Worker
        from checkend.integrations.rq import rq_exception_handler

        worker = Worker(['default'], exception_handlers=[rq_exception_handler])
        worker.work()
    """
    checkend.clear()

    # Build context from job
    context = _build_job_context(job)
    checkend.set_context(context)

    # Notify Checkend
    checkend.notify(exc_value)

    checkend.clear()


def _build_job_context(job: Any) -> dict:
    """Build context dictionary from RQ job."""
    context: dict = {}

    # Basic job info
    if hasattr(job, "id"):
        context["job_id"] = job.id

    if hasattr(job, "func_name"):
        context["job_func"] = job.func_name

    if hasattr(job, "origin"):
        context["queue"] = job.origin

    if hasattr(job, "description"):
        context["job_description"] = job.description

    # Retry info
    if hasattr(job, "retries_left"):
        context["retries_left"] = job.retries_left

    if hasattr(job, "retry_intervals"):
        context["retry_intervals"] = job.retry_intervals

    # Enqueue time
    if hasattr(job, "enqueued_at") and job.enqueued_at:
        context["enqueued_at"] = str(job.enqueued_at)

    # Add sanitized args/kwargs
    if hasattr(job, "args") and job.args:
        context["job_args"] = _sanitize_args(job.args)

    if hasattr(job, "kwargs") and job.kwargs:
        context["job_kwargs"] = _sanitize_kwargs(job.kwargs)

    return context


def _sanitize_args(args: tuple, max_items: int = 10) -> list:
    """Sanitize job arguments for safe logging."""
    result = []
    for arg in args[:max_items]:
        try:
            str_arg = str(arg)
            if len(str_arg) > 200:
                str_arg = str_arg[:200] + "..."
            result.append(str_arg)
        except Exception:
            result.append("<unserializable>")

    if len(args) > max_items:
        result.append(f"... ({len(args) - max_items} more)")

    return result


def _sanitize_kwargs(kwargs: dict, max_items: int = 10) -> dict:
    """Sanitize job keyword arguments for safe logging."""
    result = {}
    items = list(kwargs.items())[:max_items]

    for key, value in items:
        try:
            str_value = str(value)
            if len(str_value) > 200:
                str_value = str_value[:200] + "..."
            result[str(key)] = str_value
        except Exception:
            result[str(key)] = "<unserializable>"

    if len(kwargs) > max_items:
        result["_truncated"] = f"{len(kwargs) - max_items} more items"

    return result


class CheckendWorker:
    """
    Wrapper to create an RQ worker with Checkend exception handling.

    Example:
        from checkend.integrations.rq import CheckendWorker

        worker = CheckendWorker(['default'])
        worker.work()
    """

    def __init__(self, queues: list, **kwargs: Any):
        """
        Create an RQ worker with Checkend exception handling.

        Args:
            queues: List of queue names to listen to
            **kwargs: Additional arguments passed to rq.Worker
        """
        try:
            from rq import Worker
        except ImportError as err:
            raise ImportError(
                "RQ is required for the RQ integration. Install it with: pip install rq"
            ) from err

        # Add Checkend exception handler
        exception_handlers = kwargs.pop("exception_handlers", [])
        exception_handlers.append(rq_exception_handler)

        self._worker = Worker(queues, exception_handlers=exception_handlers, **kwargs)

    def work(self, **kwargs: Any) -> None:
        """Start the worker."""
        self._worker.work(**kwargs)

    @property
    def worker(self) -> Any:
        """Get the underlying RQ worker instance."""
        return self._worker
