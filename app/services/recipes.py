from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.data import recipes as repository
from app.extensions import db
from app.models import Tag


class RecipeError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def recipe_to_dict(row):
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
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

    if not isinstance(data.get("description", ""), str):
        raise RecipeError("invalid", "description must be a string")

    fields = {
        "description": data.get("description", ""),
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

    if "description" in data and not isinstance(data["description"], str):
        raise RecipeError("invalid", "description must be a string")

    fields = {
        column: data[column]
        for column in ("title", "ingredients", "instructions", "description")
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


def list_recipe_tags(row):
    return sorted(tag.name for tag in row.tags)


def add_recipe_tags(recipe_id, data, user_id, is_admin):
    row = find_recipe(recipe_id)
    require_owner_or_admin(row, user_id, is_admin)

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("tags"), list)
        or not data["tags"]
    ):
        raise RecipeError("invalid", "tags must be a non-empty list")

    names = []

    for value in data["tags"]:
        if not isinstance(value, str):
            raise RecipeError(
                "invalid",
                "tags must be non-empty strings of at most 50 characters"
            )

        name = value.strip().casefold()

        if not name or len(name) > 50:
            raise RecipeError(
                "invalid",
                "tags must be non-empty strings of at most 50 characters"
            )

        if name not in names:
            names.append(name)

    existing_tags = db.session.scalars(
        select(Tag).where(Tag.name.in_(names))
    ).all()
    tags_by_name = {tag.name: tag for tag in existing_tags}
    attached_names = {tag.name for tag in row.tags}
    changed = False

    for name in names:
        tag = tags_by_name.get(name)

        if tag is None:
            tag = Tag(name=name)
            db.session.add(tag)
            tags_by_name[name] = tag

        if name not in attached_names:
            row.tags.append(tag)
            attached_names.add(name)
            changed = True

    if changed:
        try:
            db.session.commit()
        except IntegrityError as exc:
            db.session.rollback()
            raise RecipeError(
                "conflict",
                "a tag with that name already exists"
            ) from exc

    return sorted(attached_names), changed
