import hashlib
import tempfile
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import Recipe

baseline = "3cc0e8c7f2cc928ba0c41eda669b1cca05f26fcaf5aa1e0bb6cd0e0cf47c8440"

development = Path("recipes.db")

assert hashlib.sha256(
    development.read_bytes()
).hexdigest() == baseline

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "orm-write-test.db"

    app = create_app(database=str(path))
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

    client = app.test_client()

    credentials = {
        "username": "orm_test_owner",
        "password": "TemporaryORMTestPassword"
    }

    response = client.post("/register", json=credentials)
    assert response.status_code == 201

    response = client.post("/login", json=credentials)
    assert response.status_code == 200

    headers = {
        "Authorization": "Bearer " + response.get_json()["access_token"]
    }

    print("Registration and authentication setup: PASS")
    print("\n=== THREE-REQUEST ORM WRITE SMOKE TEST ===")

    response = client.post(
        "/recipes",
        json={
            "title": "ORM Test Recipe",
            "ingredients": "Water and flour",
            "instructions": "Mix ingredients",
            "is_public": False
        },
        headers=headers
    )

    assert response.status_code == 201

    recipe_id = response.get_json()["id"]

    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        assert recipe is not None
        assert recipe.title == "ORM Test Recipe"

    print("POST /recipes: 201 PASS")
    print("ORM insertion verified")

    response = client.patch(
        f"/recipes/{recipe_id}",
        json={"instructions": "Updated through ORM"},
        headers=headers
    )

    assert response.status_code == 200
    assert response.get_json()["instructions"] == "Updated through ORM"

    with app.app_context():
        recipe = db.session.get(Recipe, recipe_id)
        assert recipe.instructions == "Updated through ORM"

    print(f"PATCH /recipes/{recipe_id}: 200 PASS")
    print("ORM attribute update verified")

    response = client.delete(
        f"/recipes/{recipe_id}",
        headers=headers
    )

    assert response.status_code == 204

    with app.app_context():
        assert db.session.get(Recipe, recipe_id) is None
        db.session.remove()
        db.engine.dispose()

    print(f"DELETE /recipes/{recipe_id}: 204 PASS")
    print("ORM deletion verified")

assert not path.exists()

assert hashlib.sha256(
    development.read_bytes()
).hexdigest() == baseline

print("\nSmoke tests: 3/3 PASS")
print("Disposable database cleanup: PASS")
print("Development database fingerprint: unchanged")
