import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from app.data.database import DEFAULT_DATABASE, get_db, close_db
from app.middleware import authenticate_token, token_required
from app.routes.auth import create_auth_bp
from app.routes.recipes import create_recipes_bp


def create_app(database=DEFAULT_DATABASE):
    load_dotenv()

    app = Flask(__name__)

    app.config["DATABASE"] = database
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
