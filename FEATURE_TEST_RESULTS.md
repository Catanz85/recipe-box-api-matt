# Recipe Count Feature Test Results

Endpoint: GET /recipes/count

Executed against a disposable SQLite database.

| Check | Actual | Expected | Result |
|---|---|---|---|
| Anonymous baseline count | (200, {'count': 2}) | (200, {'count': 2}) | PASS |
| Anonymous public count | (200, {'count': 3}) | (200, {'count': 3}) | PASS |
| Owner visible count | (200, {'count': 4}) | (200, {'count': 4}) | PASS |
| Other user visible count | (200, {'count': 4}) | (200, {'count': 4}) | PASS |
| Admin cannot count other private recipes | (200, {'count': 3}) | (200, {'count': 3}) | PASS |
| Invalid token falls back to public count | (200, {'count': 3}) | (200, {'count': 3}) | PASS |
| Expired token falls back to public count | (200, {'count': 3}) | (200, {'count': 3}) | PASS |
| Count matches existing list visibility | True | True | PASS |
| Count reflects visibility update | (200, {'count': 4}) | (200, {'count': 4}) | PASS |
| Count reflects recipe deletion | (200, {'count': 3}) | (200, {'count': 3}) | PASS |

Total: 10/10
Overall: PASS
