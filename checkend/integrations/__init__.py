"""Framework integrations for Checkend SDK."""

# Background job integrations (optional dependencies)
from checkend.integrations.celery import CheckendTask, init_celery
from checkend.integrations.django import DjangoMiddleware
from checkend.integrations.dramatiq import CheckendMiddleware as DramatiqMiddleware
from checkend.integrations.dramatiq import init_dramatiq
from checkend.integrations.fastapi import init_fastapi
from checkend.integrations.flask import init_flask
from checkend.integrations.rq import CheckendWorker, init_rq, rq_exception_handler

__all__ = [
    # Web framework integrations
    "DjangoMiddleware",
    "init_flask",
    "init_fastapi",
    # Background job integrations
    "init_celery",
    "CheckendTask",
    "init_rq",
    "rq_exception_handler",
    "CheckendWorker",
    "init_dramatiq",
    "DramatiqMiddleware",
]
