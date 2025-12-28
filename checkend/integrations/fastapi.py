"""FastAPI/Starlette integration for Checkend SDK."""

from typing import Any, Callable

import checkend


def init_fastapi(app: Any) -> None:
    """
    Initialize Checkend for a FastAPI/Starlette application.

    Usage:
        from fastapi import FastAPI
        import checkend
        from checkend.integrations.fastapi import init_fastapi

        app = FastAPI()
        checkend.configure(api_key='your-api-key')
        init_fastapi(app)

    Args:
        app: FastAPI or Starlette application instance
    """
    app.add_middleware(CheckendMiddleware)


class CheckendMiddleware:
    """
    ASGI middleware for Checkend error reporting.

    Can be used directly with any ASGI application:
        app = CheckendMiddleware(app)
    """

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Clear context at the start of each request
        checkend.clear()

        # Set request context
        self._set_request_context(scope)

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            checkend.notify(exc)
            raise
        finally:
            checkend.clear()

    def _set_request_context(self, scope: dict) -> None:
        """Extract and set request context from ASGI scope."""
        try:
            # Build URL
            scheme = scope.get("scheme", "http")
            server = scope.get("server", ("localhost", 80))
            path = scope.get("path", "/")
            query_string = scope.get("query_string", b"").decode("utf-8")

            url = f"{scheme}://{server[0]}"
            if (scheme == "http" and server[1] != 80) or (scheme == "https" and server[1] != 443):
                url += f":{server[1]}"
            url += path
            if query_string:
                url += f"?{query_string}"

            # Extract headers
            headers = {}
            for key, value in scope.get("headers", []):
                header_name = key.decode("utf-8").title()
                headers[header_name] = value.decode("utf-8")

            request_data = {
                "url": url,
                "method": scope.get("method", "GET"),
                "headers": headers,
            }

            # Parse query params
            if query_string:
                from urllib.parse import parse_qs

                params = parse_qs(query_string)
                # Convert lists to single values where appropriate
                request_data["params"] = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

            checkend.set_request(request_data)
        except Exception:
            pass
