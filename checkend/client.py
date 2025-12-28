"""HTTP client for sending notices to Checkend."""

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Optional

from checkend.configuration import Configuration
from checkend.notice import Notice
from checkend.version import VERSION


class Client:
    """HTTP client for the Checkend API."""

    def __init__(self, configuration: Configuration):
        self.configuration = configuration
        self.endpoint = f"{configuration.endpoint}/ingest/v1/errors"
        self._opener: Optional[urllib.request.OpenerDirector] = None

    def send(self, notice: Notice) -> Optional[dict[str, Any]]:
        """
        Send a notice to Checkend.

        Returns:
            Response dict with 'id' and 'problem_id' on success, None on failure
        """
        if not self.configuration.api_key:
            self.configuration.log("error", "Cannot send notice: api_key not configured")
            return None

        payload = notice.to_payload()

        # Apply data sending toggles
        if not self.configuration.send_request_data and "request" in payload:
            del payload["request"]

        if not self.configuration.send_user_data and "user" in payload:
            del payload["user"]

        # Note: session data is typically part of request, but we can filter it separately
        # if included in the payload
        if not self.configuration.send_session_data:
            if "request" in payload and "session" in payload.get("request", {}):
                del payload["request"]["session"]

        try:
            response = self._post(payload)
            self.configuration.log("debug", f"Notice sent successfully: {response}")
            return response
        except urllib.error.HTTPError as e:
            self._handle_http_error(e)
            return None
        except urllib.error.URLError as e:
            self.configuration.log("error", f"Network error: {e.reason}")
            return None
        except Exception as e:
            self.configuration.log("error", f"Unexpected error sending notice: {e}")
            return None

    def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Build SSL context based on configuration."""
        if not self.configuration.ssl_verify:
            # Create unverified context (disable SSL verification)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            return context

        if self.configuration.ssl_ca_path:
            # Create context with custom CA certificate
            context = ssl.create_default_context()
            context.load_verify_locations(self.configuration.ssl_ca_path)
            return context

        # Use default SSL context
        return None

    def _get_opener(self) -> urllib.request.OpenerDirector:
        """Get or create URL opener with proxy support."""
        if self._opener is not None:
            return self._opener

        handlers = []

        # Add proxy handler if configured
        if self.configuration.proxy:
            proxy_handler = urllib.request.ProxyHandler(
                {
                    "http": self.configuration.proxy,
                    "https": self.configuration.proxy,
                }
            )
            handlers.append(proxy_handler)

        # Add HTTPS handler with SSL context
        ssl_context = self._get_ssl_context()
        if ssl_context:
            https_handler = urllib.request.HTTPSHandler(context=ssl_context)
            handlers.append(https_handler)

        if handlers:
            self._opener = urllib.request.build_opener(*handlers)
        else:
            self._opener = urllib.request.build_opener()

        return self._opener

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a POST request to the API."""
        data = json.dumps(payload).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Checkend-Ingestion-Key": self.configuration.api_key,
            "User-Agent": f"checkend-python/{VERSION}",
        }

        request = urllib.request.Request(
            self.endpoint,
            data=data,
            headers=headers,
            method="POST",
        )

        # Use open_timeout for connection, timeout for read
        # Note: urllib doesn't support separate timeouts, so we use open_timeout
        # as a general timeout for the request
        timeout = self.configuration.open_timeout

        # Get opener with proxy/SSL support
        opener = self._get_opener()

        # If no custom handlers, use urlopen directly with SSL context
        ssl_context = self._get_ssl_context()
        if not self.configuration.proxy and ssl_context:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
                context=ssl_context,
            ) as response:
                response_data = response.read().decode("utf-8")
                return json.loads(response_data)
        elif self.configuration.proxy:
            # Use opener for proxy support
            with opener.open(request, timeout=timeout) as response:
                response_data = response.read().decode("utf-8")
                return json.loads(response_data)
        else:
            # Default case - no proxy, no custom SSL
            with urllib.request.urlopen(
                request,
                timeout=self.configuration.timeout,
            ) as response:
                response_data = response.read().decode("utf-8")
                return json.loads(response_data)

    def _handle_http_error(self, error: urllib.error.HTTPError) -> None:
        """Handle HTTP errors from the API."""
        status_code = error.code

        if status_code == 401:
            self.configuration.log("error", "Authentication failed: invalid API key")
        elif status_code == 422:
            try:
                body = error.read().decode("utf-8")
                self.configuration.log("error", f"Validation error: {body}")
            except Exception:
                self.configuration.log("error", "Validation error")
        elif status_code == 429:
            self.configuration.log("warning", "Rate limited by Checkend API")
        elif status_code >= 500:
            self.configuration.log("error", f"Server error: {status_code}")
        else:
            self.configuration.log("error", f"HTTP error: {status_code}")
