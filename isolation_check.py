import hashlib
import sqlite3
import uuid

from contextlib import closing
from pathlib import Path

from app import create_app
from app.data.database import init_db


results = []


def check(name, actual, expected):
    passed = actual == expected
    results.append(passed)

    print(
        f"{name}: {actual} "
        f"— {'PASS' if passed else 'FAIL'}"
    )


def snapshot(path, username, title):
    # Open read-only so verification cannot modify development data.
    with closing(sqlite3.connect(
        path.as_uri() + "?mode=ro", uri=True
    )) as db:

        return {
            "users": db.execute(
                "SELECT COUNT(*) FROM users"
            ).fetchone()[0],

            "recipes": db.execute(
                "SELECT COUNT(*) FROM recipes"
            ).fetchone()[0],

            "test_users": db.execute(
                "SELECT COUNT(*) FROM users WHERE username = ?",
                (username,)
            ).fetchone()[0],

            "test_recipes": db.execute(
                "SELECT COUNT(*) FROM recipes WHERE title = ?",
                (title,)
            ).fetchone()[0],
        }


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


development = create_app("development")
testing = create_app("testing")

dev_path = Path(development.config["DATABASE"]).resolve()
test_path = Path(testing.config["DATABASE"]).resolve()

username = f"isolation_{uuid.uuid4().hex[:12]}"
title = f"Isolation recipe {username}"
password = uuid.uuid4().hex

print("=== APPLICATION CONFIGURATION ===")

print("Development database:", dev_path.name)
print("Testing database: instance/" + test_path.name)

check("Separate app instances", development is not testing, True)
check("Development testing flag", development.testing, False)
check("Testing flag", testing.testing, True)
check("Database paths differ", dev_path != test_path, True)

assert dev_path != test_path, "Unsafe database configuration"
assert dev_path.exists(), "Development database is missing"

# Never delete an unexpected pre-existing database.
assert not test_path.exists(), (
    "Testing database already exists. Inspect it before continuing."
)

before = snapshot(dev_path, username, title)
before_hash = fingerprint(dev_path)

print("\n=== DEVELOPMENT BEFORE TESTING ===")
print(before)

try:
    print("\n=== TEST DATABASE INITIALIZATION ===")

    check("Testing database initially absent",
          not test_path.exists(), True)

    init_db(testing)

    check("Testing database created", test_path.exists(), True)

    with closing(sqlite3.connect(test_path)) as db:
        tables = {
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }

    print("Created tables:", sorted(tables))

    check("Required tables created",
          {"users", "recipes"}.issubset(tables), True)

    initialized = snapshot(test_path, username, title)

    print("Testing rows after initialization:", initialized)

    init_db(testing)

    check("Repeated initialization preserves rows",
          snapshot(test_path, username, title),
          initialized)

    client = testing.test_client()

    credentials = {
        "username": username,
        "password": password,
    }

    print("\n=== API SMOKE TESTS ===")

    response = client.post("/register", json=credentials)

    print("Register response:", response.get_json())

    check("Register status", response.status_code, 201)

    assert response.status_code == 201

    response = client.post("/login", json=credentials)

    check("Login status", response.status_code, 200)

    assert response.status_code == 200

    login_body = response.get_json()
    token = login_body["access_token"]

    print("Login response:", {
        **login_body,
        "access_token": "[REDACTED]"
    })

    check("Bearer token returned",
          login_body["token_type"], "Bearer")

    auth = {"Authorization": f"Bearer {token}"}

    response = client.get("/recipes")

    print("List recipes response:", response.get_json())

    check("List recipes status", response.status_code, 200)

    check("Anonymous list contains public recipes only",
          all(r["is_public"] for r in response.get_json()),
          True)

    data = {
        "title": title,
        "ingredients": "Isolation test ingredients",
        "is_public": False,
    }

    response = client.post("/recipes", json=data)

    check("Anonymous creation rejected",
          response.status_code, 401)

    response = client.post(
        "/recipes", json=data, headers=auth
    )

    check("Authenticated creation",
          response.status_code, 201)

    assert response.status_code == 201

    recipe_id = response.get_json()["id"]

    check("Anonymous private recipe rejected",
          client.get(
              f"/recipes/{recipe_id}"
          ).status_code, 401)

    check("Owner can read private recipe",
          client.get(
              f"/recipes/{recipe_id}", headers=auth
          ).status_code, 200)

    after_test = snapshot(test_path, username, title)

    after_dev = snapshot(dev_path, username, title)

    print("\n=== TESTING DATABASE AFTER REQUESTS ===")
    print(after_test)

    print("\n=== DEVELOPMENT DATABASE AFTER REQUESTS ===")
    print(after_dev)

    check("Development row counts unchanged",
          after_dev, before)

    check("Development database fingerprint unchanged",
          fingerprint(dev_path), before_hash)

    check("Test user exists in testing database",
          after_test["test_users"], 1)

    check("Test recipe exists in testing database",
          after_test["test_recipes"], 1)

    check("Test user absent from development database",
          after_dev["test_users"], 0)

    check("Test recipe absent from development database",
          after_dev["test_recipes"], 0)

finally:
    # Remove only the disposable database created during this run.
    test_path.unlink(missing_ok=True)

    print("\n=== CLEANUP ===")

    check("Disposable testing database removed",
          not test_path.exists(), True)

print("\n=== ISOLATION TEST SUMMARY ===")
print(f"Passed: {sum(results)}/{len(results)}")
print("Overall:", "PASS" if all(results) else "FAIL")

if not all(results):
    raise SystemExit(1)
