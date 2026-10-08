---
id: 08
title: Investigate findings and validate selected ones manually
status: Backlog
priority: P1
depends_on: [07]
spec_ref: spec.md sections 6, 7
---

## Goal
Treat ZAP as a source of leads. For every significant finding, answer What, Where, Why, Impact and Evidence, and manually and safely prove at least V1, V3, V4 and V7. Also record which planted weaknesses ZAP missed or got wrong (the IDOR is the likeliest miss), and at least one false positive or noise item.

## Acceptance criteria
- [ ] A findings document has one entry per significant finding with the five questions answered and an OWASP category.
- [ ] Safe proofs for V1, V3, V4 and V7 (curl commands with saved output, or screenshots) are stored under `evidence/before/manual/`.
- [ ] Proofs are minimal and local, with no weaponised payloads.
- [ ] The document lists at least one thing ZAP missed or got wrong.
- [ ] Every one of V1 to V8 is mapped to at least one finding or noted as not detected by ZAP.

## Test plan
Rerunnable proof commands recorded in the document, so ticket 10 can repeat them after the fixes.

## Out of scope
Fixing anything.
