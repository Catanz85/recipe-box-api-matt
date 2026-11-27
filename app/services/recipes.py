from app.data import recipes as repository


class RecipeError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def recipe_to_dict(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "ingredients": row["ingredients"],
        "instructions": row["instructions"],
        "is_public": bool(row["is_public"]),
    }


def list_recipes(db, user_id=None):
    rows = repository.list_visible(db, user_id)
    return [recipe_to_dict(row) for row in rows]


def find_recipe(db, recipe_id):
    row = repository.get_by_id(db, recipe_id)

    if row is None:
        raise RecipeError("not_found", "recipe not found")

    return row


def requires_authentication(row):
    return row["is_public"] != 1


def read_recipe(row, user_id=None):
    if requires_authentication(row) and row["owner_id"] != user_id:
        raise RecipeError(
            "forbidden",
            "Forbidden: you do not own this recipe"
        )

    return recipe_to_dict(row)


def require_owner_or_admin(row, user_id, is_admin):
    if not (row["owner_id"] == user_id or is_admin):
        raise RecipeError(
            "forbidden",
            "Forbidden: you do not own this recipe"
        )


def create_recipe(db, data, user_id):
    if not isinstance(data, dict) or (
        not data.get("title") or not data.get("ingredients")
    ):
        raise RecipeError(
            "invalid",
            "title and ingredients are required"
        )

    fields = {
        "title": data["title"],
        "ingredients": data["ingredients"],
        "instructions": data.get("instructions", ""),
        "is_public": 1 if data.get("is_public", True) else 0,
    }

    try:
        row = repository.insert(db, fields, user_id)
    except repository.RecipeConflict:
        raise RecipeError(
            "conflict",
            "a recipe with that title already exists"
        )

    return recipe_to_dict(row)


def update_recipe(db, recipe_id, data, user_id, is_admin):
    row = find_recipe(db, recipe_id)
    require_owner_or_admin(row, user_id, is_admin)

    if not isinstance(data, dict) or not data:
        raise RecipeError("invalid", "a JSON body is required")

    fields = {
        column: data[column]
        for column in ("title", "ingredients", "instructions")
        if column in data
    }

    if "is_public" in data:
        fields["is_public"] = 1 if data["is_public"] else 0

    if not fields:
        raise RecipeError("invalid", "nothing to update")

    try:
        row = repository.update(db, recipe_id, fields)
    except repository.RecipeConflict:
        raise RecipeError(
            "conflict",
            "a recipe with that title already exists"
        )

    if row is None:
        raise RecipeError("not_found", "recipe not found")

    return recipe_to_dict(row)


def delete_recipe(db, recipe_id, user_id, is_admin):
    row = find_recipe(db, recipe_id)
    require_owner_or_admin(row, user_id, is_admin)

    if repository.delete(db, recipe_id) == 0:
        raise RecipeError("not_found", "recipe not found")
