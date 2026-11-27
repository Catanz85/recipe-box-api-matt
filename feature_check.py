import sqlite3
import tempfile

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from app import create_app
from app.data.database import init_db


results = []


def check(name, actual, expected):
    passed = actual == expected

    status = "PASS" if passed else "FAIL"

    results.append((name, actual, expected, status))

    print(
        f"{name}: {actual} "
        f"(expected {expected}) — {status}"
    )


with tempfile.TemporaryDirectory() as temp:
    path = str(Path(temp) / "feature.db")

    app = create_app(database=path)
    app.config["TESTING"] = True

    init_db(app)

    client = app.test_client()

    password = "TemporaryFeatureTestPassword"

    for username in ("owner", "other", "admin"):
        response = client.post("/register", json={
            "username": username,
            "password": password
        })

        assert response.status_code == 201

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE users SET role = 'admin' WHERE username = ?",
            ("admin",)
        )
        db.commit()

    tokens = {}
    user_ids = {}

    for username in ("owner", "other", "admin"):
        response = client.post("/login", json={
            "username": username,
            "password": password
        })

        assert response.status_code == 200

        body = response.get_json()

        tokens[username] = {
            "Authorization": "Bearer " + body["access_token"]
        }

        user_ids[username] = body["id"]

    baseline = len(client.get("/recipes").get_json())

    def count(auth=None):
        response = client.get(
            "/recipes/count",
            headers=auth or {}
        )

        return response.status_code, response.get_json()

    check("Anonymous baseline count",
          count(), (200, {"count": baseline}))

    def create(title, username, public):
        response = client.post("/recipes", json={
            "title": title,
            "ingredients": "Test ingredients",
            "is_public": public,
        }, headers=tokens[username])

        assert response.status_code == 201

        return response.get_json()["id"]

    create("Feature public", "owner", True)

    private_id = create(
        "Feature private owner", "owner", False
    )

    create("Feature private other", "other", False)

    check("Anonymous public count",
          count(), (200, {"count": baseline + 1}))

    check("Owner visible count",
          count(tokens["owner"]),
          (200, {"count": baseline + 2}))

    check("Other user visible count",
          count(tokens["other"]),
          (200, {"count": baseline + 2}))

    check("Admin cannot count other private recipes",
          count(tokens["admin"]),
          (200, {"count": baseline + 1}))

    check("Invalid token falls back to public count",
          count({"Authorization": "Bearer invalid.token.value"}),
          (200, {"count": baseline + 1}))

    now = datetime.now(timezone.utc)

    expired = jwt.encode({
        "sub": str(user_ids["owner"]),
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }, app.config["JWT_SECRET"], algorithm="HS256")

    check("Expired token falls back to public count",
          count({"Authorization": "Bearer " + expired}),
          (200, {"count": baseline + 1}))

    matching = True

    for auth in ({}, *tokens.values()):
        listed = client.get(
            "/recipes", headers=auth
        ).get_json()

        status, body = count(auth)

        matching = matching and (
            status == 200
            and body == {"count": len(listed)}
        )

    check("Count matches existing list visibility",
          matching, True)

    response = client.patch(
        f"/recipes/{private_id}",
        json={"is_public": True},
        headers=tokens["owner"]
    )

    assert response.status_code == 200

    check("Count reflects visibility update",
          count(), (200, {"count": baseline + 2}))

    response = client.delete(
        f"/recipes/{private_id}",
        headers=tokens["owner"]
    )

    assert response.status_code == 204

    check("Count reflects recipe deletion",
          count(), (200, {"count": baseline + 1}))


passed = sum(row[3] == "PASS" for row in results)

report = [
    "# Recipe Count Feature Test Results",
    "",
    "Endpoint: GET /recipes/count",
    "",
    "Executed against a disposable SQLite database.",
    "",
    "| Check | Actual | Expected | Result |",
    "|---|---|---|---|"
]

for name, actual, expected, status in results:
    report.append(
        f"| {name} | {actual} | {expected} | {status} |"
    )

report.extend([
    "",
    f"Total: {passed}/{len(results)}",
    f"Overall: {'PASS' if passed == len(results) else 'FAIL'}",
    ""
])

Path("FEATURE_TEST_RESULTS.md").write_text(
    "\n".join(report), encoding="utf-8"
)

print(f"\nPassed: {passed}/{len(results)}")
print("Overall:", "PASS" if passed == len(results) else "FAIL")

if passed != len(results):
    raise SystemExit(1)
