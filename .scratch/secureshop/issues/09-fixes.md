---
id: 09
title: Remediate V1-V8 on the fixed branch with tests
status: Backlog
priority: P1
depends_on: [08]
spec_ref: spec.md section 5
---

## Goal
Create the `fixed` branch from `v1-vulnerable` and remediate each weakness with one focused change, so the diff reads as evidence. Fix root causes; never weaken a test to make it pass.

## Acceptance criteria
- [ ] V1 parameterised queries everywhere.
- [ ] V2 no unescaped output, plus a Content-Security-Policy header.
- [ ] V3 order ownership check (403 or 404 for other users' orders).
- [ ] V4 role-check decorator on every admin route.
- [ ] V5 salted password hashes, signed session with a real secret key, cookie flags, and login throttling.
- [ ] V6 debug off, generic error pages, and the security headers from the spec.
- [ ] V7 Flask and Werkzeug upgraded and jQuery updated or removed, with `docs/components.md` updated.
- [ ] V8 authentication events, access denials and admin actions are logged to a file.
- [ ] A test per fix passes on `fixed`, and the full smoke test still passes.
- [ ] A fix table (vulnerability, file, commit) is recorded.

## Test plan
Run the test suite and show the output. Run the rerunnable proofs from ticket 08 and show each attack is now blocked.

## Out of scope
New features, scanning (ticket 10).
