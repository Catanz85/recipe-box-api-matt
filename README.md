# Recipe Box API

A small, working Flask + SQLite API for keeping recipes. Full CRUD, clean
status codes - and **no authentication at all**. Anyone who can reach it can
read, change, or delete anything. In BE104 you fix that: real users, hashed
passwords, JSON Web Tokens, ownership rules, and middleware.

## Run it

```
python init_db.py
python app.py
```

Requires Python 3.10+ and Flask (`pip install -r requirements.txt`).

## Try it

```
curl http://127.0.0.1:5000/recipes
curl http://127.0.0.1:5000/recipes/1
curl -X POST http://127.0.0.1:5000/recipes -H "Content-Type: application/json" \
     -d '{"title": "Toast", "ingredients": "bread"}'
curl -X DELETE http://127.0.0.1:5000/recipes/1
```

## Endpoints

| Method | Path | Success | Errors |
|---|---|---|---|
| GET | /recipes | 200 | |
| GET | /recipes/&lt;id&gt; | 200 | 404 |
| POST | /recipes | 201 | 400 bad body · 409 duplicate title |
| PATCH | /recipes/&lt;id&gt; | 200 | 400 · 404 · 409 |
| DELETE | /recipes/&lt;id&gt; | 204 | 404 |

`is_public` is stored on every recipe but nothing enforces it yet - by the end
of Unit 3, private recipes will only be visible to their owners.
Notes: Matt’s local dev instance.

## SQLAlchemy Integration

Flask-SQLAlchemy is initialized through the application factory
using the extension in app/extensions.py.

The User and Recipe models in app/models map the existing
SQLite tables. Both ORM and raw SQL connections use the same
configured database path.

The ORM is used for read-only verification in this lesson.
Existing endpoint queries remain in the app/data modules.

See ORM_TEST_RESULTS.md for verification evidence.

## ORM Recipe Reads

The recipe list and detail endpoints now use SQLAlchemy ORM
queries through the existing data and service layers.

Recipe creation, updates, deletion, and the count endpoint
retain their existing raw SQL implementations.

See ORM_READ_TEST_RESULTS.md for verification evidence.

## Full ORM Conversion

All application-level database operations now use SQLAlchemy ORM,
including recipe CRUD, recipe counts, user registration,
authentication lookups, and role verification.

Transactions use commit and rollback handling. Database
initialization uses ORM table creation and seed records.

The remaining SQLite connection event enables foreign-key
enforcement and is not an application-level SQL query.

See ORM_WRITE_TEST_RESULTS.md for verification evidence.

Run the isolated ORM write smoke test with:

    python orm_write_check.py
