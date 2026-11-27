import tempfile
from pathlib import Path

from sqlalchemy import select

from app import create_app
from app.data.database import init_db
from app.extensions import cache, db
from app.models import Recipe, Tag


checks = []


def check(name, passed):
    checks.append((name, bool(passed)))
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    assert passed, name


def cache_value(app):
    with app.app_context():
        return cache.get("public_recipe_list")


with tempfile.TemporaryDirectory() as directory:
    app = create_app(database=str(Path(directory) / "tags.db"))
    app.config["TESTING"] = True
    init_db(app)
    client = app.test_client()

    tokens = {}

    for username in ("tag_owner", "tag_other"):
        registration = client.post("/register", json={
            "username": username,
            "password": "TagFeatureTestPassword",
        })
        assert registration.status_code == 201

        login = client.post("/login", json={
            "username": username,
            "password": "TagFeatureTestPassword",
        })
        assert login.status_code == 200
        tokens[username] = {
            "Authorization": "Bearer " + login.get_json()["access_token"]
        }

    public = client.post("/recipes", json={
        "title": "Tags public fixture",
        "ingredients": "test ingredients",
    }, headers=tokens["tag_owner"])
    assert public.status_code == 201
    public_id = public.get_json()["id"]

    private = client.post("/recipes", json={
        "title": "Tags private fixture",
        "ingredients": "private ingredients",
        "is_public": False,
    }, headers=tokens["tag_owner"])
    assert private.status_code == 201
    private_id = private.get_json()["id"]

    check(
        "Anonymous public recipe tags",
        client.get(f"/recipes/{public_id}/tags").get_json() == {"tags": []}
    )
    check(
        "Anonymous private recipe tags rejected",
        client.get(f"/recipes/{private_id}/tags").status_code == 401
    )
    check(
        "Owner can read private recipe tags",
        client.get(
            f"/recipes/{private_id}/tags",
            headers=tokens["tag_owner"]
        ).get_json() == {"tags": []}
    )
    check(
        "Non-owner cannot read private recipe tags",
        client.get(
            f"/recipes/{private_id}/tags",
            headers=tokens["tag_other"]
        ).status_code == 403
    )
    check(
        "Unauthorized tag modification rejected",
        client.post(
            f"/recipes/{public_id}/tags",
            json={"tags": ["quick"]},
            environ_overrides={"REMOTE_ADDR": "192.0.2.10"}
        ).status_code == 401
    )

    anonymous_list = client.get("/recipes").get_json()
    initial_cache = cache_value(app)
    check(
        "Anonymous recipe list remains public-only",
        all(recipe["is_public"] for recipe in anonymous_list)
    )
    check("Public list cache was populated", initial_cache is not None)

    non_owner_write = client.post(
        f"/recipes/{public_id}/tags",
        json={"tags": ["unauthorized"]},
        headers=tokens["tag_other"]
    )
    check("Non-owner tag modification rejected",
          non_owner_write.status_code == 403)
    check("Rejected modification preserves cache",
          cache_value(app) == initial_cache)

    added = client.post(
        f"/recipes/{public_id}/tags",
        json={"tags": [" Quick ", "Dinner", "quick"]},
        headers=tokens["tag_owner"]
    )
    check("Owner can add normalized tags",
          added.status_code == 201
          and added.get_json() == {"tags": ["dinner", "quick"]})
    check("Successful tag modification invalidates public list cache",
          cache_value(app) is None)

    check(
        "Public recipe tags are readable",
        client.get(f"/recipes/{public_id}/tags").get_json()
        == {"tags": ["dinner", "quick"]}
    )

    private_add = client.post(
        f"/recipes/{private_id}/tags",
        json={"tags": ["quick"]},
        headers=tokens["tag_owner"],
        environ_overrides={"REMOTE_ADDR": "192.0.2.11"}
    )
    check("Tags can be shared across recipes",
          private_add.status_code == 201
          and private_add.get_json() == {"tags": ["quick"]})

    with app.app_context():
        quick_tag = db.session.scalar(
            select(Tag).where(Tag.name == "quick")
        )
        related_recipe_ids = {
            recipe.id for recipe in quick_tag.recipes
        }
        check("Many-to-many association uses one shared tag",
              related_recipe_ids == {public_id, private_id})

    public_list = client.get("/recipes").get_json()
    public_cache = cache_value(app)
    invalid = client.post(
        f"/recipes/{public_id}/tags",
        json={"tags": []},
        headers=tokens["tag_owner"],
        environ_overrides={"REMOTE_ADDR": "192.0.2.12"}
    )
    check("Empty tag list rejected", invalid.status_code == 400)
    check("Invalid tag request preserves cache",
          cache_value(app) == public_cache)
    check("Tag modification preserves recipe visibility",
          public_id in {recipe["id"] for recipe in public_list}
          and private_id not in {recipe["id"] for recipe in public_list})

    rate_limited_remote = {"REMOTE_ADDR": "198.51.100.10"}
    rate_responses = [
        client.post(
            f"/recipes/{public_id}/tags",
            json={"tags": [f"limited-{number}"]},
            headers=tokens["tag_owner"],
            environ_overrides=rate_limited_remote
        )
        for number in range(1, 5)
    ]
    check("Tag write uses 3-per-minute rate limit",
          [response.status_code for response in rate_responses]
          == [201, 201, 201, 429])

print(f"Passed: {sum(passed for _, passed in checks)}/{len(checks)}")
