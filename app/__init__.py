import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify

from app.config import CONFIGS
from app.extensions import db
from app.models import User, Recipe
from app.data.database import get_db, close_db
from app.middleware import authenticate_token, token_required
from app.routes.auth import create_auth_bp
from app.routes.recipes import create_recipes_bp


def create_app(config="development", database=None):
    load_dotenv()

    app = Flask(__name__)

    # Preserve compatibility with existing positional database paths.
    if config not in CONFIGS:
        if database is not None:
            raise ValueError("Invalid configuration selector")
        database = config
        config = "development"

    app.config.from_object(CONFIGS[config])

    if config == "testing":
        if database is not None:
            raise ValueError("Testing uses its own disposable database")

        Path(app.instance_path).mkdir(parents=True, exist_ok=True)

        app.config["DATABASE"] = str(
            Path(app.instance_path) / app.config["DATABASE"]
        )

    elif database is not None:
        app.config["DATABASE"] = database
    database_path = Path(app.config["DATABASE"]).resolve()
    app.config["DATABASE"] = str(database_path)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{database_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    app.config["JWT_SECRET"] = os.environ.get("JWT_SECRET")

    if not app.config["JWT_SECRET"]:
        raise RuntimeError("JWT_SECRET is missing from your .env file")

    app.teardown_appcontext(close_db)

    @app.get("/")
    def hello():
        return jsonify({
            "message": "Recipe Box API",
            "recipes": "/recipes"
        })

    auth_bp = create_auth_bp(
        app,
        get_db,
        app.config["JWT_SECRET"]
    )

    recipes_bp = create_recipes_bp(
        get_db,
        authenticate_token,
        token_required
    )

    app.register_blueprint(auth_bp, url_prefix="/")
    app.register_blueprint(recipes_bp, url_prefix="/")

    return app
