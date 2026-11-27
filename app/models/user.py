from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False, unique=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(
        db.Text,
        nullable=False,
        server_default=db.text("'user'")
    )

    recipes = db.relationship(
        "Recipe",
        back_populates="owner",
        order_by="Recipe.id"
    )
