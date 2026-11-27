from pathlib import Path
from sqlalchemy import select, func
from app.extensions import db
from app.models import Recipe

DEFAULT_DATABASE = "recipes.db"

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


def init_db(app):
    with app.app_context():
        path = Path(app.config["DATABASE"]).resolve()

        if not app.testing and path.exists():
            raise RuntimeError(
                "Refusing to initialize an existing non-testing database"
            )

        db.create_all()

        count = db.session.scalar(
            select(func.count(Recipe.id))
        )

        if count == 0:
            try:
                for title, ingredients, instructions, public in SEED:
                    db.session.add(
                        Recipe(
                            title=title,
                            ingredients=ingredients,
                            instructions=instructions,
                            is_public=public
                        )
                    )

                db.session.commit()

            except Exception:
                db.session.rollback()
                raise
