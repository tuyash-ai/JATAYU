"""Health-check endpoint."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def health_check():
    """Return a response confirming that the API is running."""
    return jsonify({"success": True, "message": "Credit Card Default Prediction API is running"}), 200
