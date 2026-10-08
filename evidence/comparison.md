# Before versus after

Before: `v1-vulnerable` scanned 2026-10-08T12:08:41 with ZAP 2.17.0. After: `fixed` scanned 2026-10-08T12:27:35 with ZAP 2.17.0.
Both runs used the same command (`scripts/auth_scan.py`) and the same roles (anonymous, alice, admin). Alert counts exclude the 'User Agent Fuzzer' informational noise, which ZAP repeats per URL (before: 648, after: 636).

## Alert counts by severity (instances)

| | High | Medium | Low | Informational | Total |
|---|---|---|---|---|---|
| Before | 7 | 169 | 96 | 3 | 275 |
| After | 0 | 89 | 55 | 2 | 146 |

## Alert types

| Risk | Alert | Before | After |
|---|---|---|---|
| High | SQL Injection | 2 | 0 |
| High | SQL Injection - SQLite (Time Based) | 5 | 0 |
| Medium | Absence of Anti-CSRF Tokens | 90 | 89 |
| Medium | Content Security Policy (CSP) Header Not Set | 43 | 0 |
| Medium | Missing Anti-clickjacking Header | 35 | 0 |
| Medium | Vulnerable JS Library | 1 | 0 |
| Low | Cookie No HttpOnly Flag | 1 | 0 |
| Low | Cookie without SameSite Attribute | 1 | 0 |
| Low | Server Leaks Version Information via "Server" HTTP Response Header Field | 57 | 55 |
| Low | X-Content-Type-Options Header Missing | 37 | 0 |
| Informational | Authentication Request Identified | 1 | 1 |
| Informational | Information Disclosure - Suspicious Comments | 1 | 0 |
| Informational | Session Management Response Identified | 1 | 1 |

## Authenticated pages reached

| Path | Before (anon / alice / admin) | After (anon / alice / admin) |
|---|---|---|
| `/cart` | 302 / 200 / 200 | 302 / 200 / 200 |
| `/profile` | 302 / 200 / 200 | 302 / 200 / 200 |
| `/orders` | 302 / 200 / 200 | 302 / 200 / 200 |
| `/orders/1` | 302 / 200 / 200 | 302 / 200 / 404 |
| `/admin` | 200 / 200 / 200 | 302 / 403 / 200 |
| `/admin/products` | 200 / 200 / 200 | 302 / 403 / 200 |
| `/admin/users` | 200 / 200 / 200 | 302 / 403 / 200 |

Before: URLs discovered per role: {'anonymous': 21, 'alice': 28, 'admin': 42}.

After: URLs discovered per role: {'anonymous': 20, 'alice': 26, 'admin': 40}.

## Per-vulnerability result (manual proofs)

| ID | Weakness | Attack works before | Blocked after | Result |
|---|---|---|---|---|
| V1 | SQL injection (A03) | yes | yes | PASS |
| V2 | Reflected XSS (A03) | yes | yes | PASS |
| V3 | IDOR on /orders/<id> (A01) | yes | yes | PASS |
| V4 | Admin without role check (A01) | yes | yes | PASS |
| V5 | Weak auth: MD5, weak key, no lockout (A07) | yes | yes | PASS |
| V6 | Misconfiguration: debug, headers, cookie flags (A05) | yes | yes | PASS |
| V7 | Outdated components (A06) | yes | yes | PASS |
| V8 | No security logging (A09) | proven by test suite (see report) | proven by test suite | PASS |
