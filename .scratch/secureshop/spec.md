# SecureShop: Build, Attack, Identify, Fix, Retest

Status: Draft for Sahith's approval. No code is written until this is approved.

## 1. Problem and goal

The assignment ("Red Team / Application Security") asks for an intentionally vulnerable e-commerce web application called SecureShop, which is assessed with OWASP ZAP, investigated, remediated, and then retested to prove that the fixes work. The central question the assignment wants answered is: "How vulnerable is the application, and can we prove that our remediation actually works?"

The goal of this project is to produce, entirely inside a local lab, a before-and-after evidence package: a vulnerable build, a hardened build, reproducible ZAP scans of both, and a written report that maps every finding to an OWASP Top 10 category.

## 2. Constraints and decisions already made

These were settled in the discussion phase and are not open for re-litigation.

- Stack: Python with Flask, SQLite, and server-rendered Jinja templates. The instructor has approved this stack. (This deliberately overrides the default FastAPI and React stack, because an old Flask pin is the easiest way to get a genuine outdated component.)
- Environment: Windows 11, `uv` virtual environment, no Docker. The app binds to 127.0.0.1 only, on port 8080.
- Scanner: OWASP ZAP installed by hand from zaproxy.org, with a JDK 17 or newer (Temurin) installed by hand. ZAP is driven from scripts through its command line or API, with an authenticated context, so the before scan and the after scan are the same command run against different builds.
- Versioning: `git init` in this folder. The vulnerable build is tagged `v1-vulnerable`. Fixes are made on a branch named `fixed`, so the diff between the tag and the branch is the remediation evidence.
- Process: This is a normal assignment, not hackathon mode. It follows spec, tickets, board.
- Scope of testing: Only the local app at http://127.0.0.1:8080. Nothing else is ever scanned or attacked, as the brief requires.
- Deliverable set (assumed, because the PDF ends at Phase 3): the working app, ZAP before and after reports, a findings write-up with OWASP mapping, fixes with retest evidence, and a short report that ties them together.

## 3. Open items that need Sahith

1. Due date. Not in the PDF and not yet given.
2. Whether pages after Phase 3 (Fix, Retest, Report, rubric) exist. The extracted PDF has 8 pages and ends with Phase 3 plus classroom notes. If a rubric turns up, this spec is amended before tickets are written.
3. Installing the JDK and ZAP by hand. I will provide exact download steps in the first ticket, and Sahith runs the installers.

## 4. The application

### 4.1 Required functionality (from the brief)

Public: home page, login, registration, product listing, product search, product details.
Authenticated: user profile, order history, cart.
Administrative: admin login, product management, user listing.

### 4.2 Data model (minimal)

- users: id, username, email, password, role (`user` or `admin`), created_at
- products: id, name, description, price, stock
- cart_items: id, user_id, product_id, quantity
- orders: id, user_id, total, created_at
- order_items: id, order_id, product_id, quantity, price

Seed data: about 10 products, one admin account, and at least two ordinary users who each have orders, so that the access-control flaw can be demonstrated between two real accounts. Seed credentials are documented in the README and are lab-only.

### 4.3 Planted weaknesses (vulnerable build)

| ID | OWASP category | Weakness | Where |
|---|---|---|---|
| V1 | A03 Injection | SQL injection through string-built queries | Product search (and login query) |
| V2 | A03 Injection | Reflected XSS from unescaped search term | Search results page |
| V3 | A01 Broken Access Control | IDOR: any logged-in user can read any order by id | `/orders/<id>` |
| V4 | A01 Broken Access Control | Admin area reachable without an admin role check | `/admin/*` |
| V5 | A07 Authentication Failures | Plaintext (or unsalted MD5) passwords, predictable session cookie, no lockout | Login and session handling |
| V6 | A05 Security Misconfiguration | Flask debug mode on, verbose stack traces, missing security headers, permissive cookie flags | App-wide |
| V7 | A06 Vulnerable and Outdated Components | Old Flask and Werkzeug pinned in `requirements.txt`, and vendored jQuery 1.x or 2.x | Dependencies and static files |
| V8 | A09 Logging Failures (bonus) | No logging of logins, failures, or admin actions | App-wide |

The brief requires at least four categories. This plan covers six (A01, A03, A05, A06, A07, A09), which leaves a spare if one weakness is hard to demonstrate.

### 4.4 Outdated component record (required by brief section 7)

