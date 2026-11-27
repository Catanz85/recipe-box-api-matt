=== APPLICATION CONFIGURATION ===
Development database: recipes.db
Testing database: instance/testing-recipes.db
Separate app instances: True — PASS
Development testing flag: False — PASS
Testing flag: True — PASS
Database paths differ: True — PASS

=== DEVELOPMENT BEFORE TESTING ===
{'users': 11, 'recipes': 7, 'test_users': 0, 'test_recipes': 0}

=== TEST DATABASE INITIALIZATION ===
Testing database initially absent: True — PASS
Testing database created: True — PASS
Created tables: ['recipes', 'users']
Required tables created: True — PASS
Testing rows after initialization: {'users': 0, 'recipes': 3, 'test_users': 0, 'test_recipes': 0}
Repeated initialization preserves rows: {'users': 0, 'recipes': 3, 'test_users': 0, 'test_recipes': 0} — PASS

=== API SMOKE TESTS ===
Register response: {'id': 1, 'username': 'isolation_38afd3582467'}
Register status: 201 — PASS
Login status: 200 — PASS
Login response: {'access_token': '[REDACTED]', 'id': 1, 'token_type': 'Bearer', 'username': 'isolation_38afd3582467'}
Bearer token returned: Bearer — PASS
List recipes response: [{'id': 1, 'ingredients': 'eggs, tomatoes, peppers, onion, cumin, paprika', 'instructions': 'Simmer the sauce, crack in the eggs, cover until just set.', 'is_public': True, 'title': 'Shakshuka'}, {'id': 2, 'ingredients': 'rolled oats, milk, yogurt, chia seeds, honey', 'instructions': 'Stir everything together and refrigerate overnight.', 'is_public': True, 'title': 'Overnight oats'}]
List recipes status: 200 — PASS
Anonymous list contains public recipes only: True — PASS
Anonymous creation rejected: 401 — PASS
Authenticated creation: 201 — PASS
Anonymous private recipe rejected: 401 — PASS
Owner can read private recipe: 200 — PASS

=== TESTING DATABASE AFTER REQUESTS ===
{'users': 1, 'recipes': 4, 'test_users': 1, 'test_recipes': 1}

=== DEVELOPMENT DATABASE AFTER REQUESTS ===
{'users': 11, 'recipes': 7, 'test_users': 0, 'test_recipes': 0}
Development row counts unchanged: {'users': 11, 'recipes': 7, 'test_users': 0, 'test_recipes': 0} — PASS
Development database fingerprint unchanged: 3cc0e8c7f2cc928ba0c41eda669b1cca05f26fcaf5aa1e0bb6cd0e0cf47c8440 — PASS
Test user exists in testing database: 1 — PASS
Test recipe exists in testing database: 1 — PASS
Test user absent from development database: 0 — PASS
Test recipe absent from development database: 0 — PASS

=== CLEANUP ===
Disposable testing database removed: True — PASS

=== ISOLATION TEST SUMMARY ===
Passed: 24/24
Overall: PASS
