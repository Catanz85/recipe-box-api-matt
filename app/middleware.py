from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from app.data.database import get_db
from app.data.users import get_role


def authenticate_token():
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None, (
            jsonify({"error": "Missing or invalid token"}), 401
        )

    token = auth_header.split(" ", 1)[1]

    if not token.strip():
        return None, (
            jsonify({"error": "Missing or invalid token"}), 401
        )

    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET"],
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )

    except jwt.ExpiredSignatureError:
        return None, (
            jsonify({
                "error": "Token expired. Please log in again."
            }), 401
        )

    except jwt.InvalidTokenError:
        return None, (
            jsonify({"error": "Invalid token"}), 401
        )

    return payload, None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        payload, auth_error = authenticate_token()

        if auth_error is not None:
            return auth_error

        try:
            user_id = int(payload["sub"])
        except (ValueError, TypeError, KeyError):
            return jsonify({"error": "Invalid token"}), 401

        user = get_role(get_db(), user_id)

        if user is None:
            return jsonify({"error": "Invalid user"}), 401

        g.user_id = user_id
        g.is_admin = user["role"] == "admin"

        return f(*args, **kwargs)

    return decorated
