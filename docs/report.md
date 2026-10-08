# SecureShop: build, attack, identify, fix, retest

## 1. Scope, lab setup and safety statement

SecureShop is a small Flask e-commerce app built to be vulnerable, assessed with OWASP ZAP, fixed, and retested. Everything ran on one Windows 11 machine, against http://127.0.0.1:8080 only. The scan scripts refuse any other host, nothing was exposed to a network, and no weaponised payloads were used: manual proofs are plain requests that read data the lab seed already contains.

Tools: Python 3.11.14 (`uv`), Temurin JDK 17.0.20.1, OWASP ZAP 2.17.0. Details and hash checks are in `docs/lab-setup.md`.

## 2. Application overview and technology inventory

Public pages (home, products, search, product detail, register, login), signed-in pages (cart, checkout, profile, order history) and an admin area (product management, user list). Stack: Flask, SQLite, server-rendered Jinja templates.

Outdated components (verified advisories and sources are in `docs/components.md`):

| Component | Version used | Latest verified | Risk | Advisory |
|---|---|---|---|---|
| Flask | 2.0.3 | 3.1.3 | Session cookie handling can leak through caching proxies | CVE-2023-30861 (GHSA-m2qf-hxjv-5gpq), CVE-2026-27205 (GHSA-68rp-wp8r-4726) |
| Werkzeug | 2.0.3 | 3.1.9 | Multipart parser DoS; debugger code execution if exposed | CVE-2023-25577, CVE-2024-49767, CVE-2024-34069 |
| jQuery (vendored) | 1.12.4 | 4.0.0 (3.7.1 on the 3.x line) | XSS in HTML handling; cross-origin script evaluation | CVE-2020-11022, CVE-2020-11023, CVE-2015-9251 |

## 3. Scan record (before)

| Field | Value |
|---|---|
| Scan date | 2026-10-08 12:08 |
| Target | http://127.0.0.1:8080 (git tag `v1-vulnerable`) |
| ZAP version | 2.17.0 |
| Scan type | Authenticated: spider, passive and active, as anonymous, alice and admin |
| Alerts | 923 instances; 275 excluding 648 "User Agent Fuzzer" noise rows |
| Severity | High 7, Medium 169, Low 96, Informational 3 |

Authentication worked: `/cart`, `/profile`, `/orders` and `/orders/1` return 302 for anonymous and 200 for alice and admin. Files: `evidence/before/report.html`, `report.json`, `scan-record.json` (which lists every alert with its URL, parameter and evidence).

## 4. Finding investigations

Twelve findings, each with What, Where, Why, Impact, Evidence and an OWASP category, are in `docs/findings.md`. In short:

- ZAP found V1 (SQL injection), and parts of V5, V6 and V7 (cookie flags, missing headers, vulnerable jQuery).
- ZAP **missed** V2 (reflected XSS), V3 (IDOR), V4 (admin without role check), the stack trace in V6, and the weak hashing, signing key and missing lockout in V5. V8 (no logging) is not visible to a black-box scan.
- ZAP raised a **false positive**: 5 High "SQL Injection - SQLite (Time Based)" alerts on `/admin/products/N/edit`, a route that uses a bound parameter. They also vanish in the after scan although that route's code did not change.
- ZAP reported a **real, unplanted** issue: no anti-CSRF tokens (90 Medium).

Manual proofs: `evidence/before/manual/V1.json` to `V7.json`.

## 5. Remediation

All fixes are on branch `fixed`, which forks from tag `v1-vulnerable`, so `git diff v1-vulnerable fixed` is the remediation evidence.

