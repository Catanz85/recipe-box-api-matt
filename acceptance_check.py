import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone

import jwt

from app import create_app
from app.data.database import init_db


results = []

FORBIDDEN = "Forbidden: you do not own this recipe"
MISSING = "Missing or invalid token"
INVALID = "Invalid token"
EXPIRED = "Token expired. Please log in again."
NOT_FOUND = "recipe not found"
CONFLICT = "a recipe with that title already exists"
JSON_REQUIRED = "a JSON body is required"

RECIPE_FIELDS = {
    "id", "title", "ingredients", "instructions", "is_public"
}


def check(name, response, expected, verify=None):
    actual = response.status_code
    detail = ""

    try:
        body = response.get_json(silent=True)
        correct = actual == expected

        if verify is not None:
            correct = correct and bool(verify(body, response))

    except Exception as exc:
        correct = False
        detail = str(exc)

    status = "PASS" if correct else "FAIL"
    results.append((name, expected, actual, status))

    print(
        f"{len(results):02d}. {name}: "
        f"{actual} (expected {expected}) — {status}"
    )

    if not correct:
        print("    Response:", response.get_data(as_text=True))
        if detail:
            print("    Detail:", detail)


def error(message):
    return lambda body, response: body == {"error": message}


def recipe(body, response):
    return (
        isinstance(body, dict)
        and set(body) == RECIPE_FIELDS
        and isinstance(body["is_public"], bool)
    )


def empty(body, response):
    return response.data == b""


def headers(token):
    return {"Authorization": f"Bearer {token}"}


