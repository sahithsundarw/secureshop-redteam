# Board

## Backlog
- [06] Plant V1-V8, pin outdated components, tag v1-vulnerable (secureshop) — P1
- [07] Scripted authenticated ZAP scan and the before scan (secureshop) — P1
- [08] Investigate findings and manually validate (secureshop) — P1
- [09] Remediate V1-V8 on the fixed branch (secureshop) — P1
- [10] Retest scan and before-versus-after comparison (secureshop) — P1
- [11] Final report and README (secureshop) — P2

## Ready

## In Progress

## In Review
- [05] Admin area (secureshop) — P1. routes_admin.py with admin_required (403 for non-admin, redirect for anonymous; ticket 06 removes this for V4), product create/edit/delete (delete refused with 409 if referenced by orders or carts), user list without hashes, admin nav link. 81 pytest tests pass. Review pending.

## Done
- [04] Authenticated features: cart, profile, order history (secureshop) — P1. New routes_account.py blueprint (cart add/remove/checkout, profile, orders, login_required), 4 templates, nav links, add-to-cart form. Ownership check on /orders/<id> present for now (ticket 06 removes it for V3). 51 pytest tests pass (28 new). Fresh-context review still pending.
- [03] Core app: data model, seed data, public pages, registration and login (secureshop) — P1. SQLite schema (no drops), seed script that refuses a non-empty DB, public pages, register/login/logout, shared base template. 23 pytest tests pass; curl returned 200 on all pages and 404 on an unknown one; netstat shows 127.0.0.1:8080 only. SECRET_KEY now comes from the environment (random fallback) after a security-guidance warning. Fresh-context review found no code defects.
- [01] Repo init, uv venv and hello-world Flask app (secureshop) — P1. Python 3.11.14 venv, temporary Flask/Werkzeug 2.0.3 pins, 2 pytest tests pass, curl returns HTTP 200, netstat shows 127.0.0.1:8080 only. Commit 68fd96a.
- [02] Install JDK and ZAP, run one unauthenticated scan (secureshop) — P1. Temurin 17.0.20.1 and ZAP 2.17.0 installed (hashes verified), scripts/zap_scan.py ran a baseline scan (8 alerts: 4 Medium, 4 Low), refuses non-local targets, 8 pytest tests pass. Started while 01 was In Review, not Done.

## Blocked

## Run summary (2026-10-08)
- Verified: `git log` shows 8150430 (ticket 02) on top of 68fd96a (ticket 01). Tickets 01 and 02 stay In Review; only Sahith moves them to Done.
- Finished: 03 implemented in a fresh session (previous block was the guard hook on `DROP TABLE` plus auto mode), now In Review.
- Blocked: nothing. Ticket 04 is next once 03 is accepted.
- To review: the 01, 02 and 03 summaries above.