For each of Flask, Werkzeug, and jQuery the report must state: component name, version used, latest version identified, why the old version is risky, and a CVE or advisory reference. The versions and CVE identifiers are to be chosen and checked against official sources (the project's own security advisories, NVD, and the GitHub advisory database) before they are pinned. No CVE number will be written from memory.

Risk to manage: Python on this machine is 3.14, and old Flask and Werkzeug releases may not run on it. The default is to have `uv` create the venv on an older Python (3.10 or 3.11) so that the old pins install and run. This is a tooling detail, not a product decision, and will be confirmed in the first ticket.

## 5. Remediation (fixed build)

Each vulnerability gets exactly one fix on the `fixed` branch, so the diff reads cleanly as evidence.

- V1: parameterised queries everywhere.
- V2: rely on Jinja autoescaping (remove any `|safe`) and add a Content-Security-Policy header.
- V3: check that the order belongs to the current user, otherwise return 403 or 404.
- V4: a role-checking decorator on every admin route.
- V5: salted password hashes (Werkzeug's `generate_password_hash`), a signed session with a proper secret key, `HttpOnly`, `SameSite`, and `Secure`-appropriate cookie flags, and basic login throttling or lockout.
- V6: debug off, a generic error page, and security headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
- V7: upgrade Flask and Werkzeug and replace jQuery with a current release (or remove it if unused).
- V8: structured logging of authentication events, access-control denials, and admin actions to a log file.

## 6. Scan and evidence plan

- One script starts the app on a chosen build, runs ZAP through its command line or API with an authenticated context (logging in as a seeded user and as the admin), and writes an HTML report and a JSON report to `evidence/before/` or `evidence/after/`.
- Scan metadata recorded each time, as the brief requires: scan date, target URL, ZAP version, scan type, number of alerts, severity, affected URL, and evidence.
- Retest is the same single command run against the `fixed` branch.
- Manual validation: for a selected set of findings (at minimum V1, V3, V4 and V7), a safe, non-weaponised proof by hand (for example a `curl` request or a screenshot) before and after the fix. The point is demonstration of impact, not a real exploit.
- ZAP results are treated as leads, not truth. The report notes at least one false positive or a weakness ZAP missed (for example, the IDOR is likely to need manual testing), because the brief explicitly says not to trust the scanner blindly.

## 7. Report structure

1. Scope, lab setup, and safety statement (local only).
2. Application overview and technology inventory, including the outdated component table from section 4.4.
3. Scan record (the fields in section 6) for the before scan.
4. Finding investigations. Every significant finding answers the five questions from Phase 3: What, Where, Why, Impact, Evidence. Each carries its OWASP mapping.
5. Remediation: a table of fix, file, and commit, plus the key diffs.
6. Retest: the after scan record, and a before-versus-after comparison table (alert counts by severity, and per-vulnerability pass or fail).
7. Residual risk and lessons learned, including what ZAP did not find.

## 8. Acceptance criteria (pass or fail)

Application
- [ ] At 127.0.0.1:8080 every page and flow in section 4.1 works on the vulnerable build (manual walkthrough or automated smoke test passes).
- [ ] The server binds only to 127.0.0.1 (confirmed by the `netstat` output).

Vulnerabilities (vulnerable build)
- [ ] V1: a crafted search string returns data that a normal search would not (demonstrated safely).
- [ ] V2: a script-bearing search term is reflected unescaped in the response body.
- [ ] V3: user A can fetch user B's order by changing the id.
- [ ] V4: a non-admin or anonymous request reaches an admin page.
- [ ] V5: passwords in the database are not strongly hashed, and the session cookie is predictable.
- [ ] V6: an error produces a stack trace, and the expected headers are absent.
- [ ] V7: `pip freeze` shows the pinned old versions and the jQuery file shows its old version, each with a verified CVE or advisory.
- [ ] V8: a failed login leaves no log entry.

Fixes (fixed build)
- [ ] Each of V1 to V8 now fails its demonstration above (the same manual proofs are rerun and the attack is blocked).
- [ ] A test suite covers the demo path and every fix, and passes on the `fixed` branch. The same tests, marked as expected to demonstrate the flaw, are kept for `v1-vulnerable`, so the tests are never weakened to pass.
- [ ] The app still works functionally on the fixed build (the smoke test from the first group passes).

Scanning
- [ ] ZAP version, JDK version, and the scan command are recorded.
- [ ] Before and after authenticated scans both complete and reach authenticated pages (the report lists URLs behind login, such as the cart, profile, and admin).
- [ ] The after scan shows fewer alerts than the before scan, with a per-finding explanation for any that remain.

Report
- [ ] Every section in section 7 is present, with evidence files linked.
- [ ] The report names at least one thing ZAP missed or got wrong.

## 9. Out of scope

- Deployment, hosting, HTTPS certificates, and any cloud resource.
- Real exploits or weaponised payloads. Proofs stay minimal and local.
- Scanning anything other than 127.0.0.1:8080.
- Payments, email, and real e-commerce features beyond what section 4.1 lists.
- A frontend framework (React, Vite, Tailwind). Pages are server-rendered Jinja with minimal CSS.

## 10. Risks

- Old Flask or Werkzeug may not install on Python 3.14. Mitigation: an older Python via `uv` (see section 4.4).
- ZAP authenticated scanning is fiddly. Mitigation: a dedicated early ticket to get one authenticated scan working on the vulnerable build before the rest is polished.
- Manual JDK and ZAP installs happen outside my control. Mitigation: do this ticket first, so a blocker shows up on day one.
- The due date is unknown. The PDF has a note about class time but no deadline.

## 11. Proposed ticket breakdown (for approval after the spec)

Tickets will be vertical slices of roughly half a day or less, written to `.scratch/secureshop/issues/` after this spec is approved.

1. Repo init, uv venv, project skeleton, and a "hello" Flask app on 127.0.0.1:8080.
2. Install JDK and ZAP (manual steps) and run one unauthenticated ZAP scan end to end.
3. Core app: data model, seed data, registration, login, product listing, details, and search.
4. Authenticated features: cart, profile, order history.
5. Admin area: admin login, product management, user listing.
6. Plant V1 to V8 and pin the outdated components with verified advisories. Tag `v1-vulnerable`.
7. Scripted authenticated ZAP scan, and the before scan with its evidence.
8. Manual validation of the selected findings, with evidence.
9. Fixes V1 to V8 on the `fixed` branch, with tests.
10. Retest scan, comparison table, and evidence.
11. Final report and README.

## 12. Approval

Waiting for Sahith to approve this spec, answer the due date question, and say "tickets" to move on.
