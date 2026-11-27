from flask import Blueprint, g, jsonify, request
from app.extensions import cache
from app.services import recipes as service


PUBLIC_RECIPE_LIST_CACHE_KEY = "public_recipe_list"
PUBLIC_RECIPE_LIST_CACHE_TIMEOUT = 30


def create_recipes_bp(authenticate_token, token_required):
    recipes_bp = Blueprint("recipes", __name__)

    @recipes_bp.errorhandler(service.RecipeError)
    def handle_recipe_error(error):
        statuses = {
            "invalid": 400,
            "forbidden": 403,
            "not_found": 404,
            "conflict": 409,
        }
        return jsonify({"error": error.message}), statuses[error.code]

    @recipes_bp.get("/recipes")
    def list_recipes():
        payload, auth_error = authenticate_token()
        user_id = int(payload["sub"]) if auth_error is None else None

        if user_id is None:
            result = cache.get(PUBLIC_RECIPE_LIST_CACHE_KEY)
            if result is None:
                result = service.list_recipes()
                cache.set(
                    PUBLIC_RECIPE_LIST_CACHE_KEY,
                    result,
                    timeout=PUBLIC_RECIPE_LIST_CACHE_TIMEOUT
                )
        else:
            result = service.list_recipes(user_id)

        return jsonify(result), 200

    @recipes_bp.get("/recipes/count")
    def count_recipes():
        payload, auth_error = authenticate_token()

        user_id = (
            int(payload["sub"])
            if auth_error is None
            else None
        )

        result = service.count_recipes(
            user_id
        )

        return jsonify(result), 200

    @recipes_bp.get("/recipes/<int:recipe_id>")
    def get_recipe(recipe_id):
        row = service.find_recipe(recipe_id)
        user_id = None

        if service.requires_authentication(row):
            payload, auth_error = authenticate_token()

            if auth_error is not None:
                return auth_error

            user_id = int(payload["sub"])

        return jsonify(service.read_recipe(row, user_id)), 200

    @recipes_bp.post("/recipes")
    @token_required
    def create_recipe():
        result = service.create_recipe(
            request.get_json(silent=True),
            g.user_id
        )
        cache.delete(PUBLIC_RECIPE_LIST_CACHE_KEY)
        return jsonify(result), 201

    @recipes_bp.patch("/recipes/<int:recipe_id>")
    @token_required
    def update_recipe(recipe_id):
        result = service.update_recipe(
            recipe_id,
            request.get_json(silent=True),
            g.user_id,
            g.is_admin
        )
        cache.delete(PUBLIC_RECIPE_LIST_CACHE_KEY)
        return jsonify(result), 200

    @recipes_bp.delete("/recipes/<int:recipe_id>")
    @token_required
    def delete_recipe(recipe_id):
        service.delete_recipe(
            recipe_id,
            g.user_id,
            g.is_admin
        )
        cache.delete(PUBLIC_RECIPE_LIST_CACHE_KEY)
        return "", 204

    return recipes_bp
