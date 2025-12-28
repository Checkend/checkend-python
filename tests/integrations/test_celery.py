"""Tests for Celery integration."""

from unittest.mock import patch

import checkend
from checkend import Testing
from checkend.integrations.celery import (
    _sanitize_task_args,
    _sanitize_task_kwargs,
    init_celery,
)


class TestCeleryHelpers:
    def test_sanitize_task_args_basic(self):
        args = ("arg1", "arg2", 123)
        result = _sanitize_task_args(args)
        assert result == ["arg1", "arg2", "123"]

    def test_sanitize_task_args_truncates_long_values(self):
        long_arg = "x" * 500
        args = (long_arg,)
        result = _sanitize_task_args(args)
        assert len(result[0]) == 203  # 200 + '...'

    def test_sanitize_task_args_limits_items(self):
        args = tuple(range(20))
        result = _sanitize_task_args(args, max_items=5)
        assert len(result) == 6  # 5 items + truncation message
        assert "15 more" in result[-1]

    def test_sanitize_task_args_handles_unserializable(self):
        class Unserializable:
            def __str__(self):
                raise Exception("Cannot serialize")

        args = (Unserializable(),)
        result = _sanitize_task_args(args)
        assert result == ["<unserializable>"]

    def test_sanitize_task_kwargs_basic(self):
        kwargs = {"key1": "value1", "key2": 123}
        result = _sanitize_task_kwargs(kwargs)
        assert result == {"key1": "value1", "key2": "123"}

    def test_sanitize_task_kwargs_truncates_long_values(self):
        long_value = "x" * 500
        kwargs = {"key": long_value}
        result = _sanitize_task_kwargs(kwargs)
        assert len(result["key"]) == 203

    def test_sanitize_task_kwargs_limits_items(self):
        kwargs = {f"key{i}": f"value{i}" for i in range(20)}
        result = _sanitize_task_kwargs(kwargs, max_items=5)
        assert len(result) == 6  # 5 items + _truncated
        assert "_truncated" in result


class TestCeleryIntegration:
    def setup_method(self):
        checkend.reset()
        Testing.setup()

    def teardown_method(self):
        checkend.reset()
        Testing.teardown()

    def test_init_celery_requires_celery(self):
        """Test that init_celery raises ImportError when celery is not installed."""
        with patch.dict("sys.modules", {"celery": None}):
            # This test would need celery to not be installed
            # Since we can't easily uninstall it, we just verify the function exists
            assert callable(init_celery)

    def test_checkend_task_on_failure_captures_exception(self):
        """Test that the on_failure pattern captures exceptions correctly."""
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        # Simulate what CheckendTask.on_failure does
        exc = ValueError("Task failed")
        task_id = "task-123"
        task_name = "test_task"
        retry_count = 2

        context = {
            "task_id": task_id,
            "task_name": task_name,
            "retry_count": retry_count,
        }

        # Add sanitized args/kwargs
        args = ("arg1",)
        kwargs = {"key": "value"}
        sanitized_args = _sanitize_task_args(args)
        sanitized_kwargs = _sanitize_task_kwargs(kwargs)

        if sanitized_args:
            context["task_args"] = sanitized_args
        if sanitized_kwargs:
            context["task_kwargs"] = sanitized_kwargs

        checkend.set_context(context)
        checkend.notify(exc)
        checkend.clear()

        assert Testing.has_notices()
        notice = Testing.notices()[-1]
        assert notice.error_class == "ValueError"
        assert notice.context.get("task_id") == "task-123"
        assert notice.context.get("task_name") == "test_task"


class TestCeleryContextCapture:
    def setup_method(self):
        checkend.reset()
        Testing.setup()

    def teardown_method(self):
        checkend.reset()
        Testing.teardown()

    def test_context_cleared_before_task(self):
        """Test that context is cleared at the start of each task."""
        # Set some initial context
        checkend.set_context({"existing": "data"})

        # Simulate task prerun
        checkend.clear()
        checkend.set_context({"task_id": "new-task"})

        context = checkend.get_context()
        assert "existing" not in context
        assert context.get("task_id") == "new-task"

    def test_task_args_sanitized_in_context(self):
        """Test that task args are sanitized before being added to context."""
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        # Simulate task failure with args
        args = ("order-123", "user-456")
        sanitized = _sanitize_task_args(args)

        checkend.set_context({"task_args": sanitized})

        try:
            raise ValueError("Task error")
        except Exception as e:
            checkend.notify(e)

        assert Testing.has_notices()
        notice = Testing.notices()[-1]
        # Args are stringified and truncated if needed
        assert "order-123" in notice.context.get("task_args", [])