with tempfile.TemporaryDirectory() as temp:

    database = str(Path(temp) / "acceptance.db")
    app = create_app(database=database)
    app.config["TESTING"] = True

    init_db(app)

    client = app.test_client()
    password = "AcceptanceTestPassword"

    credentials = {
        "username": "owner",
        "password": password
    }

    # 1-10: Root, registration and login

    check("API root", client.get("/"), 200,
          lambda b, r: b == {
              "message": "Recipe Box API",
              "recipes": "/recipes"
          })

    check("Register new user",
          client.post("/register", json=credentials), 201,
          lambda b, r: set(b) == {"id", "username"}
          and b["username"] == "owner")

    check("Duplicate username",
          client.post("/register", json=credentials), 409,
          error("username already exists"))

    check("Missing registration credentials",
          client.post("/register", json={"username": "missing"}),
          400, error("username and password are required"))

    check("Non-object registration JSON",
          client.post("/register", json=[]),
          400, error(JSON_REQUIRED))

    response = client.post("/login", json=credentials)

    def valid_login(body, response):
        if not isinstance(body, dict):
            return False

        if set(body) != {
            "id", "username", "access_token", "token_type"
        }:
            return False

        payload = jwt.decode(
            body["access_token"],
            app.config["JWT_SECRET"],
            algorithms=["HS256"]
        )

        return (
            body["token_type"] == "Bearer"
            and body["username"] == "owner"
            and payload["sub"] == str(body["id"])
            and payload["exp"] - payload["iat"] == 3600
        )

    check("Valid login", response, 200, valid_login)

    owner_token = response.get_json()["access_token"]
    owner = headers(owner_token)

    owner_id = response.get_json()["id"]

    check("Incorrect password",
          client.post("/login", json={
              "username": "owner", "password": "wrong"
          }), 401, error("Invalid credentials"))

    check("Unknown user",
          client.post("/login", json={
              "username": "unknown", "password": password
          }), 401, error("Invalid credentials"))

    check("Missing login credentials",
          client.post("/login", json={"username": "owner"}),
          400, error("username and password are required"))

    check("Non-object login JSON",
          client.post("/login", json=[]),
          400, error(JSON_REQUIRED))

    # Prepare isolated fixtures.

    for username in ("other", "admin"):
        response = client.post("/register", json={
            "username": username, "password": password
        })
        assert response.status_code == 201

    with sqlite3.connect(database) as db:
        db.execute(
            "UPDATE users SET role = ? WHERE username = ?",
            ("admin", "admin")
        )
        db.commit()

    def login_as(username):
        response = client.post("/login", json={
            "username": username, "password": password
        })
        assert response.status_code == 200
        return headers(response.get_json()["access_token"])

    other = login_as("other")
    admin = login_as("admin")

    invalid = headers("invalid.token.value")

    now = datetime.now(timezone.utc)

    expired = headers(jwt.encode(
        {
            "sub": str(owner_id),
            "username": "owner",
            "role": "user",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1)
        },
        app.config["JWT_SECRET"],
        algorithm="HS256"
    ))

    def fixture(title, auth, public=True):
        response = client.post("/recipes", json={
            "title": title,
            "ingredients": "Test ingredients",
            "instructions": "Test instructions",
            "is_public": public
        }, headers=auth)

        assert response.status_code == 201, response.get_json()
        return response.get_json()["id"]

    public_id = fixture("Public fixture", owner)
    private_id = fixture("Private owner fixture", owner, False)
    other_private_id = fixture("Other private fixture", other, False)

    public_url = f"/recipes/{public_id}"
    private_url = f"/recipes/{private_id}"
    missing_url = "/recipes/999999"

    def ids(body):
        return {item["id"] for item in body}

    def public_only(body, response):
        return (
            isinstance(body, list)
            and public_id in ids(body)
            and all(recipe(item, response) for item in body)
            and all(item["is_public"] for item in body)
        )

    # 11-14: Recipe list visibility

    check("Anonymous list",
          client.get("/recipes"), 200, public_only)

    check("Owner list",
          client.get("/recipes", headers=owner), 200,
          lambda b, r: public_id in ids(b)
          and private_id in ids(b)
          and other_private_id not in ids(b))

    check("Other user list",
          client.get("/recipes", headers=other), 200,
          lambda b, r: public_id in ids(b)
          and other_private_id in ids(b)
          and private_id not in ids(b))

    check("Invalid token list",
          client.get("/recipes", headers=invalid), 200,
          public_only)

    # 15-21: Individual recipe visibility

    check("Anonymous public recipe",
          client.get(public_url), 200, recipe)

    check("Owner private recipe",
          client.get(private_url, headers=owner), 200, recipe)

    check("Anonymous private recipe",
          client.get(private_url), 401, error(MISSING))

    check("Invalid token private recipe",
          client.get(private_url, headers=invalid),
          401, error(INVALID))

    check("Expired token private recipe",
          client.get(private_url, headers=expired),
          401, error(EXPIRED))

    check("Non-owner private recipe",
          client.get(private_url, headers=other),
          403, error(FORBIDDEN))

    check("Missing recipe",
          client.get(missing_url), 404, error(NOT_FOUND))

    # 22-28: Recipe creation

    new_recipe = {
        "title": "Acceptance created recipe",
        "ingredients": "Test ingredients"
    }

    response = client.post(
        "/recipes", json=new_recipe, headers=owner
    )

    def created_recipe(body, response):
        if not recipe(body, response):
            return False

        with sqlite3.connect(database) as db:
            row = db.execute(
                "SELECT owner_id FROM recipes WHERE id = ?",
                (body["id"],)
            ).fetchone()

        return (
            body["is_public"] is True
            and body["title"] == new_recipe["title"]
            and row[0] == owner_id
        )

    check("Create public recipe", response, 201, created_recipe)

    check("Create private recipe",
          client.post("/recipes", json={
              "title": "Acceptance private creation",
              "ingredients": "Ingredients",
              "is_public": False
          }, headers=owner), 201,
          lambda b, r: recipe(b, r) and b["is_public"] is False)

    check("Anonymous creation",
          client.post("/recipes", json=new_recipe),
          401, error(MISSING))

    check("Invalid token creation",
          client.post("/recipes", json=new_recipe, headers=invalid),
          401, error(INVALID))

    check("Expired token creation",
          client.post("/recipes", json=new_recipe, headers=expired),
          401, error(EXPIRED))

    check("Missing required recipe fields",
          client.post("/recipes", json={"title": "Incomplete"},
                      headers=owner),
          400, error("title and ingredients are required"))

    check("Duplicate recipe title",
          client.post("/recipes", json=new_recipe, headers=owner),
          409, error(CONFLICT))

    # 29-38: Recipe updates

    patch = {"instructions": "Updated instructions"}

    check("Anonymous update",
          client.patch(public_url, json=patch),
          401, error(MISSING))

    check("Invalid token update",
          client.patch(public_url, json=patch, headers=invalid),
          401, error(INVALID))

    check("Expired token update",
          client.patch(public_url, json=patch, headers=expired),
          401, error(EXPIRED))

    before = client.get(public_url).get_json()

    check("Non-owner update",
          client.patch(public_url, json=patch, headers=other),
          403, lambda b, r: b == {"error": FORBIDDEN}
          and client.get(public_url).get_json() == before)

    check("Update missing recipe",
          client.patch(missing_url, json=patch, headers=owner),
          404, error(NOT_FOUND))

    check("Owner update",
          client.patch(public_url, json=patch, headers=owner),
          200, lambda b, r: recipe(b, r)
          and b["instructions"] == patch["instructions"])

    check("Admin override update",
          client.patch(public_url, json={
              "instructions": "Admin updated"
          }, headers=admin),
          200, lambda b, r: recipe(b, r)
          and b["instructions"] == "Admin updated")

    check("Empty update body",
          client.patch(public_url, json={}, headers=owner),
          400, error(JSON_REQUIRED))

    check("Unsupported update fields",
          client.patch(public_url, json={
              "unsupported": "value"
          }, headers=owner),
          400, error("nothing to update"))

    check("Conflicting update title",
          client.patch(public_url, json={
              "title": "Private owner fixture"
          }, headers=owner),
          409, error(CONFLICT))

    # 39-45: Recipe deletion

    check("Anonymous delete",
          client.delete(public_url),
          401, error(MISSING))

    check("Invalid token delete",
          client.delete(public_url, headers=invalid),
          401, error(INVALID))

    check("Expired token delete",
          client.delete(public_url, headers=expired),
          401, error(EXPIRED))

    check("Non-owner delete",
          client.delete(public_url, headers=other),
          403, lambda b, r: b == {"error": FORBIDDEN}
          and client.get(public_url).status_code == 200)

    check("Delete missing recipe",
          client.delete(missing_url, headers=owner),
          404, error(NOT_FOUND))

    check("Owner delete",
          client.delete(public_url, headers=owner),
          204, lambda b, r: empty(b, r)
          and client.get(public_url).status_code == 404)

    check("Admin override delete",
          client.delete(private_url, headers=admin),
          204, lambda b, r: empty(b, r)
          and client.get(private_url).status_code == 404)

    # Supplemental checks for grouped variants and boundaries.

    check("Extra: Expired token list",
          client.get("/recipes", headers=expired),
          200, lambda b, r: isinstance(b, list)
          and bool(b)
          and all(recipe(item, r) for item in b)
          and all(item["is_public"] for item in b)
          and public_id not in ids(b)
          and b == client.get("/recipes").get_json())

    check("Extra: Admin cannot read other private recipe",
          client.get(
              f"/recipes/{other_private_id}", headers=admin
          ), 403, error(FORBIDDEN))

    check("Extra: Blank registration username",
          client.post("/register", json={
              "username": " ", "password": password
          }), 400, error("username and password are required"))

    check("Extra: Non-object update JSON",
          client.patch(
              f"/recipes/{other_private_id}",
              json=[], headers=other
          ), 400, error(JSON_REQUIRED))

    check("Extra: Missing ingredients",
          client.post("/recipes", json={
              "title": "Missing ingredients"
          }, headers=owner),
          400, error("title and ingredients are required"))


