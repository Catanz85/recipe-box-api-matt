# Recipe API Security Test Results

Tests performed against a temporary database copy.

| Check | Actual | Expected | Result |
|---|---|---|---|
| Create recipe | 201 | 201 | PASS |
| Anonymous protected write | 401 | 401 | PASS |
| Invalid token | 401 | 401 | PASS |
| Owner request | 200 | 200 | PASS |
| Non-owner request | 403 | 403 | PASS |
| Anonymous delete regression | 401 | 401 | PASS |
| Cross-user delete regression | 403 | 403 | PASS |
| Password hash present | True | True | PASS |
| Plaintext password column absent | True | True | PASS |
| Plaintext password not stored | True | True | PASS |
| Admin deleting another user's recipe | 204 | 204 | PASS |
