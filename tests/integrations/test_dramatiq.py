"""Tests for Dramatiq integration."""

from unittest.mock import MagicMock

import checkend
from checkend import Testing
from checkend.integrations.dramatiq import (
    CheckendMiddleware,
    init_dramatiq,
)


class TestDramatiqMiddleware:
    def setup_method(self):
        checkend.reset()
        Testing.setup()
        self.middleware = CheckendMiddleware()

    def teardown_method(self):
        checkend.reset()
        Testing.teardown()

    def test_middleware_initialization_default(self):
        middleware = CheckendMiddleware()
        assert middleware.ignore_retries is True

    def test_middleware_initialization_custom(self):
        middleware = CheckendMiddleware(ignore_retries=False)
        assert middleware.ignore_retries is False

    def test_actor_options_returns_empty_set(self):
        assert self.middleware.actor_options == set()

    def test_before_process_message_clears_context(self):
        # Set some pre-existing context
        checkend.set_context({"existing": "data"})

        message = MagicMock()
        message.message_id = "msg-123"
        message.actor_name = "my_actor"
        message.queue_name = "default"

        self.middleware.before_process_message(None, message)

        # Old context should be cleared, new context set
        context = checkend.get_context()
        assert "existing" not in context
        assert context.get("message_id") == "msg-123"

    def test_before_process_message_sets_context(self):
        message = MagicMock()
        message.message_id = "msg-456"
        message.actor_name = "process_order"
        message.queue_name = "orders"
        message.options = {"retries": 1, "max_retries": 3}
        message.args = ("order-123",)
        message.kwargs = {"priority": "high"}

        self.middleware.before_process_message(None, message)

        context = checkend.get_context()
        assert context["message_id"] == "msg-456"
        assert context["actor_name"] == "process_order"
        assert context["queue"] == "orders"
        assert context["retries"] == 1
        assert context["max_retries"] == 3

    def test_after_process_message_success_clears_context(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)
        checkend.set_context({"some": "data"})

        message = MagicMock()

        self.middleware.after_process_message(None, message, result="success")

        assert checkend.get_context() == {}
        assert not Testing.has_notices()

    def test_after_process_message_failure_captures_error(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        # Simulate what after_process_message does when an exception occurs
        # and the message won't be retried
        exc = ValueError("Actor failed")

        # Simulate no more retries
        context = checkend.get_context() or {}
        context["dramatiq_exception"] = type(exc).__name__
        context["retries"] = 3
        checkend.set_context(context)
        checkend.notify(exc)
        checkend.clear()

        assert Testing.has_notices()
        notice = Testing.notices()[-1]
        assert notice.error_class == "ValueError"
        assert notice.message == "Actor failed"

    def test_after_process_message_ignores_retryable_errors(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        middleware = CheckendMiddleware(ignore_retries=True)

        message = MagicMock()
        message.options = {"retries": 1, "max_retries": 3}  # Will retry

        exc = ValueError("Temporary failure")

        middleware.after_process_message(None, message, exception=exc)

        # Should not capture because message will retry
        assert not Testing.has_notices()

    def test_after_process_message_captures_final_retry_error(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        middleware = CheckendMiddleware(ignore_retries=True)

        message = MagicMock()
        message.options = {"retries": 3, "max_retries": 3}  # Final retry

        exc = ValueError("Final failure")

        middleware.after_process_message(None, message, exception=exc)

        # Should capture because no more retries
        assert Testing.has_notices()

    def test_after_process_message_captures_all_when_ignore_retries_false(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        middleware = CheckendMiddleware(ignore_retries=False)

        message = MagicMock()
        message.options = {"retries": 1, "max_retries": 3}  # Will retry

        exc = ValueError("Error")

        middleware.after_process_message(None, message, exception=exc)

        # Should capture even though message will retry
        assert Testing.has_notices()

    def test_after_skip_message_clears_context(self):
        checkend.set_context({"some": "data"})

        message = MagicMock()

        self.middleware.after_skip_message(None, message)

        assert checkend.get_context() == {}


class TestDramatiqMiddlewareHelpers:
    def setup_method(self):
        self.middleware = CheckendMiddleware()

    def test_will_retry_true(self):
        message = MagicMock()
        message.options = {"retries": 1, "max_retries": 3}

        assert self.middleware._will_retry(message) is True

    def test_will_retry_false_at_max(self):
        message = MagicMock()
        message.options = {"retries": 3, "max_retries": 3}

        assert self.middleware._will_retry(message) is False

    def test_will_retry_false_no_options(self):
        message = MagicMock(spec=[])  # No options attribute

        assert self.middleware._will_retry(message) is False

    def test_sanitize_args(self):
        args = ("arg1", "arg2", 123)
        result = self.middleware._sanitize_args(args)
        assert result == ["arg1", "arg2", "123"]

    def test_sanitize_kwargs(self):
        kwargs = {"key1": "value1", "key2": 123}
        result = self.middleware._sanitize_kwargs(kwargs)
        assert result == {"key1": "value1", "key2": "123"}


class TestInitDramatiq:
    def test_init_dramatiq_adds_middleware(self):
        broker = MagicMock()

        middleware = init_dramatiq(broker)

        broker.add_middleware.assert_called_once()
        assert isinstance(middleware, CheckendMiddleware)

    def test_init_dramatiq_with_ignore_retries(self):
        broker = MagicMock()

        middleware = init_dramatiq(broker, ignore_retries=False)

        assert middleware.ignore_retries is False


class TestBuildMessageContext:
    def setup_method(self):
        self.middleware = CheckendMiddleware()

    def test_build_context_full_message(self):
        message = MagicMock()
        message.message_id = "msg-123"
        message.actor_name = "my_actor"
        message.queue_name = "default"
        message.options = {"retries": 2, "max_retries": 5}
        message.args = ("arg1", "arg2")
        message.kwargs = {"key": "value"}

        context = self.middleware._build_message_context(message)

        assert context["message_id"] == "msg-123"
        assert context["actor_name"] == "my_actor"
        assert context["queue"] == "default"
        assert context["retries"] == 2
        assert context["max_retries"] == 5
        assert context["message_args"] == ["arg1", "arg2"]
        assert context["message_kwargs"] == {"key": "value"}

    def test_build_context_minimal_message(self):
        message = MagicMock(spec=["message_id"])
        message.message_id = "msg-456"

        context = self.middleware._build_message_context(message)

        assert context["message_id"] == "msg-456"
        assert "actor_name" not in context
        assert "queue" not in context
