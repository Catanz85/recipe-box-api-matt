# Recipe API Acceptance Test Results

Tests executed against a disposable temporary SQLite database.
The existing project database was not modified.

- Core acceptance scenarios: 45/45
- Supplemental checks: 5/5
- Total: 50/50

| # | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | API root | 200 | 200 | PASS |
| 2 | Register new user | 201 | 201 | PASS |
| 3 | Duplicate username | 409 | 409 | PASS |
| 4 | Missing registration credentials | 400 | 400 | PASS |
| 5 | Non-object registration JSON | 400 | 400 | PASS |
| 6 | Valid login | 200 | 200 | PASS |
| 7 | Incorrect password | 401 | 401 | PASS |
| 8 | Unknown user | 401 | 401 | PASS |
| 9 | Missing login credentials | 400 | 400 | PASS |
| 10 | Non-object login JSON | 400 | 400 | PASS |
| 11 | Anonymous list | 200 | 200 | PASS |
| 12 | Owner list | 200 | 200 | PASS |
| 13 | Other user list | 200 | 200 | PASS |
| 14 | Invalid token list | 200 | 200 | PASS |
| 15 | Anonymous public recipe | 200 | 200 | PASS |
| 16 | Owner private recipe | 200 | 200 | PASS |
| 17 | Anonymous private recipe | 401 | 401 | PASS |
| 18 | Invalid token private recipe | 401 | 401 | PASS |
| 19 | Expired token private recipe | 401 | 401 | PASS |
| 20 | Non-owner private recipe | 403 | 403 | PASS |
| 21 | Missing recipe | 404 | 404 | PASS |
| 22 | Create public recipe | 201 | 201 | PASS |
| 23 | Create private recipe | 201 | 201 | PASS |
| 24 | Anonymous creation | 401 | 401 | PASS |
| 25 | Invalid token creation | 401 | 401 | PASS |
| 26 | Expired token creation | 401 | 401 | PASS |
| 27 | Missing required recipe fields | 400 | 400 | PASS |
| 28 | Duplicate recipe title | 409 | 409 | PASS |
| 29 | Anonymous update | 401 | 401 | PASS |
| 30 | Invalid token update | 401 | 401 | PASS |
| 31 | Expired token update | 401 | 401 | PASS |
| 32 | Non-owner update | 403 | 403 | PASS |
| 33 | Update missing recipe | 404 | 404 | PASS |
| 34 | Owner update | 200 | 200 | PASS |
| 35 | Admin override update | 200 | 200 | PASS |
| 36 | Empty update body | 400 | 400 | PASS |
| 37 | Unsupported update fields | 400 | 400 | PASS |
| 38 | Conflicting update title | 409 | 409 | PASS |
| 39 | Anonymous delete | 401 | 401 | PASS |
| 40 | Invalid token delete | 401 | 401 | PASS |
| 41 | Expired token delete | 401 | 401 | PASS |
| 42 | Non-owner delete | 403 | 403 | PASS |
| 43 | Delete missing recipe | 404 | 404 | PASS |
| 44 | Owner delete | 204 | 204 | PASS |
| 45 | Admin override delete | 204 | 204 | PASS |
| 46 | Extra: Expired token list | 200 | 200 | PASS |
| 47 | Extra: Admin cannot read other private recipe | 403 | 403 | PASS |
| 48 | Extra: Blank registration username | 400 | 400 | PASS |
| 49 | Extra: Non-object update JSON | 400 | 400 | PASS |
| 50 | Extra: Missing ingredients | 400 | 400 | PASS |

**Overall: PASS**
