"""Configuration for the Checkend SDK."""

import os
import sys
from typing import Any, Callable, Optional, Union

DEFAULT_ENDPOINT = "https://app.checkend.com"
DEFAULT_TIMEOUT = 15
DEFAULT_OPEN_TIMEOUT = 5
DEFAULT_MAX_QUEUE_SIZE = 1000

DEFAULT_FILTER_KEYS = [
    "password",
    "password_confirmation",
    "secret",
    "secret_key",
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "authorization",
    "token",
    "credit_card",
    "card_number",
    "cvv",
    "cvc",
    "ssn",
    "social_security",
]

DEFAULT_IGNORED_EXCEPTIONS: list[Union[type[BaseException], str]] = [
    KeyboardInterrupt,
    SystemExit,
    # Django HTTP exceptions
    "django.http.Http404",
    "django.core.exceptions.PermissionDenied",
    "django.core.exceptions.SuspiciousOperation",
    # Flask/Werkzeug HTTP exceptions
    "werkzeug.exceptions.NotFound",
    "werkzeug.exceptions.MethodNotAllowed",
    "werkzeug.exceptions.Forbidden",
    # FastAPI/Starlette HTTP exceptions
    "starlette.exceptions.HTTPException",
    "fastapi.exceptions.HTTPException",
]


class Configuration:
    """Configuration for the Checkend SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        environment: Optional[str] = None,
        enabled: Optional[bool] = None,
        async_send: bool = True,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        open_timeout: int = DEFAULT_OPEN_TIMEOUT,
        filter_keys: Optional[list[str]] = None,
        ignored_exceptions: Optional[list[Union[type[BaseException], str]]] = None,
        before_notify: Optional[list[Callable]] = None,
        logger: Optional[Any] = None,
        debug: bool = False,
        # Proxy and SSL settings
        proxy: Optional[str] = None,
        ssl_verify: bool = True,
        ssl_ca_path: Optional[str] = None,
        # Data sending toggles
        send_request_data: bool = True,
        send_session_data: bool = True,
        send_user_data: bool = True,
        **kwargs,
    ):
        # API key from parameter or environment
        self.api_key = api_key or os.environ.get("CHECKEND_API_KEY")

        # Endpoint from parameter or environment
        self.endpoint = endpoint or os.environ.get("CHECKEND_ENDPOINT") or DEFAULT_ENDPOINT

        # Environment detection
        self.environment = (
            environment or os.environ.get("CHECKEND_ENVIRONMENT") or self._detect_environment()
        )

        # Enable/disable based on environment
        if enabled is not None:
            self.enabled = enabled
        else:
            self.enabled = self.environment in ("production", "staging")

        # Async settings
        self.async_send = async_send
        self.max_queue_size = max_queue_size

        # HTTP settings
        self.timeout = timeout
        self.open_timeout = (
            open_timeout
            if open_timeout != DEFAULT_OPEN_TIMEOUT
            else int(os.environ.get("CHECKEND_OPEN_TIMEOUT", DEFAULT_OPEN_TIMEOUT))
        )

        # Proxy settings
        self.proxy = proxy or os.environ.get("CHECKEND_PROXY")

        # SSL settings
        self.ssl_verify = ssl_verify
        if not ssl_verify:
            pass  # Use provided value
        else:
            ssl_verify_env = os.environ.get("CHECKEND_SSL_VERIFY", "").lower()
            if ssl_verify_env in ("false", "0", "no"):
                self.ssl_verify = False
        self.ssl_ca_path = ssl_ca_path or os.environ.get("CHECKEND_SSL_CA_PATH")

        # Data sending toggles
        self.send_request_data = send_request_data
        self.send_session_data = send_session_data
        self.send_user_data = send_user_data

        # Filter settings
        self.filter_keys = list(DEFAULT_FILTER_KEYS)
        if filter_keys:
            self.filter_keys.extend(filter_keys)

        # Ignored exceptions
        self.ignored_exceptions = list(DEFAULT_IGNORED_EXCEPTIONS)
        if ignored_exceptions:
            self.ignored_exceptions.extend(ignored_exceptions)

        # Callbacks
        self.before_notify = before_notify or []

        # Logging
        self.logger = logger
        self.debug = debug or os.environ.get("CHECKEND_DEBUG", "").lower() in ("true", "1", "yes")

    def _detect_environment(self) -> str:
        """Detect the current environment from common environment variables."""
        env_vars = [
            "PYTHON_ENV",
            "ENVIRONMENT",
            "ENV",
            "RAILS_ENV",  # For mixed environments
            "NODE_ENV",
            "DJANGO_SETTINGS_MODULE",
        ]

        for var in env_vars:
            value = os.environ.get(var)
            if value:
                # Handle Django settings module
                if var == "DJANGO_SETTINGS_MODULE":
                    if "production" in value.lower():
                        return "production"
                    elif "staging" in value.lower():
                        return "staging"
                    elif "test" in value.lower():
                        return "test"
                    else:
                        return "development"
                return value

        return "development"

    def log(self, level: str, message: str) -> None:
        """Log a message if logging is enabled."""
        if not self.debug and level == "debug":
            return

        if self.logger:
            log_method = getattr(self.logger, level, None)
            if log_method:
                log_method(f"[Checkend] {message}")
        elif self.debug:
            print(f"[Checkend] [{level.upper()}] {message}", file=sys.stderr)

    def validate(self) -> list[str]:
        """Validate the configuration and return a list of errors."""
        errors = []

        if not self.api_key:
            errors.append("api_key is required")

        if not self.endpoint:
            errors.append("endpoint is required")

        return errors

    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return len(self.validate()) == 0


# Module-level configuration instance
_configuration: Optional[Configuration] = None


def configure(**options) -> Configuration:
    """Configure the Checkend SDK."""
    global _configuration
    _configuration = Configuration(**options)
    return _configuration


def get_configuration() -> Optional[Configuration]:
    """Get the current configuration."""
    return _configuration