| ID | Fix | Files | Commit |
|---|---|---|---|
| V1 | Parameterised queries in search and login | `routes_shop.py`, `routes_auth.py` | 242ba62 (search), ce12b63 (login) |
| V2 | Autoescaped search term (removed `|safe`) | `templates/search.html` | 242ba62 |
| V3 | Order query also filters on the signed-in user; 404 otherwise | `routes_account.py` | 809c015 |
| V4 | `admin_required` redirects anonymous users and returns 403 to non-admins | `routes_admin.py` | 809c015 |
| V5 | Salted password hashes, random secret key from the environment, HttpOnly and SameSite cookies, lockout after 5 failures in 5 minutes (HTTP 429) | `routes_auth.py`, `seed.py`, `app.py` | ce12b63, b82babd |
| V6 | Debug off, generic 403 and 500 pages, CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy | `app.py` | b82babd |
| V7 | Flask 3.1.3, Werkzeug 3.1.9, jQuery removed (it was unused) | `requirements.txt`, `templates/base.html`, `static/vendor/` | d551e3d |
| V8 | Authentication, access-denial and admin-action events logged to `logs/security.log` | `security_log.py`, `routes_*.py`, `app.py` | 809c015, ce12b63, b82babd |

Tests: `tests/test_fixes.py` has one or more tests per fix. It replaces `tests/test_vulnerabilities.py`, which stays on the tag as the demonstration of each flaw, so no test was weakened. The two `xfail` markers that expected V3 and V4 to be absent were removed. On `fixed`: 104 passed. On `main`: 87 passed, 10 expected failures.

## 6. Retest

Same command, run against `fixed` on 2026-10-08 12:27 with ZAP 2.17.0. Full tables: `evidence/comparison.md`. Files: `evidence/after/`.

| | High | Medium | Low | Informational | Total |
|---|---|---|---|---|---|
| Before | 7 | 169 | 96 | 3 | 275 |
| After | 0 | 89 | 55 | 2 | 146 |

Per-vulnerability result from the rerun manual proofs (`evidence/after/manual/`):

| ID | Weakness | Before | After |
|---|---|---|---|
| V1 | SQL injection | Rows from `users` returned in search; login bypassed | Blocked |
| V2 | Reflected XSS | Script tag reflected verbatim | Escaped |
| V3 | IDOR | Alice read orders 3 and 4 (200) | 404 |
| V4 | Admin access | 200 for anonymous and alice | 302 and 403 |
| V5 | Authentication | No lockout, no cookie flags | 429 after 5 failures; HttpOnly, SameSite=Lax |
| V6 | Misconfiguration | 4 headers missing, stack trace on error | All present, generic error page |
| V7 | Components | jQuery 1.12.4, Werkzeug 2.0.3 | jQuery gone (404), Werkzeug 3.1.9 |
| V8 | Logging | No entries (test) | Entries written (test) |

The after scan reached the same authenticated pages (`/cart`, `/profile`, `/orders`, `/orders/1`, `/admin/...`). `/orders/1` is 404 for admin because order 1 belongs to alice, which is correct.

Alerts that remain, and why:

| Alert | Count | Explanation |
|---|---|---|
| Absence of Anti-CSRF Tokens (Medium) | 89 | Genuine, not part of V1-V8. Accepted as residual risk for this lab; `SameSite=Lax` reduces cross-site POSTs but is not a token. Recommended follow-up ticket. |
| Server header leaks version (Low) | 55 | Now `Werkzeug/3.1.9 Python/3.11`. It comes from the Flask development server; a production WSGI server and proxy would control the header. Accepted for the lab. |
| Authentication Request Identified, Session Management Response Identified (Informational) | 2 | Informational notes about the login flow, not vulnerabilities. |

## 7. Residual risk and lessons learned

- ZAP is a lead generator. It found 1 of 8 planted weaknesses outright and parts of 3 more; broken access control and logic flaws (V3, V4) and stored-secret problems (V5, V8) need manual testing and code review. It also reported one false positive.
- The fixed build is not "secure". Open items: CSRF tokens, the development server and its banner, an in-memory lockout that resets on restart and is not shared between processes, Secure cookies off because the lab runs on plain HTTP, and no audit of transitive dependencies beyond the advisories listed.
- The session cookie is signed with a random key generated at start-up unless `SECRET_KEY` is set, so sessions end on restart.
- **The after scan ran before the storefront redesign.** The shop's look (images, layout, footer) was added afterwards to `main` and `fixed` as a presentation-only change. It touches templates and CSS, not routes, queries or headers, and `fixed` still passes its 104 tests. The scan evidence describes the build as it was scanned.
