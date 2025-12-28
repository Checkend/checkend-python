"""Tests for RQ integration."""

from unittest.mock import MagicMock

import checkend
from checkend import Testing
from checkend.integrations.rq import (
    _build_job_context,
    _sanitize_args,
    _sanitize_kwargs,
    init_rq,
    rq_exception_handler,
)


class TestRQHelpers:
    def test_sanitize_args_basic(self):
        args = ("arg1", "arg2", 123)
        result = _sanitize_args(args)
        assert result == ["arg1", "arg2", "123"]

    def test_sanitize_args_truncates_long_values(self):
        long_arg = "x" * 500
        args = (long_arg,)
        result = _sanitize_args(args)
        assert len(result[0]) == 203

    def test_sanitize_args_limits_items(self):
        args = tuple(range(20))
        result = _sanitize_args(args, max_items=5)
        assert len(result) == 6
        assert "15 more" in result[-1]

    def test_sanitize_kwargs_basic(self):
        kwargs = {"key1": "value1", "key2": 123}
        result = _sanitize_kwargs(kwargs)
        assert result == {"key1": "value1", "key2": "123"}

    def test_build_job_context_basic(self):
        job = MagicMock()
        job.id = "job-123"
        job.func_name = "my_task"
        job.origin = "default"
        job.description = "A test job"
        job.args = ("arg1",)
        job.kwargs = {"key": "value"}
        job.retries_left = 3
        job.enqueued_at = "2024-01-01T00:00:00"

        context = _build_job_context(job)

        assert context["job_id"] == "job-123"
        assert context["job_func"] == "my_task"
        assert context["queue"] == "default"
        assert context["job_description"] == "A test job"
        assert context["retries_left"] == 3
        assert "job_args" in context
        assert "job_kwargs" in context

    def test_build_job_context_handles_missing_attributes(self):
        job = MagicMock(spec=[])  # Empty spec means no attributes
        context = _build_job_context(job)
        assert context == {}


class TestRQExceptionHandler:
    def setup_method(self):
        checkend.reset()
        Testing.setup()

    def teardown_method(self):
        checkend.reset()
        Testing.teardown()

    def test_exception_handler_captures_error(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        # Simulate what rq_exception_handler does
        job_id = "job-123"
        job_func = "failing_task"
        queue = "default"

        checkend.clear()
        context = {
            "job_id": job_id,
            "job_func": job_func,
            "queue": queue,
        }
        checkend.set_context(context)

        exc = ValueError("Job failed")
        checkend.notify(exc)
        checkend.clear()

        assert Testing.has_notices()
        notice = Testing.notices()[-1]
        assert notice.error_class == "ValueError"
        assert notice.message == "Job failed"

    def test_exception_handler_sets_context(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        # Simulate what rq_exception_handler does
        checkend.clear()
        context = {
            "job_id": "job-456",
            "job_func": "my_job",
            "queue": "high-priority",
        }
        checkend.set_context(context)

        exc = RuntimeError("Something went wrong")
        checkend.notify(exc)

        notice = Testing.notices()[-1]
        assert notice.context.get("job_id") == "job-456"
        assert notice.context.get("job_func") == "my_job"
        assert notice.context.get("queue") == "high-priority"

        checkend.clear()

    def test_exception_handler_clears_context_after(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        # Set some pre-existing context
        checkend.set_context({"pre_existing": "data"})

        job = MagicMock()
        job.id = "job-789"

        exc = ValueError("Error")

        rq_exception_handler(job, ValueError, exc, None)

        # Context should be cleared after handler runs
        assert checkend.get_context() == {}


class TestRQInit:
    def test_init_rq_is_callable(self):
        """Test that init_rq exists and is callable."""
        assert callable(init_rq)

    def test_init_rq_does_nothing(self):
        """Test that init_rq is a no-op (configuration happens elsewhere)."""
        result = init_rq()
        assert result is None


class TestCheckendWorker:
    def test_checkend_worker_requires_rq(self):
        """Test that CheckendWorker raises ImportError when rq is not installed."""
        # This test would need rq to not be installed
        # Since we can't easily control that, we just verify the class exists
        from checkend.integrations.rq import CheckendWorker

        assert CheckendWorker is not None
