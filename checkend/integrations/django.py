"""Django integration for Checkend SDK."""

from typing import Any, Callable

import checkend


class DjangoMiddleware:
    """
    Django middleware for Checkend error reporting.

    Add to your MIDDLEWARE setting:
        MIDDLEWARE = [
            'checkend.integrations.django.DjangoMiddleware',
            # ... other middleware
        ]

    Configure Checkend in your settings.py:
        import checkend
        checkend.configure(api_key='your-api-key')
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        # Clear context at the start of each request
        checkend.clear()

        # Set request context
        self._set_request_context(request)

        # Set user context if available
        self._set_user_context(request)

        try:
            response = self.get_response(request)
            return response
        finally:
            # Clear context after request
            checkend.clear()

    def process_exception(self, request: Any, exception: Exception) -> None:
        """Handle uncaught exceptions."""
        checkend.notify(exception)
        # Return None to let Django continue with default exception handling

    def _set_request_context(self, request: Any) -> None:
        """Extract and set request context."""
        try:
            request_data = {
                "url": request.build_absolute_uri(),
                "method": request.method,
                "headers": self._extract_headers(request),
            }

            # Add query parameters
            if hasattr(request, "GET") and request.GET:
                request_data["params"] = dict(request.GET)

            # Add request ID if available
            request_id = getattr(request, "id", None) or request.META.get("HTTP_X_REQUEST_ID")
            if request_id:
                checkend.set_context({"request_id": request_id})

            checkend.set_request(request_data)
        except Exception:
            pass

    def _set_user_context(self, request: Any) -> None:
        """Extract and set user context."""
        try:
            user = getattr(request, "user", None)
            if user and hasattr(user, "is_authenticated"):
                if user.is_authenticated:
                    user_data = {"id": user.pk}
                    if hasattr(user, "email"):
                        user_data["email"] = user.email
                    if hasattr(user, "get_full_name"):
                        name = user.get_full_name()
                        if name:
                            user_data["name"] = name
                    checkend.set_user(user_data)
        except Exception:
            pass

    def _extract_headers(self, request: Any) -> dict:
        """Extract relevant headers from request."""
        headers = {}
        header_keys = [
            "HTTP_USER_AGENT",
            "HTTP_ACCEPT",
            "HTTP_ACCEPT_LANGUAGE",
            "HTTP_REFERER",
            "CONTENT_TYPE",
            "CONTENT_LENGTH",
        ]

        for key in header_keys:
            value = request.META.get(key)
            if value:
                # Convert HTTP_USER_AGENT to User-Agent format
                header_name = key.replace("HTTP_", "").replace("_", "-").title()
                headers[header_name] = value

        return headers
