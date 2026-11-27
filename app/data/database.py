import sqlite3
from flask import current_app, g

DEFAULT_DATABASE = "recipes.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    ingredients TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    is_public INTEGER NOT NULL DEFAULT 1,
    owner_id INTEGER REFERENCES users(id)
);
"""

SEED = [
    (
        "Shakshuka",
        "eggs, tomatoes, peppers, onion, cumin, paprika",
        "Simmer the sauce, crack in the eggs, cover until just set.",
        1,
    ),
    (
        "Overnight oats",
        "rolled oats, milk, yogurt, chia seeds, honey",
        "Stir everything together and refrigerate overnight.",
        1,
    ),
    (
        "Secret family hot sauce",
        "habaneros, garlic, vinegar, a secret ingredient",
        "If we wrote it down here, it wouldn't be a secret.",
        0,
    ),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")

    return g.db


def close_db(exception=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()

        try:
            db.executescript(SCHEMA)

            user_columns = [
                row[1]
                for row in db.execute("PRAGMA table_info(users)")
            ]

            if "role" not in user_columns:
                db.execute(
                    "ALTER TABLE users "
                    "ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
                )

            recipe_columns = [
                row[1]
                for row in db.execute("PRAGMA table_info(recipes)")
            ]

            if "owner_id" not in recipe_columns:
                db.execute(
                    "ALTER TABLE recipes "
                    "ADD COLUMN owner_id INTEGER REFERENCES users(id)"
                )

            count = db.execute(
                "SELECT COUNT(*) FROM recipes"
            ).fetchone()[0]

            if count == 0:
                db.executemany(
                    """
                    INSERT INTO recipes
                    (title, ingredients, instructions, is_public)
                    VALUES (?, ?, ?, ?)
                    """,
                    SEED,
                )

            db.commit()

        finally:
            close_db()
