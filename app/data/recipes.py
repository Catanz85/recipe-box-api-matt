import sqlite3

from sqlalchemy import select, or_
from app.extensions import db as orm_db
from app.models import Recipe


class RecipeConflict(Exception):
    pass


def list_visible(db, user_id=None, is_admin=False):
    if user_id is None:
        return db.execute(
            "SELECT * FROM recipes "
            "WHERE is_public = 1 ORDER BY id"
        ).fetchall()

    return db.execute(
        "SELECT * FROM recipes "
        "WHERE is_public = 1 OR owner_id = ? "
        "ORDER BY id",
        (user_id,)
    ).fetchall()


def get_by_id(db, recipe_id):
    return db.execute(
        "SELECT * FROM recipes WHERE id = ?",
        (recipe_id,)
    ).fetchone()


def insert(db, data, user_id):
    try:
        cur = db.execute(
            "INSERT INTO recipes "
            "(title, ingredients, instructions, is_public, owner_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                data["title"],
                data["ingredients"],
                data["instructions"],
                data["is_public"],
                user_id,
            )
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise RecipeConflict() from exc

    return get_by_id(db, cur.lastrowid)


def update(db, recipe_id, fields):
    allowed = ("title", "ingredients", "instructions", "is_public")

    if not fields or any(key not in allowed for key in fields):
        raise ValueError("Invalid update fields")

    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = list(fields.values()) + [recipe_id]

    try:
        cur = db.execute(
            f"UPDATE recipes SET {assignments} WHERE id = ?",
            values
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise RecipeConflict() from exc

    if cur.rowcount == 0:
        return None

    return get_by_id(db, recipe_id)


def delete(db, recipe_id):
    cur = db.execute(
        "DELETE FROM recipes WHERE id = ?",
        (recipe_id,)
    )
    db.commit()
    return cur.rowcount


def count_visible(db, user_id=None):
    if user_id is None:
        row = db.execute(
            "SELECT COUNT(*) FROM recipes "
            "WHERE is_public = 1"
        ).fetchone()

    else:
        row = db.execute(
            "SELECT COUNT(*) FROM recipes "
            "WHERE is_public = 1 OR owner_id = ?",
            (user_id,)
        ).fetchone()

    return row[0]


def list_visible_orm(user_id=None):
    statement = select(Recipe)

    if user_id is None:
        statement = statement.where(
            Recipe.is_public == 1
        )
    else:
        statement = statement.where(
            or_(
                Recipe.is_public == 1,
                Recipe.owner_id == user_id
            )
        )

    statement = statement.order_by(Recipe.id)

    return orm_db.session.scalars(statement).all()


def get_by_id_orm(recipe_id):
    return orm_db.session.get(Recipe, recipe_id)
