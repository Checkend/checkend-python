"""Tests for Notice class."""

from checkend.notice import Notice


class TestNotice:
    def test_basic_notice(self):
        notice = Notice(
            error_class="ValueError",
            message="Invalid value",
            backtrace=["file.py:10 in main"],
        )
        assert notice.error_class == "ValueError"
        assert notice.message == "Invalid value"
        assert notice.backtrace == ["file.py:10 in main"]

    def test_notice_with_optional_fields(self):
        notice = Notice(
            error_class="TypeError",
            message="Type error",
            backtrace=[],
            fingerprint="custom-fingerprint",
            tags=["critical", "frontend"],
            context={"order_id": 123},
            user={"id": "user-1"},
            request={"url": "https://example.com"},
            environment="production",
        )
        assert notice.fingerprint == "custom-fingerprint"
        assert notice.tags == ["critical", "frontend"]
        assert notice.context == {"order_id": 123}
        assert notice.user == {"id": "user-1"}
        assert notice.request == {"url": "https://example.com"}
        assert notice.environment == "production"

    def test_to_payload_basic(self):
        notice = Notice(
            error_class="ValueError",
            message="Test error",
            backtrace=["file.py:10 in main"],
            environment="test",
        )
        payload = notice.to_payload()

        assert payload["error"]["class"] == "ValueError"
        assert payload["error"]["message"] == "Test error"
        assert payload["error"]["backtrace"] == ["file.py:10 in main"]
        assert payload["context"]["environment"] == "test"
        assert "occurred_at" in payload["error"]

    def test_to_payload_with_fingerprint(self):
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
            fingerprint="my-fingerprint",
        )
        payload = notice.to_payload()
        assert payload["error"]["fingerprint"] == "my-fingerprint"

    def test_to_payload_with_tags(self):
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
            tags=["urgent", "backend"],
        )
        payload = notice.to_payload()
        assert payload["error"]["tags"] == ["urgent", "backend"]

    def test_to_payload_without_optional_fields(self):
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
        )
        payload = notice.to_payload()

        # Should not include empty optional fields
        assert "fingerprint" not in payload["error"]
        assert "tags" not in payload["error"]
        assert "request" not in payload
        assert "user" not in payload

    def test_to_payload_with_request_and_user(self):
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
            request={"url": "https://example.com", "method": "POST"},
            user={"id": "user-123", "email": "user@example.com"},
        )
        payload = notice.to_payload()

        assert payload["request"] == {"url": "https://example.com", "method": "POST"}
        assert payload["user"] == {"id": "user-123", "email": "user@example.com"}

    def test_to_payload_merges_context(self):
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
            context={"custom_key": "custom_value"},
            environment="production",
        )
        payload = notice.to_payload()

        assert payload["context"]["environment"] == "production"
        assert payload["context"]["custom_key"] == "custom_value"

    def test_notifier_in_payload(self):
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
            notifier={"name": "checkend-python", "version": "0.1.0"},
        )
        payload = notice.to_payload()

        assert payload["notifier"]["name"] == "checkend-python"
        assert payload["notifier"]["version"] == "0.1.0"
