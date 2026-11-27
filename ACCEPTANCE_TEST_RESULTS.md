# Recipe API Acceptance Test Results

Tests performed against a temporary database copy.

| # | Scenario | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | API root | 200 | 200 | PASS |
| 2 | Register new user | 201 | 201 | PASS |
| 3 | Duplicate username | 409 | 409 | PASS |
| 4 | Missing registration password | 400 | 400 | PASS |
| 5 | Non-object registration JSON | 400 | 400 | PASS |
| 6 | Valid login | 200 | 200 | PASS |
| 7 | Wrong password | 401 | 401 | PASS |
| 8 | Unknown user | 401 | 401 | PASS |
| 9 | Missing login credentials | 400 | 400 | PASS |
| 10 | Non-object login JSON | 400 | 400 | PASS |
| 11 | Anonymous recipe list | 200 | 200 | PASS |
| 12 | Owner recipe list | 200 | 200 | PASS |
| 13 | Other user recipe list | 200 | 200 | PASS |
| 14 | Invalid token recipe list | 200 | 200 | PASS |
| 15 | Anonymous public recipe | 200 | 200 | PASS |
| 16 | Owner private recipe | 200 | 200 | PASS |
| 17 | Anonymous private recipe | 401 | 401 | PASS |
| 18 | Invalid token private recipe | 401 | 401 | PASS |
| 19 | Expired token private recipe | 401 | 401 | PASS |
| 20 | Other user private recipe | 403 | 403 | PASS |
| 21 | Missing recipe | 404 | 404 | PASS |
| 22 | Create public recipe by default | 201 | 201 | PASS |
| 23 | Create private recipe | 201 | 201 | PASS |
| 24 | Anonymous create | 401 | 401 | PASS |
| 25 | Invalid token create | 401 | 401 | PASS |
| 26 | Expired token create | 401 | 401 | PASS |
| 27 | Missing required recipe fields | 400 | 400 | PASS |
| 28 | Duplicate recipe title | 409 | 409 | PASS |
| 29 | Anonymous update | 401 | 401 | PASS |
| 30 | Invalid token update | 401 | 401 | PASS |
| 31 | Expired token update | 401 | 401 | PASS |
| 32 | Unauthorized update | 403 | 403 | PASS |
| 33 | Update missing recipe | 404 | 404 | PASS |
| 34 | Owner update | 200 | 200 | PASS |
| 35 | Admin update | 200 | 200 | PASS |
| 36 | Empty update JSON | 400 | 400 | PASS |
| 37 | Unsupported update fields | 400 | 400 | PASS |
| 38 | Duplicate title update | 409 | 409 | PASS |
| 39 | Anonymous delete | 401 | 401 | PASS |
| 40 | Invalid token delete | 401 | 401 | PASS |
| 41 | Expired token delete | 401 | 401 | PASS |
| 42 | Unauthorized delete | 403 | 403 | PASS |
| 43 | Delete missing recipe | 404 | 404 | PASS |
| 44 | Owner delete | 204 | 204 | PASS |
| 45 | Admin delete | 204 | 204 | PASS |

Total: 45
Passed: 45
Failed: 0
Overall: PASS
