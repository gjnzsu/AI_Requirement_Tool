"""Core page and health routes for the Flask web app."""

from flask import Blueprint, render_template


core_blueprint = Blueprint("core", __name__)


@core_blueprint.route("/api/health")
def health():
    """Health check endpoint for k8s probes."""
    return {"status": "ok"}, 200


@core_blueprint.route("/")
def index():
    """Serve the main chat interface."""
    return render_template("index.html")


@core_blueprint.route("/login")
def login_page():
    """Serve the login page."""
    return render_template("login.html")