"""Create or update the recipes database."""

from flask import Flask
from app.data.database import DEFAULT_DATABASE, init_db


if __name__ == "__main__":
    app = Flask(__name__)
    app.config["DATABASE"] = DEFAULT_DATABASE
    init_db(app)
    print("Database initialized successfully.")
