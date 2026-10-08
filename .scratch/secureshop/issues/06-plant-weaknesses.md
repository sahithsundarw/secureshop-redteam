---
id: 06
title: Plant weaknesses V1-V8, pin outdated components, tag v1-vulnerable
status: Backlog
priority: P1
depends_on: [04, 05]
spec_ref: spec.md sections 4.3, 4.4
---

## Goal
Introduce the eight controlled weaknesses and the outdated components, then freeze this state as the vulnerable build. Before pinning, choose Flask, Werkzeug and jQuery versions and verify the CVE or advisory references against official sources (project advisories, NVD, GitHub advisory database). No CVE number is written from memory.

## Acceptance criteria
- [ ] V1 SQL injection in search and login (string-built queries).
- [ ] V2 reflected XSS in search results.
- [ ] V3 IDOR on `/orders/<id>`.
- [ ] V4 admin routes lack a role check.
- [ ] V5 weak password storage, predictable session cookie, no lockout.
- [ ] V6 debug mode on, verbose errors, missing security headers.
- [ ] V7 old Flask and Werkzeug pinned, and old jQuery vendored under static files.
- [ ] V8 no logging of security events.
- [ ] `docs/components.md` lists, for each outdated component: name, version used, latest version identified, why risky, and a verified advisory reference with its source URL.
- [ ] Each weakness is a small, clearly commented change, so the diff against ticket 05 is reviewable.
- [ ] Commit tagged `v1-vulnerable`.

## Test plan
A test file asserts each weakness is present (marked so it is clearly a demonstration of the flaw). The full smoke test from tickets 03 to 05 still passes.

## Out of scope
Fixes, scanning.
