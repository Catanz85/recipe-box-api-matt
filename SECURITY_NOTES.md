# Security findings – 2026-11-01

- Anonymous `GET /recipes` → returned all recipes, including `"Secret family hot sauce"` with `"is_public": false`. No authentication or access control was required.