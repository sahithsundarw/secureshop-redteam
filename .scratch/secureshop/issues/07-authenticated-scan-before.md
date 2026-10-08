---
id: 07
title: Scripted authenticated ZAP scan and the before scan
status: Backlog
priority: P1
depends_on: [02, 06]
spec_ref: spec.md section 6
---

## Goal
Extend the scan script from ticket 02 so it logs in as a seeded user and as the admin, crawls and scans pages behind login, and records all required metadata. Run it against `v1-vulnerable` to produce the before evidence.

## Acceptance criteria
- [ ] One command starts the app on a given build, scans it, and writes HTML and JSON reports to `evidence/before/`.
- [ ] The report lists authenticated URLs (cart, profile, orders, admin), proving authentication worked.
- [ ] A scan record file captures: scan date, target URL, ZAP version, scan type, number of alerts, severity breakdown, affected URLs and evidence.
- [ ] The script still refuses non-local targets.
- [ ] The same command can later be run unchanged against the fixed build, writing to `evidence/after/`.

## Test plan
Run the command, show the output and the list of authenticated URLs found, and show the alert counts by severity.

## Out of scope
Manual validation, fixes.
