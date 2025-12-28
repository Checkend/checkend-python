"""Flask integration for Checkend SDK."""

from typing import Any, Optional

import checkend


def init_flask(app: Any) -> None:
    """
    Initialize Checkend for a Flask application.

    Usage:
        from flask import Flask
        import checkend
        from checkend.integrations.flask import init_flask

        app = Flask(__name__)
        checkend.configure(api_key='your-api-key')
        init_flask(app)

    Args:
        app: Flask application instance
    """

    @app.before_request
    def checkend_before_request() -> None:
        """Set up context before each request."""
        from flask import request

        # Clear context at the start of each request
        checkend.clear()

        # Set request context
        try:
            request_data = {
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
            }

            if request.args:
                request_data["params"] = dict(request.args)

            checkend.set_request(request_data)
        except Exception:
            pass

    @app.after_request
    def checkend_after_request(response: Any) -> Any:
        """Clean up after each request."""
        checkend.clear()
        return response

    @app.teardown_request
    def checkend_teardown_request(exception: Optional[BaseException]) -> None:
        """Handle exceptions and clean up."""
        if exception is not None:
            checkend.notify(exception)
        checkend.clear()

    # Register error handler for unhandled exceptions
    @app.errorhandler(Exception)
    def checkend_error_handler(exception: Exception) -> Any:
        """Handle uncaught exceptions."""
        checkend.notify(exception)
        # Re-raise to let Flask handle the error response
        raise exception
