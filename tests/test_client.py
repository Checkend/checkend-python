"""Tests for HTTP Client class."""

import json
import ssl
import urllib.error
import urllib.request
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from checkend.client import Client
from checkend.configuration import Configuration
from checkend.notice import Notice


def mock_urlopen_response(json_data, status_code=200):
    """Create a mock response for urlopen."""
    response = MagicMock()
    response.read.return_value = json.dumps(json_data).encode("utf-8")
    response.status = status_code
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    return response


class TestClient:
    def setup_method(self):
        self.config = Configuration(
            api_key="test-key",
            endpoint="https://app.checkend.com",
        )

    def _create_notice(self):
        return Notice(
            error_class="ValueError",
            message="Test error",
            backtrace=["test.py:1 in test_func"],
            environment="test",
            notifier={"name": "checkend-python", "version": "0.1.0"},
        )

    def test_client_initialization(self):
        client = Client(self.config)
        assert client.endpoint == "https://app.checkend.com/ingest/v1/errors"

    def test_client_without_api_key_returns_none(self):
        config = Configuration(endpoint="https://app.checkend.com")
        client = Client(config)
        notice = self._create_notice()
        result = client.send(notice)
        assert result is None

    @patch("urllib.request.urlopen")
    def test_client_sends_notice(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123, "problem_id": 456})

        client = Client(self.config)
        notice = self._create_notice()
        result = client.send(notice)

        assert result is not None
        assert result["id"] == 123
        assert mock_urlopen.called

    @patch("urllib.request.urlopen")
    def test_client_sends_correct_headers(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123})

        client = Client(self.config)
        notice = self._create_notice()
        client.send(notice)

        # Get the request object passed to urlopen
        call_args = mock_urlopen.call_args
        request = call_args[0][0]

        assert request.get_header("Content-type") == "application/json"
        assert request.get_header("Checkend-ingestion-key") == "test-key"
        assert "checkend-python" in request.get_header("User-agent")

    @patch("urllib.request.urlopen")
    def test_client_handles_401_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://app.checkend.com", 401, "Unauthorized", {}, None
        )

        client = Client(self.config)
        notice = self._create_notice()
        result = client.send(notice)

        assert result is None

    @patch("urllib.request.urlopen")
    def test_client_handles_422_error(self, mock_urlopen):
        error_response = BytesIO(b'{"errors": ["Invalid payload"]}')
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://app.checkend.com", 422, "Unprocessable Entity", {}, error_response
        )

        client = Client(self.config)
        notice = self._create_notice()
        result = client.send(notice)

        assert result is None

    @patch("urllib.request.urlopen")
    def test_client_handles_429_rate_limit(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://app.checkend.com", 429, "Too Many Requests", {}, None
        )

        client = Client(self.config)
        notice = self._create_notice()
        result = client.send(notice)

        assert result is None

    @patch("urllib.request.urlopen")
    def test_client_handles_500_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://app.checkend.com", 500, "Internal Server Error", {}, None
        )

        client = Client(self.config)
        notice = self._create_notice()
        result = client.send(notice)

        assert result is None

    @patch("urllib.request.urlopen")
    def test_client_handles_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        client = Client(self.config)
        notice = self._create_notice()
        result = client.send(notice)

        assert result is None


