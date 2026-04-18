"""Async job polling routes for the Flask web app."""

from flask import Blueprint, jsonify

from src.services.async_job_service import AsyncJobNotFoundError
from src.webapp import get_app_runtime

try:
    from src.auth import token_required
except ImportError:
    token_required = lambda f: f


jobs_blueprint = Blueprint("jobs", __name__)


@jobs_blueprint.route("/api/jobs/<job_id>", methods=["GET"])
@token_required
def get_job(job_id):
    """Return the current status of an async job."""
    try:
        runtime = get_app_runtime()
        payload = runtime._get_async_job_service().get_job_status(job_id)
        return jsonify(payload)
    except AsyncJobNotFoundError:
        return jsonify({"error": "Job not found", "job_id": job_id}), 404
    except Exception as error:
        return jsonify({"error": str(error)}), 500
