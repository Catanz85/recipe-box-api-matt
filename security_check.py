import os
import shutil
import sqlite3
import tempfile
import uuid

import app as api

results = []
original_db = api.DATABASE

def check(name, actual, expected):
    status = "PASS" if actual == expected else "FAIL"
    results.append((name, actual, expected, status))
    print(f"{name}: {actual} — {status}")

with tempfile.TemporaryDirectory() as temp:
    test_db = os.path.join(temp, "recipes.db")
    shutil.copy2(original_db, test_db)
    api.DATABASE = test_db
    client = api.app.test_client()

    password = uuid.uuid4().hex
    prefix = uuid.uuid4().hex[:10]

    def create_user(name):
        username = f"{prefix}_{name}"
        response = client.post("/register", json={
            "username": username,
            "password": password
        })
        assert response.status_code == 201, response.get_json()
        return username

    def login(username):
        response = client.post("/login", json={
            "username": username,
            "password": password
        })
        assert response.status_code == 200
        return {"Authorization": "Bearer " +
                response.get_json()["access_token"]}

    owner = create_user("owner")
    other = create_user("other")
    admin = create_user("admin")

    with sqlite3.connect(test_db) as db:
        db.execute(
            "UPDATE users SET role = 'admin' WHERE username = ?",
            (admin,)
        )
        db.commit()

    owner_token = login(owner)
    other_token = login(other)
    admin_token = login(admin)

    response = client.post("/recipes", json={
        "title": f"Security test {prefix}",
        "ingredients": "Test ingredients"
    }, headers=owner_token)

    check("Create recipe", response.status_code, 201)
    recipe_id = response.get_json()["id"]
    url = f"/recipes/{recipe_id}"

    body = {"instructions": "Security verified"}

    check("Anonymous protected write",
          client.patch(url, json=body).status_code, 401)

    check("Invalid token",
          client.patch(url, json=body, headers={
              "Authorization": "Bearer invalid.token.value"
          }).status_code, 401)

    check("Owner request",
          client.patch(url, json=body,
                       headers=owner_token).status_code, 200)

    check("Non-owner request",
          client.patch(url, json=body,
                       headers=other_token).status_code, 403)

    check("Anonymous delete regression",
          client.delete(url).status_code, 401)

    check("Cross-user delete regression",
          client.delete(url, headers=other_token).status_code, 403)

    with sqlite3.connect(test_db) as db:
        columns = [
            row[1] for row in db.execute("PRAGMA table_info(users)")
        ]
        stored = db.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (owner,)
        ).fetchone()[0]

    check("Password hash present", "password_hash" in columns, True)
    check("Plaintext password column absent",
          "password" not in columns, True)
    check("Plaintext password not stored",
          stored != password, True)

    check("Admin deleting another user's recipe",
          client.delete(url, headers=admin_token).status_code, 204)

api.DATABASE = original_db

passed = all(row[3] == "PASS" for row in results)

with open("SECURITY_TEST_RESULTS.md", "w") as f:
    f.write("# Recipe API Security Test Results\n\n")
    f.write("Tests performed against a temporary database copy.\n\n")
    f.write("| Check | Actual | Expected | Result |\n")
    f.write("|---|---|---|---|\n")
    for name, actual, expected, status in results:
        f.write(f"| {name} | {actual} | {expected} | {status} |\n")

print("\nOverall:", "PASS" if passed else "FAIL")
print("Evidence: SECURITY_TEST_RESULTS.md")

if not passed:
    raise SystemExit(1)
