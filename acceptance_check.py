import os
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import app as api

results = []

with tempfile.TemporaryDirectory() as temp:
    test_db = os.path.join(temp, "recipes.db")
    shutil.copy2("recipes.db", test_db)

    client = api.create_app(database=test_db).test_client()
    prefix = uuid.uuid4().hex[:10]
    password = uuid.uuid4().hex

    owner = f"{prefix}_owner"
    other = f"{prefix}_other"
    admin = f"{prefix}_admin"

    def call(method, path, body=None, headers=None):
        kwargs = {"headers": headers or {}}
        if body is not None:
            kwargs["json"] = body
        return client.open(path, method=method, **kwargs)

    def check(number, name, response, expected, verify=None):
        try:
            behavior_ok = verify(response) if verify else True
        except Exception:
            behavior_ok = False

        passed = response.status_code == expected and behavior_ok
        status = "PASS" if passed else "FAIL"

        results.append((
            number, name, expected,
            response.status_code, status
        ))

        print(
            f"{number:02d}. {name}: "
            f"{response.status_code} — {status}"
        )

        if not passed:
            print("    Response:", response.get_json(silent=True))

        return response

    def error(message):
        return lambda r: r.get_json().get("error") == message

    def credentials(username):
        return {"username": username, "password": password}

    def login(username):
        response = call("POST", "/login", credentials(username))
        assert response.status_code == 200
        return {
            "Authorization": "Bearer " +
            response.get_json()["access_token"]
        }

    def recipe_shape(response):
        data = response.get_json()
        return (
            set(data) == {
                "id", "title", "ingredients",
                "instructions", "is_public"
            }
            and isinstance(data["is_public"], bool)
        )

    def recipe_body(title, public=True):
        return {
            "title": f"{prefix}_{title}",
            "ingredients": "Test ingredients",
            "instructions": "Test instructions",
            "is_public": public
        }

    missing_error = error("Missing or invalid token")
    invalid_error = error("Invalid token")
    expired_error = error(
        "Token expired. Please log in again."
    )
    forbidden_error = error(
        "Forbidden: you do not own this recipe"
    )
    not_found = error("recipe not found")
    json_error = error("a JSON body is required")
    duplicate_error = error(
        "a recipe with that title already exists"
    )

    # ROOT AND AUTHENTICATION

    check(1, "API root",
          call("GET", "/"), 200,
          lambda r: r.get_json() == {
              "message": "Recipe Box API",
              "recipes": "/recipes"
          })

    response = check(
        2, "Register new user",
        call("POST", "/register", credentials(owner)), 201,
        lambda r: r.get_json()["username"] == owner
        and isinstance(r.get_json()["id"], int)
    )
    owner_id = response.get_json()["id"]

    check(3, "Duplicate username",
          call("POST", "/register", credentials(owner)), 409,
          error("username already exists"))

    check(4, "Missing registration password",
          call("POST", "/register", {"username": owner}), 400,
          error("username and password are required"))

    check(5, "Non-object registration JSON",
          call("POST", "/register", []), 400, json_error)

    def valid_login(response):
        data = response.get_json()
        payload = jwt.decode(
            data["access_token"],
            os.environ["JWT_SECRET"],
            algorithms=["HS256"]
        )
        return (
            data["id"] == owner_id
            and data["username"] == owner
            and data["token_type"] == "Bearer"
            and payload["sub"] == str(owner_id)
            and payload["exp"] - payload["iat"] == 3600
        )

    check(6, "Valid login",
          call("POST", "/login", credentials(owner)), 200,
          valid_login)

    check(7, "Wrong password",
          call("POST", "/login", {
              "username": owner, "password": "incorrect"
          }), 401, error("Invalid credentials"))

    check(8, "Unknown user",
          call("POST", "/login", credentials(prefix + "_missing")),
          401, error("Invalid credentials"))

    check(9, "Missing login credentials",
          call("POST", "/login", {}), 400,
          error("username and password are required"))

    check(10, "Non-object login JSON",
          call("POST", "/login", []), 400, json_error)

    # TEST FIXTURES

    for username in (other, admin):
        response = call("POST", "/register", credentials(username))
        assert response.status_code == 201

    with sqlite3.connect(test_db) as db:
        db.execute(
            "UPDATE users SET role = 'admin' WHERE username = ?",
            (admin,)
        )
        other_id = db.execute(
            "SELECT id FROM users WHERE username = ?", (other,)
        ).fetchone()[0]
        db.commit()

    owner_token = login(owner)
    other_token = login(other)
    admin_token = login(admin)

    invalid_token = {
        "Authorization": "Bearer invalid.token.value"
    }

    now = datetime.now(timezone.utc)

    expired = jwt.encode({
        "sub": str(owner_id),
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1)
    }, os.environ["JWT_SECRET"], algorithm="HS256")

    expired_token = {"Authorization": "Bearer " + expired}

    def fixture(title, public, token):
        response = call(
            "POST", "/recipes",
            recipe_body(title, public), token
        )
        assert response.status_code == 201
        return response.get_json()["id"]

    public_id = fixture("public", True, owner_token)
    private_id = fixture("private", False, owner_token)
    other_private_id = fixture("other_private", False, other_token)

    public_url = f"/recipes/{public_id}"
    private_url = f"/recipes/{private_id}"

    with sqlite3.connect(test_db) as db:
        missing_id = db.execute(
            "SELECT COALESCE(MAX(id), 0) + 10000 FROM recipes"
        ).fetchone()[0]

    missing_url = f"/recipes/{missing_id}"

    def visible_recipes(user_id=None):
        with sqlite3.connect(test_db) as db:
            rows = db.execute(
                "SELECT id FROM recipes "
                "WHERE is_public = 1 OR owner_id = ?",
                (user_id,)
            ).fetchall()
        expected = {row[0] for row in rows}

        return lambda r: {
            item["id"] for item in r.get_json()
        } == expected

    # READ RECIPES

    check(11, "Anonymous recipe list",
          call("GET", "/recipes"), 200,
          visible_recipes())

    check(12, "Owner recipe list",
          call("GET", "/recipes", headers=owner_token),
          200, visible_recipes(owner_id))

    check(13, "Other user recipe list",
          call("GET", "/recipes", headers=other_token),
          200, visible_recipes(other_id))

    check(14, "Invalid token recipe list",
          call("GET", "/recipes", headers=invalid_token),
          200, visible_recipes())

    check(15, "Anonymous public recipe",
          call("GET", public_url), 200, recipe_shape)

    check(16, "Owner private recipe",
          call("GET", private_url, headers=owner_token),
          200, recipe_shape)

    check(17, "Anonymous private recipe",
          call("GET", private_url), 401, missing_error)

    check(18, "Invalid token private recipe",
          call("GET", private_url, headers=invalid_token),
          401, invalid_error)

    check(19, "Expired token private recipe",
          call("GET", private_url, headers=expired_token),
          401, expired_error)

    check(20, "Other user private recipe",
          call("GET", private_url, headers=other_token),
          403, forbidden_error)

    check(21, "Missing recipe",
          call("GET", missing_url), 404, not_found)

    # CREATE RECIPES

    def created_public(response):
        data = response.get_json()
        with sqlite3.connect(test_db) as db:
            stored_owner = db.execute(
                "SELECT owner_id FROM recipes WHERE id = ?",
                (data["id"],)
            ).fetchone()[0]
        return (
            recipe_shape(response)
            and data["is_public"] is True
            and stored_owner == owner_id
        )

    body = recipe_body("create")
    del body["is_public"]

    check(22, "Create public recipe by default",
          call("POST", "/recipes", body, owner_token),
          201, created_public)

    check(23, "Create private recipe",
          call("POST", "/recipes",
               recipe_body("create_private", False), owner_token),
          201, lambda r: recipe_shape(r)
          and r.get_json()["is_public"] is False)

    check(24, "Anonymous create",
          call("POST", "/recipes", body), 401, missing_error)

    check(25, "Invalid token create",
          call("POST", "/recipes", body, invalid_token),
          401, invalid_error)

    check(26, "Expired token create",
          call("POST", "/recipes", body, expired_token),
          401, expired_error)

    check(27, "Missing required recipe fields",
          call("POST", "/recipes", {}, owner_token), 400,
          error("title and ingredients are required"))

    check(28, "Duplicate recipe title",
          call("POST", "/recipes", body, owner_token),
          409, duplicate_error)

    # UPDATE RECIPES

    update = {"instructions": "Updated instructions"}

    check(29, "Anonymous update",
          call("PATCH", public_url, update),
          401, missing_error)

    check(30, "Invalid token update",
          call("PATCH", public_url, update, invalid_token),
          401, invalid_error)

    check(31, "Expired token update",
          call("PATCH", public_url, update, expired_token),
          401, expired_error)

    original = call("GET", public_url).get_json()

    check(32, "Unauthorized update",
          call("PATCH", public_url, update, other_token),
          403, lambda r: forbidden_error(r)
          and call("GET", public_url).get_json() == original)

    check(33, "Update missing recipe",
          call("PATCH", missing_url, update, owner_token),
          404, not_found)

    check(34, "Owner update",
          call("PATCH", public_url, update, owner_token),
          200, lambda r: recipe_shape(r)
          and r.get_json()["instructions"] == update["instructions"])

    check(35, "Admin update",
          call("PATCH", public_url,
               {"instructions": "Admin update"}, admin_token),
          200, lambda r: recipe_shape(r)
          and r.get_json()["instructions"] == "Admin update")

    check(36, "Empty update JSON",
          call("PATCH", public_url, {}, owner_token),
          400, json_error)

    check(37, "Unsupported update fields",
          call("PATCH", public_url,
               {"unsupported": True}, owner_token),
          400, error("nothing to update"))

    check(38, "Duplicate title update",
          call("PATCH", public_url,
               {"title": body["title"]}, owner_token),
          409, duplicate_error)

    # DELETE RECIPES

    check(39, "Anonymous delete",
          call("DELETE", public_url), 401, missing_error)

    check(40, "Invalid token delete",
          call("DELETE", public_url, headers=invalid_token),
          401, invalid_error)

    check(41, "Expired token delete",
          call("DELETE", public_url, headers=expired_token),
          401, expired_error)

    original = call("GET", public_url).get_json()

    check(42, "Unauthorized delete",
          call("DELETE", public_url, headers=other_token),
          403, lambda r: forbidden_error(r)
          and call("GET", public_url).get_json() == original)

    check(43, "Delete missing recipe",
          call("DELETE", missing_url, headers=owner_token),
          404, not_found)

    check(44, "Owner delete",
          call("DELETE", public_url, headers=owner_token),
          204, lambda r: r.data == b""
          and call("GET", public_url).status_code == 404)

    check(45, "Admin delete",
          call("DELETE", private_url, headers=admin_token),
          204, lambda r: r.data == b""
          and call("GET", private_url,
                   headers=owner_token).status_code == 404)

# VERIFICATION EVIDENCE

passed = sum(row[4] == "PASS" for row in results)
failed = len(results) - passed

report = [
    "# Recipe API Acceptance Test Results",
    "",
    "Tests performed against a temporary database copy.",
    "",
    "| # | Scenario | Expected | Actual | Result |",
    "|---|---|---|---|---|"
]

for number, name, expected, actual, status in results:
    report.append(
        f"| {number} | {name} | {expected} | {actual} | {status} |"
    )

report.extend([
    "",
    f"Total: {len(results)}",
    f"Passed: {passed}",
    f"Failed: {failed}",
    f"Overall: {'PASS' if passed == 45 and failed == 0 else 'FAIL'}"
])

Path("ACCEPTANCE_TEST_RESULTS.md").write_text(
    "\n".join(report) + "\n"
)

print("\nTotal:", len(results))
print("Passed:", passed)
print("Failed:", failed)
print("Overall:", "PASS" if passed == 45 and failed == 0 else "FAIL")
print("Evidence: ACCEPTANCE_TEST_RESULTS.md")

if passed != 45 or failed:
    raise SystemExit(1)
