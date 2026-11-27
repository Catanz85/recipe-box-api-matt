import sqlite3
from datetime import datetime, timedelta, timezone
import jwt
from flask import Blueprint, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


def create_auth_bp(app, get_db, JWT_SECRET):
    auth_bp = Blueprint("auth", __name__)

    # REGISTER
    @auth_bp.post("/register")
    def register():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({"error": "a JSON body is required"}), 400

        username = data.get("username")
        password = data.get("password")

        if (
            not isinstance(username, str)
            or not username.strip()
            or not isinstance(password, str)
            or not password
        ):
            return jsonify({
                "error": "username and password are required"
            }), 400

        username = username.strip()

        # Temporary email for classroom testing
        email = f"{username}@example.com"

        db = get_db()

        try:
            cur = db.execute(
                "INSERT INTO users (username, email, password_hash) "
                "VALUES (?, ?, ?)",
                (
                    username,
                    email,
                    generate_password_hash(password),
                ),
            )
            db.commit()

        except sqlite3.IntegrityError as e:
            error = str(e)

            if "users.username" in error or "users.email" in error:
                return jsonify({
                    "error": "username already exists"
                }), 409

            app.logger.error("Registration database error: %s", error)

            return jsonify({
                "error": "registration failed"
            }), 500

        return jsonify({
            "id": cur.lastrowid,
            "username": username,
        }), 201


    # LOGIN - Verify password and generate JWT
    @auth_bp.post("/login")
    def login():
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "a JSON body is required"
            }), 400

        username = data.get("username")
        password = data.get("password")

        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify({
                "error": "username and password are required"
            }), 400

        db = get_db()

        # Include role in login query
        user = db.execute(
            "SELECT id, username, password_hash, role "
            "FROM users WHERE username = ?",
            (username,),
        ).fetchone()

        if not user or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({"error": "Invalid credentials"}), 401

        # Create JWT token valid for one hour
        now = datetime.now(timezone.utc)

        payload = {
            "sub": str(user["id"]),
            "username": user["username"],
            "role": user["role"],
            "iat": now,
            "exp": now + timedelta(hours=1),
        }

        token = jwt.encode(
            payload,
            JWT_SECRET,
            algorithm="HS256"
        )

        return jsonify({
            "id": user["id"],
            "username": user["username"],
            "access_token": token,
            "token_type": "Bearer",
        }), 200


    return auth_bp
