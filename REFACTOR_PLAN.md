Recipe Box API — Refactor Plan
Planning only. No application code moves or rewrites. Baseline: supplied app.py and recovered prior classroom curl/security scenarios. The original local curl checklist is not available for exact comparison; the matrix below consolidates recovered scenarios and adds code-derived contract checks for coverage. Expected results are not a new test run.
Responsibility inventory (13)
1. Configuration — environment variables, database path, JWT secret.
2. Application setup — initialize Flask.
3. Database access — open, manage and close connections.
4. Request handling — define routes and process requests.
5. Input validation — validate JSON and required fields.
6. User registration — create accounts.
7. Password security — hash and verify passwords.
8. Authentication — issue and validate JWTs, enforce authentication.
9. Authorization — enforce recipe ownership and administrator permissions.
10. Recipe management — create, read, update and delete recipes.
11. Response formatting — serialize records to JSON.
12. Error handling — return error messages and HTTP status codes.
13. Application startup — start the Flask development server.
Target layout
recipe-box/
├── app.py
├── config/
├── data/
├── auth/
│   ├── routes.py
│   ├── services.py
│   └── data.py
└── recipes/
    ├── routes.py
    ├── services.py
    └── data.py
Shared configuration and database connection management belong in config/ and data/; feature-specific queries belong in each feature's data.py. Existing supporting files remain in place during planning.
Public contract
The refactor may change the internal file structure and organization of the code, but must preserve all existing API endpoints, request and response formats, status codes, security rules, and behavior.
Curl acceptance checklist
Base URL: http://127.0.0.1:5001. Use distinct test accounts (owner, other user, and an existing admin), unique recipe titles, public/private fixtures, and an unused recipe ID. Send JSON with Content-Type: application/json; use Authorization: Bearer $TOKEN when required. Each row is one method/path/scenario assertion. ID means an existing fixture unless described as missing. Recipe JSON contains id, title, ingredients, instructions, and boolean is_public. Error responses are JSON objects with an error field. Use a disposable test database, not production data.
#	Method	Path	Scenario	Status	Expected response behavior
1	GET	/	API root	200	message: Recipe Box API; recipes: /recipes
2	POST	/register	New username and password	201	id and username
3	POST	/register	Duplicate username	409	username already exists
4	POST	/register	Missing password or blank username	400	username and password are required
5	POST	/register	Non-object JSON	400	a JSON body is required
6	POST	/login	Valid credentials	200	id, username, access_token, token_type Bearer; JWT expires in one hour
7	POST	/login	Wrong password	401	Invalid credentials
8	POST	/login	Unknown user	401	Invalid credentials
9	POST	/login	Missing credentials	400	username and password are required
10	POST	/login	Non-object JSON	400	a JSON body is required
11	GET	/recipes	Anonymous	200	Public recipes only
12	GET	/recipes	Owner token	200	Public recipes and own private recipes only
13	GET	/recipes	Other user token	200	Public recipes and that user’s own private recipes only
14	GET	/recipes	Invalid or expired token	200	Public recipes only
15	GET	/recipes/ID	Public recipe, anonymous	200	Recipe JSON
16	GET	/recipes/ID	Private recipe, owner token	200	Recipe JSON
17	GET	/recipes/ID	Private recipe, no token	401	Missing or invalid token
18	GET	/recipes/ID	Private recipe, invalid token	401	Invalid token
19	GET	/recipes/ID	Private recipe, expired token	401	Token expired. Please log in again.
20	GET	/recipes/ID	Private recipe, other user	403	Forbidden: you do not own this recipe
21	GET	/recipes/ID	Missing recipe	404	recipe not found
22	POST	/recipes	Valid token and unique recipe	201	Created recipe JSON; owner assigned to authenticated creator; public by default
23	POST	/recipes	Valid token, is_public false	201	Created recipe JSON with is_public false
24	POST	/recipes	Missing token	401	Missing or invalid token
25	POST	/recipes	Invalid token	401	Invalid token
26	POST	/recipes	Expired token	401	Token expired. Please log in again.
27	POST	/recipes	Missing title or ingredients	400	title and ingredients are required
28	POST	/recipes	Duplicate title violating database constraint	409	a recipe with that title already exists
29	PATCH	/recipes/ID	Missing token	401	Missing or invalid token
30	PATCH	/recipes/ID	Invalid token	401	Invalid token
31	PATCH	/recipes/ID	Expired token	401	Token expired. Please log in again.
32	PATCH	/recipes/ID	Other user, not admin	403	Forbidden: you do not own this recipe; recipe unchanged
33	PATCH	/recipes/ID	Missing recipe, valid token	404	recipe not found
34	PATCH	/recipes/ID	Owner, valid request	200	Updated recipe JSON
35	PATCH	/recipes/ID	Admin, another user’s recipe	200	Updated recipe JSON
36	PATCH	/recipes/ID	Empty or non-object JSON, owner	400	a JSON body is required
37	PATCH	/recipes/ID	No supported update fields, owner	400	nothing to update
38	PATCH	/recipes/ID	Duplicate title violating database constraint, owner	409	a recipe with that title already exists
39	DELETE	/recipes/ID	Missing token	401	Missing or invalid token
40	DELETE	/recipes/ID	Invalid token	401	Invalid token
41	DELETE	/recipes/ID	Expired token	401	Token expired. Please log in again.
42	DELETE	/recipes/ID	Other user, not admin	403	Forbidden: you do not own this recipe; recipe unchanged
43	DELETE	/recipes/ID	Missing recipe, valid token	404	recipe not found
44	DELETE	/recipes/ID	Owner, valid request	204	Empty body; recipe removed
45	DELETE	/recipes/ID	Admin, another user’s recipe	204	Empty body; recipe removed


Total acceptance-list items: 45.

Count is per scenario row, not per endpoint or public-contract category. Some rows group equivalent input variants; the exact historical curl list could not be independently verified. Preserve stateless logout (client discards token; no server logout endpoint) and password hashing as additional non-curl security invariants. Re-run the existing security regression script after any future refactor.