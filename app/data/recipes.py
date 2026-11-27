from sqlalchemy import select, or_, func, null
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Recipe, User


class RecipeConflict(Exception):
    pass


def visibility_filter(user_id=None):
    if user_id is None:
        return Recipe.is_public == 1

    return or_(
        Recipe.is_public == 1,
        Recipe.owner.has(User.id == user_id)
    )


def list_visible(user_id=None):
    statement = (
        select(Recipe)
        .where(visibility_filter(user_id))
        .order_by(Recipe.id)
    )
    return db.session.scalars(statement).all()


def get_by_id(recipe_id):
    return db.session.get(Recipe, recipe_id)


def insert(data, user_id):
    fields = dict(data)

    if fields.get("instructions") is None:
        fields["instructions"] = null()

    recipe = Recipe(**fields, owner_id=user_id)

    try:
        db.session.add(recipe)
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise RecipeConflict() from exc

    return recipe


def update(recipe_id, fields):
    allowed = ("title", "ingredients", "instructions", "is_public")

    if not fields or any(key not in allowed for key in fields):
        raise ValueError("Invalid update fields")

    recipe = get_by_id(recipe_id)

    if recipe is None:
        return None

    try:
        for key, value in fields.items():
            setattr(recipe, key, value)

        db.session.commit()

    except IntegrityError as exc:
        db.session.rollback()
        raise RecipeConflict() from exc

    return recipe


def delete(recipe_id):
    recipe = get_by_id(recipe_id)

    if recipe is None:
        return 0

    try:
        db.session.delete(recipe)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return 1


def count_visible(user_id=None):
    statement = (
        select(func.count(Recipe.id))
        .where(visibility_filter(user_id))
    )
    return db.session.scalar(statement)
