"""Dramatiq integration for Checkend error monitoring."""

from typing import Any, Optional

import checkend


class CheckendMiddleware:
    """
    Dramatiq middleware that reports exceptions to Checkend.

    This middleware automatically captures exceptions from Dramatiq actors
    and reports them to Checkend with relevant context.

    Example:
        import dramatiq
        from dramatiq.brokers.redis import RedisBroker
        from checkend.integrations.dramatiq import CheckendMiddleware

        import checkend
        checkend.configure(api_key='your-key')

        broker = RedisBroker()
        broker.add_middleware(CheckendMiddleware())
        dramatiq.set_broker(broker)

        @dramatiq.actor
        def my_task():
            # Your task logic
            pass
    """

    def __init__(self, ignore_retries: bool = True):
        """
        Initialize the Checkend middleware.

        Args:
            ignore_retries: If True, don't report errors for messages that will be retried.
                           Default is True to avoid duplicate error reports.
        """
        self.ignore_retries = ignore_retries

    @property
    def actor_options(self) -> set:
        """Return the set of actor options this middleware adds."""
        return set()

    def before_process_message(
        self,
        broker: Any,
        message: Any,
    ) -> None:
        """Called before a message is processed."""
        checkend.clear()

        context = self._build_message_context(message)
        checkend.set_context(context)

    def after_process_message(
        self,
        broker: Any,
        message: Any,
        *,
        result: Any = None,
        exception: Optional[BaseException] = None,
    ) -> None:
        """Called after a message is processed (success or failure)."""
        if exception is not None:
            # Check if we should ignore retries
            if self.ignore_retries and self._will_retry(message):
                checkend.clear()
                return

            # Add exception context
            context = checkend.get_context() or {}
            context["dramatiq_exception"] = type(exception).__name__

            # Add retry info
            if hasattr(message, "options"):
                options = message.options or {}
                if "retries" in options:
                    context["retries"] = options["retries"]

            checkend.set_context(context)
            checkend.notify(exception)

        checkend.clear()

    def after_skip_message(
        self,
        broker: Any,
        message: Any,
    ) -> None:
        """Called when a message is skipped."""
        checkend.clear()

    def _build_message_context(self, message: Any) -> dict[str, Any]:
        """Build context dictionary from Dramatiq message."""
        context: dict[str, Any] = {}

        if hasattr(message, "message_id"):
            context["message_id"] = message.message_id

        if hasattr(message, "actor_name"):
            context["actor_name"] = message.actor_name

        if hasattr(message, "queue_name"):
            context["queue"] = message.queue_name

        if hasattr(message, "options"):
            options = message.options or {}

            if "retries" in options:
                context["retries"] = options["retries"]

            if "max_retries" in options:
                context["max_retries"] = options["max_retries"]

        # Add sanitized args/kwargs
        if hasattr(message, "args") and message.args:
            context["message_args"] = self._sanitize_args(message.args)

        if hasattr(message, "kwargs") and message.kwargs:
            context["message_kwargs"] = self._sanitize_kwargs(message.kwargs)

        return context

    def _will_retry(self, message: Any) -> bool:
        """Check if a message will be retried."""
        if not hasattr(message, "options"):
            return False

        options = message.options or {}
        retries = options.get("retries", 0)
        max_retries = options.get("max_retries", 0)

        return retries < max_retries

    def _sanitize_args(self, args: tuple, max_items: int = 10) -> list:
        """Sanitize message arguments for safe logging."""
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

    def _sanitize_kwargs(self, kwargs: dict, max_items: int = 10) -> dict:
        """Sanitize message keyword arguments for safe logging."""
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


def init_dramatiq(broker: Any, ignore_retries: bool = True) -> CheckendMiddleware:
    """
    Initialize Checkend for Dramatiq by adding the middleware to a broker.

    Args:
        broker: Dramatiq broker instance
        ignore_retries: If True, don't report errors for messages that will be retried

    Returns:
        The CheckendMiddleware instance

    Example:
        import dramatiq
        from dramatiq.brokers.redis import RedisBroker
        from checkend.integrations.dramatiq import init_dramatiq

        import checkend
        checkend.configure(api_key='your-key')

        broker = RedisBroker()
        init_dramatiq(broker)
        dramatiq.set_broker(broker)
    """
    middleware = CheckendMiddleware(ignore_retries=ignore_retries)
    broker.add_middleware(middleware)
    return middleware
