from flask import Blueprint, jsonify, request

from app.services import auth_service as service
from app.extensions import limiter


def create_auth_bp(app, JWT_SECRET):
    auth_bp = Blueprint("auth", __name__)

    @auth_bp.errorhandler(service.AuthError)
    def handle_auth_error(error):
        statuses = {
            "invalid": 400,
            "unauthorized": 401,
            "conflict": 409,
            "registration_failed": 500,
        }

        if error.code == "registration_failed":
            app.logger.error(
                "Registration database error: %s",
                error.detail
            )

        return jsonify({
            "error": error.message
        }), statuses[error.code]

    @auth_bp.post("/register")
    @limiter.limit("3 per minute")
    def register():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "a JSON body is required"
            }), 400

        result = service.register_user(
            data.get("username"),
            data.get("password")
        )

        return jsonify(result), 201

    @auth_bp.post("/login")
    @limiter.limit("5 per minute")
    def login():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "a JSON body is required"
            }), 400

        result = service.authenticate_user(
            data.get("username"),
            data.get("password"),
            JWT_SECRET
        )

        return jsonify(result), 200

    return auth_bp
