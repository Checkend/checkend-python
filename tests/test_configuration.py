"""Tests for Configuration class."""

from checkend.configuration import Configuration


class TestConfiguration:
    def test_api_key_from_parameter(self):
        config = Configuration(api_key="test-key")
        assert config.api_key == "test-key"

    def test_api_key_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_API_KEY", "env-key")
        config = Configuration()
        assert config.api_key == "env-key"

    def test_parameter_overrides_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_API_KEY", "env-key")
        config = Configuration(api_key="param-key")
        assert config.api_key == "param-key"

    def test_default_endpoint(self):
        config = Configuration(api_key="test-key")
        assert config.endpoint == "https://app.checkend.com"

    def test_custom_endpoint(self):
        config = Configuration(api_key="test-key", endpoint="https://custom.example.com")
        assert config.endpoint == "https://custom.example.com"

    def test_endpoint_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_ENDPOINT", "https://env.example.com")
        config = Configuration(api_key="test-key")
        assert config.endpoint == "https://env.example.com"

    def test_default_environment_is_development(self):
        config = Configuration(api_key="test-key")
        assert config.environment == "development"

    def test_environment_from_parameter(self):
        config = Configuration(api_key="test-key", environment="staging")
        assert config.environment == "staging"

    def test_environment_detection_from_python_env(self, monkeypatch):
        monkeypatch.setenv("PYTHON_ENV", "production")
        config = Configuration(api_key="test-key")
        assert config.environment == "production"

    def test_enabled_default_in_production(self, monkeypatch):
        monkeypatch.setenv("PYTHON_ENV", "production")
        config = Configuration(api_key="test-key")
        assert config.enabled is True

    def test_enabled_default_in_development(self):
        config = Configuration(api_key="test-key")
        assert config.enabled is False

    def test_enabled_explicit_override(self):
        config = Configuration(api_key="test-key", enabled=True)
        assert config.enabled is True

    def test_default_filter_keys(self):
        config = Configuration(api_key="test-key")
        assert "password" in config.filter_keys
        assert "secret" in config.filter_keys
        assert "api_key" in config.filter_keys

    def test_custom_filter_keys_extend_defaults(self):
        config = Configuration(api_key="test-key", filter_keys=["custom_key"])
        assert "password" in config.filter_keys
        assert "custom_key" in config.filter_keys

    def test_default_async_send(self):
        config = Configuration(api_key="test-key")
        assert config.async_send is True

    def test_async_send_disabled(self):
        config = Configuration(api_key="test-key", async_send=False)
        assert config.async_send is False

    def test_default_timeout(self):
        config = Configuration(api_key="test-key")
        assert config.timeout == 15

    def test_custom_timeout(self):
        config = Configuration(api_key="test-key", timeout=30)
        assert config.timeout == 30

    def test_default_max_queue_size(self):
        config = Configuration(api_key="test-key")
        assert config.max_queue_size == 1000

    def test_validation_missing_api_key(self):
        config = Configuration()
        errors = config.validate()
        assert "api_key is required" in errors
        assert config.is_valid() is False

    def test_validation_with_api_key(self):
        config = Configuration(api_key="test-key")
        errors = config.validate()
        assert len(errors) == 0
        assert config.is_valid() is True

    def test_debug_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_DEBUG", "true")
        config = Configuration(api_key="test-key")
        assert config.debug is True

    def test_before_notify_default_empty(self):
        config = Configuration(api_key="test-key")
        assert config.before_notify == []

    def test_before_notify_with_callbacks(self):
        def callback(notice):
            return True

        config = Configuration(api_key="test-key", before_notify=[callback])
        assert len(config.before_notify) == 1

    # New tests for proxy, SSL, timeouts, and data toggles

    def test_default_open_timeout(self):
        config = Configuration(api_key="test-key")
        assert config.open_timeout == 5

    def test_custom_open_timeout(self):
        config = Configuration(api_key="test-key", open_timeout=10)
        assert config.open_timeout == 10

    def test_open_timeout_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_OPEN_TIMEOUT", "20")
        config = Configuration(api_key="test-key")
        assert config.open_timeout == 20

    def test_proxy_default_none(self):
        config = Configuration(api_key="test-key")
        assert config.proxy is None

    def test_proxy_from_parameter(self):
        config = Configuration(api_key="test-key", proxy="http://proxy.example.com:8080")
        assert config.proxy == "http://proxy.example.com:8080"

    def test_proxy_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_PROXY", "http://env-proxy.example.com:8080")
        config = Configuration(api_key="test-key")
        assert config.proxy == "http://env-proxy.example.com:8080"

    def test_ssl_verify_default_true(self):
        config = Configuration(api_key="test-key")
        assert config.ssl_verify is True

    def test_ssl_verify_disabled_from_parameter(self):
        config = Configuration(api_key="test-key", ssl_verify=False)
        assert config.ssl_verify is False

    def test_ssl_verify_disabled_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_SSL_VERIFY", "false")
        config = Configuration(api_key="test-key")
        assert config.ssl_verify is False

    def test_ssl_verify_disabled_from_environment_zero(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_SSL_VERIFY", "0")
        config = Configuration(api_key="test-key")
        assert config.ssl_verify is False

    def test_ssl_ca_path_default_none(self):
        config = Configuration(api_key="test-key")
        assert config.ssl_ca_path is None

    def test_ssl_ca_path_from_parameter(self):
        config = Configuration(api_key="test-key", ssl_ca_path="/path/to/ca.crt")
        assert config.ssl_ca_path == "/path/to/ca.crt"

    def test_ssl_ca_path_from_environment(self, monkeypatch):
        monkeypatch.setenv("CHECKEND_SSL_CA_PATH", "/env/path/to/ca.crt")
        config = Configuration(api_key="test-key")
        assert config.ssl_ca_path == "/env/path/to/ca.crt"

    def test_send_request_data_default_true(self):
        config = Configuration(api_key="test-key")
        assert config.send_request_data is True

    def test_send_request_data_disabled(self):
        config = Configuration(api_key="test-key", send_request_data=False)
        assert config.send_request_data is False

    def test_send_session_data_default_true(self):
        config = Configuration(api_key="test-key")
        assert config.send_session_data is True

    def test_send_session_data_disabled(self):
        config = Configuration(api_key="test-key", send_session_data=False)
        assert config.send_session_data is False

    def test_send_user_data_default_true(self):
        config = Configuration(api_key="test-key")
        assert config.send_user_data is True

    def test_send_user_data_disabled(self):
        config = Configuration(api_key="test-key", send_user_data=False)
        assert config.send_user_data is False

    def test_default_ignored_exceptions_includes_keyboard_interrupt(self):
        config = Configuration(api_key="test-key")
        assert KeyboardInterrupt in config.ignored_exceptions

    def test_default_ignored_exceptions_includes_system_exit(self):
        config = Configuration(api_key="test-key")
        assert SystemExit in config.ignored_exceptions

    def test_default_ignored_exceptions_includes_django_http404(self):
        config = Configuration(api_key="test-key")
        assert "django.http.Http404" in config.ignored_exceptions

    def test_default_ignored_exceptions_includes_werkzeug_not_found(self):
        config = Configuration(api_key="test-key")
        assert "werkzeug.exceptions.NotFound" in config.ignored_exceptions

    def test_default_ignored_exceptions_includes_fastapi_http_exception(self):
        config = Configuration(api_key="test-key")
        assert "fastapi.exceptions.HTTPException" in config.ignored_exceptions
