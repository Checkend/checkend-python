# Checkend Python SDK

[![CI](https://github.com/Checkend/checkend-python/actions/workflows/ci.yml/badge.svg)](https://github.com/Checkend/checkend-python/actions/workflows/ci.yml)

Python SDK for [Checkend](https://checkend.com) error monitoring. Zero dependencies, async by default.

## Features

- **Zero dependencies** - Uses only Python standard library
- **Async by default** - Non-blocking error sending via background thread
- **Framework integrations** - Django, Flask, FastAPI/Starlette
- **Automatic context** - Request, user, and custom context tracking
- **Sensitive data filtering** - Automatic scrubbing of passwords, tokens, etc.
- **Testing utilities** - Capture errors in tests without sending

## Installation

```bash
pip install checkend
```

## Quick Start

```python
import checkend

# Configure the SDK
checkend.configure(api_key='your-api-key')

# Report an error
try:
    do_something()
except Exception as e:
    checkend.notify(e)
```

## Configuration

```python
import checkend

checkend.configure(
    api_key='your-api-key',              # Required: Your Checkend ingestion key
    endpoint='https://app.checkend.com',  # Optional: Custom endpoint
    environment='production',             # Optional: Auto-detected if not set
    enabled=True,                         # Optional: Enable/disable reporting
    async_send=True,                      # Optional: Async sending (default: True)
    timeout=15,                           # Optional: HTTP timeout in seconds
    filter_keys=['password', 'secret'],   # Optional: Additional keys to filter
    ignored_exceptions=[KeyError],        # Optional: Exceptions to ignore
    debug=False,                          # Optional: Enable debug logging
)
```

### Environment Variables

```bash
CHECKEND_API_KEY=your-api-key
CHECKEND_ENDPOINT=https://your-server.com
CHECKEND_ENVIRONMENT=production
CHECKEND_DEBUG=true
```

## Manual Error Reporting

```python
import checkend

# Basic error reporting
try:
    risky_operation()
except Exception as e:
    checkend.notify(e)

# With additional context
try:
    process_order(order_id)
except Exception as e:
    checkend.notify(
        e,
        context={'order_id': order_id},
        user={'id': user.id, 'email': user.email},
        tags=['orders', 'critical'],
        fingerprint='order-processing-error',
    )

# Synchronous sending (blocks until sent)
response = checkend.notify_sync(e)
print(f"Notice ID: {response['id']}")
```

## Context & User Tracking

```python
import checkend

# Set context for all errors in this request
checkend.set_context({
    'order_id': 12345,
    'feature_flag': 'new-checkout',
})

# Set user information
checkend.set_user({
    'id': user.id,
    'email': user.email,
    'name': user.name,
})

# Set request information
checkend.set_request({
    'url': request.url,
    'method': request.method,
    'headers': dict(request.headers),
})

# Clear all context (call at end of request)
checkend.clear()
```

## Framework Integrations

### Django

```python
# settings.py
MIDDLEWARE = [
    'checkend.integrations.django.DjangoMiddleware',
    # ... other middleware
]

# Configure in settings.py or apps.py
import checkend
checkend.configure(api_key='your-api-key')
```

### Flask

```python
from flask import Flask
import checkend
from checkend.integrations.flask import init_flask

app = Flask(__name__)
checkend.configure(api_key='your-api-key')
init_flask(app)
```

### FastAPI

```python
from fastapi import FastAPI
import checkend
from checkend.integrations.fastapi import init_fastapi

app = FastAPI()
checkend.configure(api_key='your-api-key')
init_fastapi(app)
```

## Testing

Use the `Testing` class to capture errors without sending them:

```python
import checkend
from checkend import Testing

def test_error_reporting():
    # Enable testing mode
    Testing.setup()
    checkend.configure(api_key='test-key')

    try:
        # Trigger an error
        raise ValueError("Test error")
    except Exception as e:
        checkend.notify(e)

    # Assert on captured notices
    assert Testing.has_notices()
    assert Testing.notice_count() == 1
    notices = Testing.notices()
    assert notices[0].error_class == 'ValueError'

    # Clean up
    Testing.teardown()
    checkend.reset()
```

## Filtering Sensitive Data

By default, these keys are filtered: `password`, `secret`, `token`, `api_key`, `authorization`, `credit_card`, `cvv`, `ssn`, etc.

Add custom keys:

```python
checkend.configure(
    api_key='your-api-key',
    filter_keys=['custom_secret', 'internal_token'],
)
```

Filtered values appear as `[FILTERED]` in the dashboard.

## Ignoring Exceptions

```python
checkend.configure(
    api_key='your-api-key',
    ignored_exceptions=[
        KeyboardInterrupt,
        SystemExit,
        'MyCustomException',
        'django.http.Http404',
    ],
)
```

## Before Notify Callbacks

```python
def add_extra_context(notice):
    notice.context['server'] = 'web-1'
    return True  # Return False to skip sending

def filter_specific_errors(notice):
    if 'ignore-me' in notice.message:
        return False  # Don't send this error
    return True

checkend.configure(
    api_key='your-api-key',
    before_notify=[add_extra_context, filter_specific_errors],
)
```

## Graceful Shutdown

The SDK automatically flushes pending notices on program exit. For manual control:

```python
# Wait for pending notices to send
checkend.flush(timeout=10)

# Stop the worker thread
checkend.stop(timeout=5)
```

## Requirements

- Python 3.9+
- No external dependencies

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=checkend

# Lint
ruff check .
ruff format .
```

## License

MIT License - see [LICENSE](LICENSE) for details.
