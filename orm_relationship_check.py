import hashlib
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.extensions import db
from app.models import User, Recipe

baseline = (
    "3cc0e8c7f2cc928ba0c41eda669b1cca05"
    "f26fcaf5aa1e0bb6cd0e0cf47c8440"
)

development = Path("recipes.db")

assert hashlib.sha256(
    development.read_bytes()
).hexdigest() == baseline

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "relationship-test.db"

    app = create_app(database=str(path))
    app.config["TESTING"] = True

    with app.app_context():
        db.create_all()

        owner = User(
            username="relationship_owner",
            email="owner@example.com",
            password_hash="test-only"
        )

        other = User(
            username="relationship_other",
            email="other@example.com",
            password_hash="test-only"
        )

        admin = User(
            username="relationship_admin",
            email="admin@example.com",
            password_hash="test-only",
            role="admin"
        )

        db.session.add_all([owner, other, admin])
        db.session.commit()

        owner_id = owner.id
        other_id = other.id
        admin_id = admin.id

        print("=== REFERENTIAL INTEGRITY ===")

        invalid_id = max(
            owner_id, other_id, admin_id
        ) + 1000

        invalid = Recipe(
            title="Invalid owner recipe",
            ingredients="Water",
            owner_id=invalid_id
        )

        try:
            db.session.add(invalid)
            db.session.commit()

        except IntegrityError as exc:
            db.session.rollback()

            assert "FOREIGN KEY constraint failed" in str(
                exc.orig
            )

            print("Invalid owner write: PASS")
            print("Expected error:", exc.orig)

        else:
            raise AssertionError(
                "Invalid owner unexpectedly accepted"
            )

        assert db.session.scalar(
            select(Recipe).where(
                Recipe.title == "Invalid owner recipe"
            )
        ) is None

        print("Invalid record not persisted: PASS")

        owner = db.session.get(User, owner_id)
        other = db.session.get(User, other_id)

        private = Recipe(
            title="Owner private recipe",
            ingredients="Flour",
            instructions="Mix",
            is_public=0,
            owner=owner
        )

        public = Recipe(
            title="Public recipe",
            ingredients="Water",
            is_public=1,
            owner=other
        )

        other_private = Recipe(
            title="Other private recipe",
            ingredients="Salt",
            is_public=0,
            owner=other
        )

        unowned = Recipe(
            title="Unowned recipe",
            ingredients="Sugar",
            is_public=1
        )

        db.session.add_all([
            private, public, other_private, unowned
        ])

        db.session.commit()

        private_id = private.id
        public_id = public.id
        other_private_id = other_private.id
        unowned_id = unowned.id

        print("Valid owner write: PASS")

        assert private.owner.id == owner_id
        assert private.owner_id == owner_id

        print("Recipe.owner navigation: PASS")

        assert private_id in [
            item.id for item in owner.recipes
        ]

        print("User.recipes navigation: PASS")

        assert unowned.owner is None
        assert unowned.owner_id is None

        print("Nullable owner relationship: PASS")

    # Generate temporary test credentials without
    # exposing the application secret or tokens.

    import jwt
    from datetime import datetime, timedelta, timezone

    def headers(user_id, username, role="user"):
        now = datetime.now(timezone.utc)

        token = jwt.encode(
            {
                "sub": str(user_id),
                "username": username,
                "role": role,
                "iat": now,
                "exp": now + timedelta(minutes=10)
            },
            app.config["JWT_SECRET"],
            algorithm="HS256"
        )

        return {"Authorization": f"Bearer {token}"}

    owner_headers = headers(
        owner_id, "relationship_owner"
    )

    other_headers = headers(
        other_id, "relationship_other"
    )

    admin_headers = headers(
        admin_id, "relationship_admin", "admin"
    )

    client = app.test_client()

    print("\n=== THREE-REQUEST RELATIONSHIP SMOKE TEST ===")

    # Request 1: Owner can access their private recipe.

    response = client.get(
        f"/recipes/{private_id}",
        headers=owner_headers
    )

    assert response.status_code == 200
    assert response.get_json()["id"] == private_id

    print("1. Owner private recipe access: 200 PASS")

    # Request 2: Another user cannot access it.

    response = client.get(
        f"/recipes/{private_id}",
        headers=other_headers
    )

    assert response.status_code == 403
    assert response.get_json() == {
        "error": "Forbidden: you do not own this recipe"
    }

    print("2. Non-owner private recipe access: 403 PASS")

    # Request 3: Admin listing preserves public visibility.
    # Admin status must not expose other users' private recipes.

    response = client.get(
        "/recipes",
        headers=admin_headers
    )

    assert response.status_code == 200

    ids = [
        item["id"] for item in response.get_json()
    ]

    assert ids == sorted([public_id, unowned_id])
    assert private_id not in ids
    assert other_private_id not in ids

    print("3. Admin recipe listing: 200 PASS")
    print("Public visibility and ordering preserved")

    with app.app_context():
        db.session.remove()
        db.engine.dispose()

assert not path.exists()

assert hashlib.sha256(
    development.read_bytes()
).hexdigest() == baseline

print("\nSmoke requests: 3/3 PASS")
print("Disposable database cleanup: PASS")
print("Development database fingerprint: unchanged")
