import os
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


def create_app(database="recipes.db"):
    # Load environment variables from .env
    load_dotenv()

    DATABASE = database

    app = Flask(__name__)

    JWT_SECRET = os.environ.get("JWT_SECRET")

    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET is missing from your .env file")


    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(DATABASE)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
        return g.db


    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop("db", None)
        if db is not None:
            db.close()


    def recipe_to_dict(row):
        return {
            "id": row["id"],
            "title": row["title"],
            "ingredients": row["ingredients"],
            "instructions": row["instructions"],
            "is_public": bool(row["is_public"]),
        }


    # JWT AUTHENTICATION
    # Expired or invalid tokens return 401 Unauthorized.
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
                JWT_SECRET,
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


    # REUSABLE AUTHENTICATION DECORATOR
    # Protected routes get the authenticated user's ID and current role.
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

            db = get_db()
            user = db.execute(
                "SELECT role FROM users WHERE id = ?",
                (user_id,)
            ).fetchone()

            if user is None:
                return jsonify({"error": "Invalid user"}), 401

            g.user_id = user_id
            g.is_admin = user["role"] == "admin"

            return f(*args, **kwargs)

        return decorated


    @app.get("/")
    def hello():
        return jsonify({
            "message": "Recipe Box API",
            "recipes": "/recipes"
        })



    from .routes.auth import create_auth_bp
    from .routes.recipes import create_recipes_bp

    auth_bp = create_auth_bp(app, get_db, JWT_SECRET)

    recipes_bp = create_recipes_bp(
        get_db,
        recipe_to_dict,
        authenticate_token,
        token_required,
    )

    app.register_blueprint(auth_bp, url_prefix="/")
    app.register_blueprint(recipes_bp, url_prefix="/")

    # LOGOUT - Stateless JWT
    # Logout is handled by the client deleting its stored token.
    # The server does not maintain or clear a login session.
    # A copied token remains valid until it expires unless
    # server-side token revocation is implemented.

    return app
