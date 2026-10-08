# Finding investigations (vulnerable build, tag `v1-vulnerable`)

Scope: only the local lab app at http://127.0.0.1:8080. ZAP is treated as a source of leads, not as truth. Each finding below answers What, Where, Why, Impact and Evidence, with an OWASP Top 10 (2021) category.

Evidence files: `evidence/before/report.html`, `evidence/before/report.json`, `evidence/before/scan-record.json`, and the manual proofs in `evidence/before/manual/`.

Rerun the proofs (starts the chosen build, sends minimal local requests, saves the output):

```
.venv\Scripts\python scripts\manual_proofs.py --build before
.venv\Scripts\python scripts\manual_proofs.py --build after
```

## Scan summary (before)

ZAP 2.17.0, authenticated scan as anonymous, alice and admin (spider, passive and active). 923 alert instances. Excluding the 648 "User Agent Fuzzer" informational noise rows, that is 275: 7 High, 169 Medium, 96 Low, 3 Informational, in 12 alert types. Authentication worked: `/cart`, `/profile`, `/orders`, `/orders/1` return 302 for anonymous and 200 for alice and admin, and the spider found `/cart`, `/orders/1`, `/orders/2` and `/profile` as alice and `/admin/products/N/edit` as admin.

## F1 SQL injection in search and login (V1, A03 Injection)

- **What:** User input is concatenated into SQL text, so the query structure can be changed.
- **Where:** `GET /search?q=` (`routes_shop.py`) and the `username` field of `POST /login` (`routes_auth.py`).
- **Why:** f-strings build the SQL instead of bound parameters.
- **Impact:** A search string with a `UNION SELECT` returns rows from the `users` table inside the product list, and `admin'--` as username signs in as admin with a wrong password.
- **Evidence:** ZAP High "SQL Injection" on `/search` and `/login`. Manual proof `evidence/before/manual/V1.json`: the probe returned the usernames `admin`, `alice`, `bob` in the product list; the login probe returned 302 to `/`.

## F2 ZAP "SQL Injection - SQLite (Time Based)" on `/admin/products/N/edit`: false positive

- **What:** 5 High alerts claim time-based SQL injection on the product edit pages.
- **Where:** `/admin/products/<id>/edit`.
- **Why it is wrong:** The route converts the id with `<int:product_id>` and `_get_product` runs `SELECT * FROM products WHERE id = ?` with a bound parameter (`routes_admin.py`). There is no injectable input. The probable cause is response-time noise while the active scanner ran eight threads against a debug-mode server, which time-based checks cannot tell apart from a real delay. That cause is a hypothesis; I did not reproduce the delay.
- **Impact:** None. Counting these would overstate the High total by 5.
- **Evidence:** `evidence/before/report.json` lists the alerts; the code reference above disproves them. The route's code is identical in the fixed build, and the alerts do not appear in the after scan, which supports reading them as noise rather than a real flaw.

## F3 Missing security headers (V6, A05 Security Misconfiguration)

- **What:** No Content-Security-Policy, no anti-clickjacking header, no `X-Content-Type-Options`, and the `Server` header discloses `Werkzeug/2.0.3 Python/3.11.14`.
- **Where:** Every response.
- **Why:** The app sets none of these headers.
- **Impact:** XSS has no second line of defence, pages can be framed (clickjacking), browsers may sniff content types, and the exact framework version helps an attacker pick known exploits for it.
- **Evidence:** ZAP Medium "Content Security Policy (CSP) Header Not Set" (43), "Missing Anti-clickjacking Header" (35), Low "X-Content-Type-Options Header Missing" (37), "Server Leaks Version Information" (57). Manual proof `V6.json` lists all four headers missing.

## F4 Debug mode and stack traces (V6, A05)

- **What:** An error produces a Werkzeug debugger page with a stack trace.
- **Where:** Any unhandled exception, for example `GET /search?q=x' OR` (a malformed query).
- **Why:** `DEBUG = True` and no generic 500 handler.
- **Impact:** Leaks source paths, code and library versions; the interactive debugger is a code-execution risk if ever exposed (CVE-2024-34069 in `docs/components.md`).
- **Evidence:** Manual proof `V6.json`: status 500 and `stack_trace_in_error_page: true`. **ZAP did not report this** (no "Application Error Disclosure" alert), so it is a scanner miss.

## F5 Session cookie flags (V6 and V5, A05 and A07)

- **What:** The session cookie has no `HttpOnly` and no `SameSite`.
- **Where:** `Set-Cookie` on `POST /login`.
- **Why:** `SESSION_COOKIE_HTTPONLY` is set to False and SameSite is not configured.
- **Impact:** Script on the page can read the cookie (made worse by F7 XSS), and the cookie is sent on cross-site requests.
- **Evidence:** ZAP Low "Cookie No HttpOnly Flag" and "Cookie without SameSite Attribute" on `/login`. Manual proof `V5.json`: `session=<value>; Path=/`.

## F6 Outdated components (V7, A06 Vulnerable and Outdated Components)

- **What:** Flask 2.0.3, Werkzeug 2.0.3 and a vendored jQuery 1.12.4.
- **Where:** `requirements.txt` and `static/vendor/jquery-1.12.4.min.js`.
- **Why:** Pinned deliberately old; advisories with exact affected ranges and sources are in `docs/components.md`.
- **Impact:** Known vulnerabilities such as CVE-2020-11022/11023 (jQuery XSS), CVE-2023-25577 (Werkzeug multipart DoS), CVE-2023-30861 (Flask session cookie caching). Whether each is reachable in this app is not claimed here; the point is the exposure.
- **Evidence:** ZAP Medium "Vulnerable JS Library" on the jQuery file (the only one of the three it found). Manual proof `V7.json`: jQuery banner `1.12.4` and `Server: Werkzeug/2.0.3`. ZAP only learned the Werkzeug version from the Server header (F3) and did not flag Flask or Werkzeug as outdated.

