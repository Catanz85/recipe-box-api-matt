"""Initialize a new Recipe Box database."""

from app import create_app
from app.data.database import init_db


if __name__ == "__main__":
    app = create_app()
    init_db(app)
    print("Database initialized successfully.")
