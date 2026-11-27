# Cache Invalidation Verification

## Existing implementation

`GET /recipes` uses the cache key `public_recipe_list`. It caches only the
anonymous public list, with an explicit 30-second timeout. Valid authenticated
list requests query the service directly and bypass this shared cache.

Each recipe write invalidates the public-list entry only after the service
operation succeeds:

```python
result = service.create_recipe(request.get_json(silent=True), g.user_id)
cache.delete(PUBLIC_RECIPE_LIST_CACHE_KEY)
return jsonify(result), 201
```

```python
result = service.update_recipe(
    recipe_id, request.get_json(silent=True), g.user_id, g.is_admin
)
cache.delete(PUBLIC_RECIPE_LIST_CACHE_KEY)
return jsonify(result), 200
```

```python
service.delete_recipe(recipe_id, g.user_id, g.is_admin)
cache.delete(PUBLIC_RECIPE_LIST_CACHE_KEY)
return "", 204
```

The cache key is deleted after successful creation, update, and deletion.
Errors raised by the service return before the deletion line.

## Curl reproduction

The following requests used temporary app snapshots and separate temporary
SQLite databases, never the project database. In the disabled snapshot only,
the three `cache.delete(...)` lines were removed. The disabled app was
restarted between write scenarios to begin each scenario with an empty
process-local SimpleCache and a database containing the recipe being tested.
The restored snapshot used the committed implementation and repeated the same
write payloads and list requests.

All responses below are actual `curl` output. The temporary bearer token is
omitted.

### Invalidation disabled: stale responses

**Create**

```text
POST /recipes {"title":"Created after warm","ingredients":"safe"}
{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}
HTTP 201

GET /recipes
[{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Update fixture before cache"},{"description":"","id":2,"ingredients":"safe","instructions":"","is_public":true,"title":"Delete fixture before cache"}]
HTTP 200
```

The successful create is absent from the cached list.

**Update**

```text
PATCH /recipes/1 {"title":"Updated fixture"}
{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Updated fixture"}
HTTP 200

GET /recipes
[{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Update fixture before cache"},{"description":"","id":2,"ingredients":"safe","instructions":"","is_public":true,"title":"Delete fixture before cache"},{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}]
HTTP 200
```

The PATCH succeeds, but the list still has the old title.

**Delete**

```text
DELETE /recipes/2

HTTP 204

GET /recipes
[{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Updated fixture"},{"description":"","id":2,"ingredients":"safe","instructions":"","is_public":true,"title":"Delete fixture before cache"},{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}]
HTTP 200
```

The DELETE succeeds, but the cached list still contains the deleted recipe.

### Invalidation restored: fresh responses

```text
POST /recipes {"title":"Created after warm","ingredients":"safe"}
{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}
HTTP 201

GET /recipes
[{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Update fixture before cache"},{"description":"","id":2,"ingredients":"safe","instructions":"","is_public":true,"title":"Delete fixture before cache"},{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}]
HTTP 200

PATCH /recipes/1 {"title":"Updated fixture"}
{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Updated fixture"}
HTTP 200

GET /recipes
[{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Updated fixture"},{"description":"","id":2,"ingredients":"safe","instructions":"","is_public":true,"title":"Delete fixture before cache"},{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}]
HTTP 200

DELETE /recipes/2

HTTP 204

GET /recipes
[{"description":"","id":1,"ingredients":"safe","instructions":"","is_public":true,"title":"Updated fixture"},{"description":"","id":3,"ingredients":"safe","instructions":"","is_public":true,"title":"Created after warm"}]
HTTP 200
```

## Failed and unauthorized writes

With the public list cached, an isolated test instrumented `cache.delete` and
checked the cache value and stored recipe after each request:

| Request | Response | Cache invalidated? | Stored data changed? |
|---|---:|---|---|
| Unauthenticated `POST /recipes` | 401 | No | No |
| Invalid authenticated `POST /recipes` | 400 | No | No |
| Non-owner `PATCH /recipes/1` | 403 | No | No |
| Non-owner `DELETE /recipes/1` | 403 | No | No |
| Owner `PATCH /recipes/99999` | 404 | No | No |
| Owner `DELETE /recipes/99999` | 404 | No | No |

All six checks passed. The cache-delete spy recorded no calls; the recipe
count and stored title were unchanged.

## Endpoints to never cache

- `POST /register` and `POST /login`: authentication and account-specific data.
- Authenticated `GET /recipes`: visible results depend on the requesting user.
  Only the anonymous public result is shared-cached.
- `GET /recipes/count`: the count depends on authenticated visibility.
- `GET /recipes/<id>`: visibility and response depend on private-recipe
  ownership and authorization.
- `POST /recipes`, `PATCH /recipes/<id>`, and `DELETE /recipes/<id>`: these are
  state-changing operations; do not cache their responses. Successful recipe
  writes invalidate the public-list entry.

## Regression and security results

All existing check scripts were run against the isolated current-code copy:

- `feature_check.py`: **10/10 PASS**
- `isolation_check.py`: **24/24 PASS**
- `security_check.py`: **PASS**
- Targeted cache visibility checks: anonymous lists excluded private recipes;
  authenticated owner/other lists bypassed the shared cache and preserved
  ownership filtering: **PASS**
- Failed/unauthorized write checks: **6/6 PASS**
- `acceptance_check.py`: **41/50**. The same nine assertions fail at the
  pre-caching baseline: their expected recipe-field set omits `description`,
  which the existing API responses include.
- `orm_write_check.py` and `orm_relationship_check.py`: both stop at their
  pre-existing database fingerprint guard. They expect SHA256
  `3cc0e8c7f2cc928ba0c41eda669b1cca05f26fcaf5aa1e0bb6cd0e0cf47c8440`;
  the isolated copy of the local database is
  `c5cb545d595efb58b5367f9b242de772839cf416aa754a0a68f433274277454f`.

The original database was not modified. No application-code change was needed.
