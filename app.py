import os
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

# Load environment variables from .env
load_dotenv()

DATABASE = "recipes.db"

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


@app.get("/")
def hello():
    return jsonify({
        "message": "Recipe Box API",
        "recipes": "/recipes"
    })


# REGISTER
@app.post("/register")
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
@app.post("/login")
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "a JSON body is required"}), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({
            "error": "username and password are required"
        }), 400

    db = get_db()

    user = db.execute(
        "SELECT id, username, password_hash "
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


# GET ALL RECIPES - No authentication required
@app.get("/recipes")
def list_recipes():
    rows = get_db().execute(
        "SELECT * FROM recipes ORDER BY id"
    ).fetchall()

    return jsonify([recipe_to_dict(r) for r in rows])


# GET ONE RECIPE - No authentication required
@app.get("/recipes/<int:recipe_id>")
def get_recipe(recipe_id):
    row = get_db().execute(
        "SELECT * FROM recipes WHERE id = ?",
        (recipe_id,)
    ).fetchone()

    if row is None:
        return jsonify({"error": "recipe not found"}), 404

    return jsonify(recipe_to_dict(row))


# CREATE RECIPE - JWT required
@app.post("/recipes")
def create_recipe():
    payload, auth_error = authenticate_token()

    if auth_error is not None:
        return auth_error

    # Authenticated user ID
    user_id = payload["sub"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or (
        not data.get("title") or not data.get("ingredients")
    ):
        return jsonify({
            "error": "title and ingredients are required"
        }), 400

    db = get_db()

    try:
        cur = db.execute(
            "INSERT INTO recipes "
            "(title, ingredients, instructions, is_public) "
            "VALUES (?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data.get("instructions", ""),
                1 if data.get("is_public", True) else 0,
            ),
        )
        db.commit()

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "a recipe with that title already exists"
        }), 409

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (cur.lastrowid,)
    ).fetchone()

    return jsonify(recipe_to_dict(row)), 201


# UPDATE RECIPE - JWT required
@app.patch("/recipes/<int:recipe_id>")
def update_recipe(recipe_id):
    payload, auth_error = authenticate_token()

    if auth_error is not None:
        return auth_error

    # Authenticated user ID
    user_id = payload["sub"]

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "error": "a JSON body is required"
        }), 400

    fields, values = [], []

    for column in ("title", "ingredients", "instructions"):
        if column in data:
            fields.append(f"{column} = ?")
            values.append(data[column])

    if "is_public" in data:
        fields.append("is_public = ?")
        values.append(1 if data["is_public"] else 0)

    if not fields:
        return jsonify({"error": "nothing to update"}), 400

    values.append(recipe_id)

    db = get_db()

    try:
        cur = db.execute(
            f"UPDATE recipes SET {', '.join(fields)} "
            "WHERE id = ?",
            values
        )
        db.commit()

    except sqlite3.IntegrityError:
        return jsonify({
            "error": "a recipe with that title already exists"
        }), 409

    if cur.rowcount == 0:
        return jsonify({"error": "recipe not found"}), 404

    row = db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (recipe_id,)
    ).fetchone()

    return jsonify(recipe_to_dict(row))


# DELETE RECIPE - JWT required
@app.delete("/recipes/<int:recipe_id>")
def delete_recipe(recipe_id):
    payload, auth_error = authenticate_token()

    if auth_error is not None:
        return auth_error

    # Authenticated user ID
    user_id = payload["sub"]

    db = get_db()

    cur = db.execute(
        "DELETE FROM recipes WHERE id = ?",
        (recipe_id,)
    )

    db.commit()

    if cur.rowcount == 0:
        return jsonify({"error": "recipe not found"}), 404

    return "", 204


# LOGOUT - Stateless JWT
# Logout is handled by the client deleting its stored token.
# The server does not maintain or clear a login session.
# A copied token remains valid until it expires unless
# server-side token revocation is implemented.


if __name__ == "__main__":
    app.run(debug=True, port=5001)