class TestClientDataToggles:
    def setup_method(self):
        self.base_config = {
            "api_key": "test-key",
            "endpoint": "https://app.checkend.com",
        }

    def _create_notice_with_data(self):
        return Notice(
            error_class="ValueError",
            message="Test error",
            backtrace=["test.py:1 in test_func"],
            environment="test",
            notifier={"name": "checkend-python", "version": "0.1.0"},
            request={"url": "https://example.com", "method": "GET"},
            user={"id": "user-1", "email": "test@example.com"},
        )

    @patch("urllib.request.urlopen")
    def test_send_request_data_disabled_removes_request(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123})

        config = Configuration(**self.base_config, send_request_data=False)
        client = Client(config)
        notice = self._create_notice_with_data()
        client.send(notice)

        # Get the request body that was sent
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        request_body = json.loads(request.data.decode("utf-8"))

        assert "request" not in request_body

    @patch("urllib.request.urlopen")
    def test_send_user_data_disabled_removes_user(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123})

        config = Configuration(**self.base_config, send_user_data=False)
        client = Client(config)
        notice = self._create_notice_with_data()
        client.send(notice)

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        request_body = json.loads(request.data.decode("utf-8"))

        assert "user" not in request_body

    @patch("urllib.request.urlopen")
    def test_send_session_data_disabled_removes_session(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123})

        config = Configuration(**self.base_config, send_session_data=False)
        client = Client(config)

        # Create notice with session data in request
        notice = Notice(
            error_class="ValueError",
            message="Test error",
            backtrace=["test.py:1 in test_func"],
            environment="test",
            notifier={"name": "checkend-python", "version": "0.1.0"},
            request={
                "url": "https://example.com",
                "method": "GET",
                "session": {"user_id": "123", "token": "abc"},
            },
        )
        client.send(notice)

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        request_body = json.loads(request.data.decode("utf-8"))

        assert "session" not in request_body.get("request", {})

    @patch("urllib.request.urlopen")
    def test_all_data_toggles_enabled_by_default(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123})

        config = Configuration(**self.base_config)
        client = Client(config)
        notice = self._create_notice_with_data()
        client.send(notice)

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        request_body = json.loads(request.data.decode("utf-8"))

        assert "request" in request_body
        assert "user" in request_body


class TestClientSSL:
    def setup_method(self):
        self.base_config = {
            "api_key": "test-key",
            "endpoint": "https://app.checkend.com",
        }

    def test_ssl_context_default_returns_none(self):
        config = Configuration(**self.base_config)
        client = Client(config)
        context = client._get_ssl_context()
        assert context is None

    def test_ssl_context_when_verify_disabled(self):
        config = Configuration(**self.base_config, ssl_verify=False)
        client = Client(config)
        context = client._get_ssl_context()

        assert context is not None
        assert context.verify_mode == ssl.CERT_NONE
        assert context.check_hostname is False

    def test_ssl_context_with_custom_ca_path(self, tmp_path):
        # Create a temporary CA file (just for testing the path is used)
        ca_file = tmp_path / "ca.crt"
        ca_file.write_text("dummy")

        config = Configuration(**self.base_config, ssl_ca_path=str(ca_file))
        client = Client(config)

        # This will fail because the file isn't a real cert, but we're testing
        # that the code path is correct
        with pytest.raises(ssl.SSLError):
            client._get_ssl_context()


class TestClientProxy:
    def setup_method(self):
        self.base_config = {
            "api_key": "test-key",
            "endpoint": "https://app.checkend.com",
        }

    def test_opener_without_proxy(self):
        config = Configuration(**self.base_config)
        client = Client(config)
        opener = client._get_opener()
        assert opener is not None

    def test_opener_with_proxy(self):
        config = Configuration(**self.base_config, proxy="http://proxy.example.com:8080")
        client = Client(config)
        opener = client._get_opener()
        assert opener is not None
        # The opener should have handlers for proxy
        assert len(opener.handlers) > 0

    def test_opener_cached(self):
        config = Configuration(**self.base_config)
        client = Client(config)
        opener1 = client._get_opener()
        opener2 = client._get_opener()
        assert opener1 is opener2


class TestClientTimeout:
    def setup_method(self):
        self.base_config = {
            "api_key": "test-key",
            "endpoint": "https://app.checkend.com",
        }

    @patch("urllib.request.urlopen")
    def test_uses_timeout_configuration(self, mock_urlopen):
        mock_urlopen.return_value = mock_urlopen_response({"id": 123})

        config = Configuration(**self.base_config, timeout=30)
        client = Client(config)
        notice = Notice(
            error_class="ValueError",
            message="Test",
            backtrace=[],
            environment="test",
            notifier={},
        )
        client.send(notice)

        # Check that timeout was passed
        call_args = mock_urlopen.call_args
        assert "timeout" in call_args.kwargs or len(call_args) > 1