## F7 Reflected XSS in search (V2, A03 Injection): missed by ZAP

- **What:** The search term is echoed into the page without escaping.
- **Where:** `GET /search?q=` (`templates/search.html`, `|safe`).
- **Why:** The template disables Jinja autoescaping for the term.
- **Impact:** A crafted link runs attacker script in the victim's session.
- **Evidence:** Manual proof `V2.json`: `<script>alert(1)</script>` appears verbatim in the response body (`reflected_unescaped: true`). The script is never run; the proof only checks the response text. **ZAP reported no XSS alert in this run**, although it did report SQL injection on the same parameter. I did not establish why.

## F8 IDOR on order pages (V3, A01 Broken Access Control): missed by ZAP

- **What:** Any signed-in user can read any order by changing the id.
- **Where:** `GET /orders/<id>` (`routes_account.py`).
- **Why:** The query filters on the order id only, not on the owner.
- **Impact:** Disclosure of other customers' purchases.
- **Evidence:** Manual proof `V3.json`: alice owns orders 1 and 2; orders 3 and 4 (bob's) also returned 200. ZAP cannot know that order 3 belongs to someone else, so it reported nothing. This is the expected miss for a scanner with no model of ownership.

## F9 Admin area has no role check (V4, A01): missed by ZAP

- **What:** Anonymous and ordinary users can open admin pages and read the user list.
- **Where:** `/admin`, `/admin/products`, `/admin/users`.
- **Why:** `admin_required` was reduced to a pass-through.
- **Impact:** Anyone can see all usernames and emails and use the product management pages.
- **Evidence:** Manual proof `V4.json`: `/admin/users` returned 200 for anonymous, alice and admin, and the anonymous response contained `alice@secureshop.test`. ZAP reached the pages but, with no notion of who should see them, raised no alert.

## F10 Weak authentication (V5, A07 Identification and Authentication Failures): missed by ZAP

- **What:** Passwords are stored as unsalted MD5, the session signing key is the guessable string `secret` (so cookies can be forged), and there is no lockout.
- **Where:** `routes_auth.py`, `seed.py`, `app.py`.
- **Why:** Deliberate shortcuts in hashing, key and rate limiting.
- **Impact:** A database leak exposes passwords to fast lookup; anyone who guesses the key can mint an admin session; passwords can be guessed without limit.
- **Evidence:** Manual proof `V5.json`: eight consecutive wrong passwords all returned 401, never a lockout. The MD5 storage and the forged-cookie result are shown by `tests/test_vulnerabilities.py` on the tag (`test_v5_passwords_stored_as_unsalted_md5`, `test_v5_session_cookie_forgeable_with_known_key`). A black-box scanner cannot see storage or signing keys, so ZAP raised nothing.

## F11 No security logging (V8, A09 Security Logging and Monitoring Failures): not detectable by ZAP

- **What:** Failed logins, access denials and admin actions leave no log entry.
- **Where:** App-wide.
- **Why:** No logging is implemented.
- **Impact:** Attacks such as F1 and F10 would go unnoticed and could not be investigated afterwards.
- **Evidence:** `tests/test_vulnerabilities.py::test_v8_failed_login_and_admin_action_leave_no_log_entry` on the tag. Logging is server-side behaviour a black-box scan cannot observe.

## F12 Absence of anti-CSRF tokens (not planted, A01)

- **What:** 90 Medium alerts: state-changing forms (login, register, cart, profile, admin product forms) carry no CSRF token.
- **Where:** All POST forms.
- **Why:** Never implemented; it is not one of V1-V8.
- **Impact:** A malicious page can make a signed-in user's browser submit these forms. `SameSite=Lax` (added in the fixed build) limits cross-site POSTs in modern browsers but is not a CSRF token.
- **Evidence:** ZAP Medium "Absence of Anti-CSRF Tokens". Judged a genuine finding that falls outside the planned scope. It remains in the after scan and is carried as residual risk in the report.

## Noise

- "User Agent Fuzzer" (648 informational instances) is ZAP repeating a request with different User-Agent strings, once per URL. It carries no finding.
- "Authentication Request Identified", "Session Management Response Identified" and "Suspicious Comments" in the jQuery file are informational and not vulnerabilities.

## V1-V8 mapping

| ID | Weakness | ZAP result | Finding |
|---|---|---|---|
| V1 | SQL injection | Detected (High, `/search`, `/login`) | F1 |
| V2 | Reflected XSS | **Not detected** | F7 |
| V3 | IDOR | **Not detected** | F8 |
| V4 | Admin without role check | **Not detected** | F9 |
| V5 | Weak authentication | Cookie flags only (Low); hashing, key and lockout **not detected** | F5, F10 |
| V6 | Misconfiguration | Headers, Server banner and cookie flags detected; stack trace **not detected** | F3, F4, F5 |
| V7 | Outdated components | jQuery only (Medium); Flask and Werkzeug **not flagged** | F6 |
| V8 | No logging | **Not detectable** by a black-box scan | F11 |

Summary: ZAP found V1 and parts of V5, V6 and V7, and missed V2, V3, V4, V8 and the stack trace entirely. It also produced one false positive (F2) and a large block of noise.
