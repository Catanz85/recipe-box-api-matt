from app.extensions import db


recipe_tags = db.Table(
    "recipe_tags",
    db.Column(
        "recipe_id",
        db.Integer,
        db.ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True
    ),
    db.Column(
        "tag_id",
        db.Integer,
        db.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True
    )
)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    recipes = db.relationship(
        "Recipe",
        secondary=recipe_tags,
        back_populates="tags",
        passive_deletes=True
    )
