"""Flask route blueprints for the web application."""

from .auth import auth_blueprint
from .core import core_blueprint
from .conversations import conversations_blueprint
from .jobs import jobs_blueprint

__all__ = ["auth_blueprint", "core_blueprint", "conversations_blueprint", "jobs_blueprint"]
