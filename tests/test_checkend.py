"""Tests for main checkend module."""

import checkend
from checkend import Testing


class TestCheckend:
    def setup_method(self):
        checkend.reset()
        Testing.setup()

    def teardown_method(self):
        checkend.reset()
        Testing.teardown()

    def test_configure_returns_configuration(self):
        config = checkend.configure(api_key="test-key", enabled=True)
        assert config.api_key == "test-key"

    def test_notify_captures_exception(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        try:
            raise ValueError("Test error")
        except Exception as e:
            checkend.notify(e)

        assert Testing.has_notices()
        assert Testing.notice_count() == 1
        notices = Testing.notices()
        assert notices[0].error_class == "ValueError"
        assert notices[0].message == "Test error"

    def test_notify_with_context(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e, context={"order_id": 123})

        notices = Testing.notices()
        assert notices[0].context["order_id"] == 123

    def test_notify_with_user(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e, user={"id": "user-1", "email": "test@example.com"})

        notices = Testing.notices()
        assert notices[0].user["id"] == "user-1"
        assert notices[0].user["email"] == "test@example.com"

    def test_notify_with_tags(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e, tags=["critical", "backend"])

        notices = Testing.notices()
        assert notices[0].tags == ["critical", "backend"]

    def test_notify_with_fingerprint(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e, fingerprint="custom-fingerprint")

        notices = Testing.notices()
        assert notices[0].fingerprint == "custom-fingerprint"

    def test_notify_disabled_does_not_capture(self):
        checkend.configure(api_key="test-key", enabled=False)

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e)

        assert not Testing.has_notices()

    def test_notify_ignores_configured_exceptions(self):
        checkend.configure(
            api_key="test-key",
            enabled=True,
            async_send=False,
            ignored_exceptions=[ValueError],
        )

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e)

        assert not Testing.has_notices()

    def test_set_and_get_context(self):
        checkend.set_context({"key1": "value1"})
        checkend.set_context({"key2": "value2"})

        context = checkend.get_context()
        assert context["key1"] == "value1"
        assert context["key2"] == "value2"

    def test_set_and_get_user(self):
        checkend.set_user({"id": "user-1", "email": "test@example.com"})

        user = checkend.get_user()
        assert user["id"] == "user-1"
        assert user["email"] == "test@example.com"

    def test_set_and_get_request(self):
        checkend.set_request({"url": "https://example.com", "method": "POST"})

        request = checkend.get_request()
        assert request["url"] == "https://example.com"
        assert request["method"] == "POST"

    def test_clear_resets_context(self):
        checkend.set_context({"key": "value"})
        checkend.set_user({"id": "user-1"})
        checkend.set_request({"url": "https://example.com"})

        checkend.clear()

        assert checkend.get_context() == {}
        assert checkend.get_user() == {}
        assert checkend.get_request() == {}

    def test_context_merged_into_notice(self):
        checkend.configure(api_key="test-key", enabled=True, async_send=False)
        checkend.set_context({"global_key": "global_value"})

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e, context={"local_key": "local_value"})

        notices = Testing.notices()
        assert notices[0].context["global_key"] == "global_value"
        assert notices[0].context["local_key"] == "local_value"

    def test_before_notify_callback(self):
        called = []

        def callback(notice):
            called.append(notice)
            return True

        checkend.configure(
            api_key="test-key",
            enabled=True,
            async_send=False,
            before_notify=[callback],
        )

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e)

        assert len(called) == 1
        assert Testing.has_notices()

    def test_before_notify_can_skip_notice(self):
        def callback(notice):
            return False  # Skip sending

        checkend.configure(
            api_key="test-key",
            enabled=True,
            async_send=False,
            before_notify=[callback],
        )

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e)

        assert not Testing.has_notices()

    def test_notify_sync_returns_response(self):
        checkend.configure(api_key="test-key", enabled=True)

        try:
            raise ValueError("Test")
        except Exception as e:
            response = checkend.notify_sync(e)

        assert response is not None
        assert response["id"] == 0  # Testing mode returns 0


class TestTesting:
    def setup_method(self):
        Testing.teardown()

    def teardown_method(self):
        Testing.teardown()

    def test_setup_enables_testing(self):
        assert not Testing.is_enabled()
        Testing.setup()
        assert Testing.is_enabled()

    def test_teardown_disables_testing(self):
        Testing.setup()
        Testing.teardown()
        assert not Testing.is_enabled()

    def test_notices_returns_copy(self):
        Testing.setup()
        notices1 = Testing.notices()
        notices2 = Testing.notices()
        assert notices1 is not notices2

    def test_clear_notices(self):
        Testing.setup()
        checkend.configure(api_key="test-key", enabled=True, async_send=False)

        try:
            raise ValueError("Test")
        except Exception as e:
            checkend.notify(e)

        assert Testing.has_notices()
        Testing.clear_notices()
        assert not Testing.has_notices()