core = results[:45]
extra = results[45:]

core_passed = sum(row[3] == "PASS" for row in core)
extra_passed = sum(row[3] == "PASS" for row in extra)
total_passed = core_passed + extra_passed

report = [
    "# Recipe API Acceptance Test Results",
    "",
    "Tests executed against a disposable temporary SQLite database.",
    "The existing project database was not modified.",
    "",
    f"- Core acceptance scenarios: {core_passed}/{len(core)}",
    f"- Supplemental checks: {extra_passed}/{len(extra)}",
    f"- Total: {total_passed}/{len(results)}",
    "",
    "| # | Scenario | Expected | Actual | Result |",
    "|---|---|---|---|---|"
]

for number, (name, expected, actual, status) in enumerate(results, 1):
    report.append(
        f"| {number} | {name} | {expected} | {actual} | {status} |"
    )

passed = (
    len(core) == 45
    and total_passed == len(results)
)

report.extend([
    "",
    f"**Overall: {'PASS' if passed else 'FAIL'}**",
    ""
])

Path("ACCEPTANCE_TEST_RESULTS.md").write_text(
    "\n".join(report), encoding="utf-8"
)

print("\n=== ACCEPTANCE SUMMARY ===")
print(f"Core scenarios: {core_passed}/{len(core)}")
print(f"Supplemental checks: {extra_passed}/{len(extra)}")
print(f"Total passed: {total_passed}/{len(results)}")
print("Overall:", "PASS" if passed else "FAIL")
print("Evidence: ACCEPTANCE_TEST_RESULTS.md")

if not passed:
    raise SystemExit(1)
