from app.data import recipes as repository


class RecipeError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def recipe_to_dict(row):
    return {
        "id": row.id,
        "title": row.title,
        "ingredients": row.ingredients,
        "instructions": row.instructions,
        "is_public": bool(row.is_public),
    }


def list_recipes(user_id=None):
    rows = repository.list_visible(user_id)
    return [recipe_to_dict(row) for row in rows]


def find_recipe(recipe_id):
    row = repository.get_by_id(recipe_id)

    if row is None:
        raise RecipeError("not_found", "recipe not found")

    return row


def recipe_owner_id(row):
    return row.owner.id if row.owner is not None else None


def requires_authentication(row):
    return row.is_public != 1


def read_recipe(row, user_id=None):
    if requires_authentication(row) and recipe_owner_id(row) != user_id:
        raise RecipeError(
            "forbidden",
            "Forbidden: you do not own this recipe"
        )

    return recipe_to_dict(row)


def require_owner_or_admin(row, user_id, is_admin):
    if not (recipe_owner_id(row) == user_id or is_admin):
        raise RecipeError(
            "forbidden",
            "Forbidden: you do not own this recipe"
        )


def create_recipe(data, user_id):
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
        row = repository.insert(fields, user_id)
    except repository.RecipeConflict:
        raise RecipeError(
            "conflict",
            "a recipe with that title already exists"
        )

    return recipe_to_dict(row)


def update_recipe(recipe_id, data, user_id, is_admin):
    row = find_recipe(recipe_id)
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
        row = repository.update(recipe_id, fields)
    except repository.RecipeConflict:
        raise RecipeError(
            "conflict",
            "a recipe with that title already exists"
        )

    if row is None:
        raise RecipeError("not_found", "recipe not found")

    return recipe_to_dict(row)


def delete_recipe(recipe_id, user_id, is_admin):
    row = find_recipe(recipe_id)
    require_owner_or_admin(row, user_id, is_admin)

    if repository.delete(recipe_id) == 0:
        raise RecipeError("not_found", "recipe not found")


def count_recipes(user_id=None):
    return {
        "count": repository.count_visible(user_id)
    }
