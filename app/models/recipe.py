from app.extensions import db


class Recipe(db.Model):
    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False, unique=True)
    ingredients = db.Column(db.Text, nullable=False)
    description = db.Column(
        db.Text,
        nullable=False,
        server_default=db.text("''")
    )
    instructions = db.Column(
        db.Text,
        nullable=False,
        server_default=db.text("''")
    )
    is_public = db.Column(
        db.Integer,
        nullable=False,
        server_default=db.text("1")
    )
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    owner = db.relationship(
        "User",
        back_populates="recipes"
    )
    tags = db.relationship(
        "Tag",
        secondary="recipe_tags",
        back_populates="recipes",
        order_by="Tag.name",
        passive_deletes=True
    )
