# SecureShop (security lab)

An intentionally vulnerable e-commerce app for the Red Team / Application Security assignment.
Lab use only. It must run on 127.0.0.1 and nothing else may be scanned.

## Setup
- Python 3.11 (via `uv`). The machine default is 3.14, which old Flask/Werkzeug pins may not support.
- `uv venv --python 3.11 .venv`
- `uv pip install --python .venv\Scripts\python.exe -r requirements.txt`
- The pins in `requirements.txt` are temporary until ticket 06 chooses and verifies the final outdated versions.

## Run
`.venv\Scripts\python.exe app.py` then open http://127.0.0.1:8080/

## Database and seed data
- `.venv\Scripts\python.exe seed.py` creates `instance/secureshop.db` (tables, 10 products, 3 users, 4 orders). It refuses to run if the database already has data; delete `instance/secureshop.db` yourself to reseed.

Seed credentials (lab-only, never reuse anywhere real):

| Username | Password | Role |
|---|---|---|
| admin | AdminLab#1 | admin |
| alice | AliceLab#1 | user |
| bob | BobLab#1 | user |

## Scan (OWASP ZAP, local only)
See `docs/lab-setup.md` for tool versions and the scan command. `scripts/zap_scan.py` refuses any target other than 127.0.0.1 or localhost.

## Test
`.venv\Scripts\python.exe -m pytest`
