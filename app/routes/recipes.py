import sqlite3
from flask import Blueprint, g, jsonify, request


def create_recipes_bp(get_db, recipe_to_dict, authenticate_token, token_required):
    recipes_bp = Blueprint("recipes", __name__)

    # GET ALL RECIPES - Optional JWT authentication
    # Public recipes are visible to everyone.
    # Logged-in users also see their own private recipes.
    @recipes_bp.get("/recipes")
    def list_recipes():
        payload, auth_error = authenticate_token()

        db = get_db()

        if auth_error is None:
            user_id = int(payload["sub"])

            rows = db.execute(
                "SELECT * FROM recipes "
                "WHERE is_public = 1 OR owner_id = ? "
                "ORDER BY id",
                (user_id,)
            ).fetchall()

        else:
            rows = db.execute(
                "SELECT * FROM recipes "
                "WHERE is_public = 1 "
                "ORDER BY id"
            ).fetchall()

        return jsonify([recipe_to_dict(r) for r in rows]), 200


    # GET ONE RECIPE - Public access or private owner access
    @recipes_bp.get("/recipes/<int:recipe_id>")
    def get_recipe(recipe_id):
        db = get_db()

        row = db.execute(
            "SELECT * FROM recipes WHERE id = ?",
            (recipe_id,)
        ).fetchone()

        if row is None:
            return jsonify({"error": "recipe not found"}), 404

        # Anyone can view public recipes
        if row["is_public"] == 1:
            return jsonify(recipe_to_dict(row)), 200

        # Private recipes require authentication
        payload, auth_error = authenticate_token()

        if auth_error is not None:
            return auth_error

        user_id = int(payload["sub"])

        if row["owner_id"] != user_id:
            return jsonify({
                "error": "Forbidden: you do not own this recipe"
            }), 403

        return jsonify(recipe_to_dict(row)), 200


    # CREATE RECIPE - JWT required
    # New recipes are assigned to their authenticated creator.
    @recipes_bp.post("/recipes")
    @token_required
    def create_recipe():
        user_id = g.user_id

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
                "(title, ingredients, instructions, is_public, owner_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    data["title"],
                    data["ingredients"],
                    data.get("instructions", ""),
                    1 if data.get("is_public", True) else 0,
                    user_id,
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


    # UPDATE RECIPE - Owner or admin required
    @recipes_bp.patch("/recipes/<int:recipe_id>")
    @token_required
    def update_recipe(recipe_id):
        user_id = g.user_id
        db = get_db()

        # Find the recipe and its owner
        recipe = db.execute(
            "SELECT owner_id FROM recipes WHERE id = ?",
            (recipe_id,)
        ).fetchone()

        if recipe is None:
            return jsonify({"error": "recipe not found"}), 404

        # Allow the owner OR an admin
        is_owner = recipe["owner_id"] == user_id
        is_admin = g.is_admin

        if not (is_owner or is_admin):
            return jsonify({
                "error": "Forbidden: you do not own this recipe"
            }), 403

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

        # Owner/admin permission was checked above
        values.append(recipe_id)

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

        return jsonify(recipe_to_dict(row)), 200


    # DELETE RECIPE - Owner or admin required
    @recipes_bp.delete("/recipes/<int:recipe_id>")
    @token_required
    def delete_recipe(recipe_id):
        user_id = g.user_id
        db = get_db()

        # Find the recipe and its owner
        recipe = db.execute(
            "SELECT owner_id FROM recipes WHERE id = ?",
            (recipe_id,)
        ).fetchone()

        if recipe is None:
            return jsonify({"error": "recipe not found"}), 404

        # Allow the owner OR an admin
        is_owner = recipe["owner_id"] == user_id
        is_admin = g.is_admin

        if not (is_owner or is_admin):
            return jsonify({
                "error": "Forbidden: you do not own this recipe"
            }), 403

        # Delete after authorization succeeds
        cur = db.execute(
            "DELETE FROM recipes WHERE id = ?",
            (recipe_id,)
        )

        db.commit()

        if cur.rowcount == 0:
            return jsonify({"error": "recipe not found"}), 404

        return "", 204


    return recipes_bp
