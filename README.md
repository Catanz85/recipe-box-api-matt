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
