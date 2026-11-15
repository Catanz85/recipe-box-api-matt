
"""Create or update the recipes database."""

import sqlite3

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

connection = sqlite3.connect("recipes.db")

try:
    connection.executescript(SCHEMA)

    # Add role to existing users table if missing.
    user_columns = [
        row[1]
        for row in connection.execute("PRAGMA table_info(users)")
    ]

    if "role" not in user_columns:
        connection.execute(
            "ALTER TABLE users "
            "ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
        )
        print("Added role to users.")

    # Add owner_id to existing recipes table if missing.
    columns = [
        row[1]
        for row in connection.execute("PRAGMA table_info(recipes)")
    ]

    if "owner_id" not in columns:
        connection.execute(
            "ALTER TABLE recipes ADD COLUMN "
            "owner_id INTEGER REFERENCES users(id)"
        )
        print("Added owner_id to recipes.")

    existing = connection.execute(
        "SELECT COUNT(*) FROM recipes"
    ).fetchone()[0]

    if existing == 0:
        connection.executemany(
            "INSERT INTO recipes "
            "(title, ingredients, instructions, is_public) "
            "VALUES (?, ?, ?, ?)",
            SEED,
        )
        print(f"Seeded {len(SEED)} recipes.")
    else:
        print(f"Preserved {existing} existing recipes.")

    connection.commit()

finally:
    connection.close()
