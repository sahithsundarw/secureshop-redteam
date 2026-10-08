# SecureShop (security lab)

An intentionally vulnerable e-commerce app, built to be attacked, fixed and retested for the Red Team / Application Security assignment. **Lab use only.** It binds to 127.0.0.1:8080, and nothing else may ever be scanned or attacked.

| Build | Where | What it is |
|---|---|---|
| Vulnerable | git tag `v1-vulnerable` (the app code on `main` matches it, plus tooling, evidence and docs) | Planted weaknesses V1-V8, Flask/Werkzeug 2.0.3, jQuery 1.12.4 |
| Fixed | branch `fixed` | One focused fix per weakness, Flask 3.1.3, Werkzeug 3.1.9, jQuery removed |

Start with `docs/report.md` (the write-up) and `evidence/comparison.md` (before versus after).

## Setup
- Python 3.11 via `uv` (the machine default 3.14 is not used, because the old pins need an older Python).
- `uv venv --python 3.11 .venv`
- `uv pip install --python .venv\Scripts\python.exe -r requirements.txt`
- For the scans: a JDK 17+ and OWASP ZAP 2.17.0, installed as described in `docs/lab-setup.md`.

## Run a build
Vulnerable (this checkout):
`.venv\Scripts\python.exe seed.py` (once) then `.venv\Scripts\python.exe app.py`, and open http://127.0.0.1:8080/

Fixed: `git worktree add ..\secureshop-fixed fixed`, create a venv there the same way (its `requirements.txt` has the upgraded pins), then seed and run as above. `scripts/auth_scan.py` does all of this by itself under `C:\Users\sahit\tools\builds\`.

Seed credentials (lab-only, never reuse anywhere real):

| Username | Password | Role |
|---|---|---|
| admin | AdminLab#1 | admin |
| alice | AliceLab#1 | user |
| bob | BobLab#1 | user |

## Scan (OWASP ZAP, local only)
One command per build. It checks the build out, seeds a throwaway database, starts the app, logs in as alice and admin, runs a spider plus passive plus active scan as anonymous, alice and admin, and writes the reports:

```
.venv\Scripts\python.exe scripts\auth_scan.py --build before    # tag v1-vulnerable -> evidence/before/
.venv\Scripts\python.exe scripts\auth_scan.py --build after     # branch fixed      -> evidence/after/
.venv\Scripts\python.exe scripts\compare.py                     # evidence/comparison.md
```

Each run takes roughly 15 to 25 minutes. Both scripts refuse any target other than 127.0.0.1 or localhost (exit code 2).

## Manual proofs (V1-V7)
```
.venv\Scripts\python.exe scripts\manual_proofs.py --build before   # evidence/before/manual/
.venv\Scripts\python.exe scripts\manual_proofs.py --build after    # evidence/after/manual/
```

## Test
`.venv\Scripts\python.exe -m pytest` on `main` (87 passed, 10 expected failures that document the planted flaws). On `fixed`: 104 passed.

## Repository layout
- `app.py`, `routes_*.py`, `templates/`, `static/`: the app
- `scripts/`: scan, proof and comparison tooling
- `docs/`: `report.md`, `findings.md`, `components.md`, `lab-setup.md`
- `evidence/`: ZAP reports, scan records, manual proofs, `comparison.md`
- `.scratch/`: spec, tickets and board
