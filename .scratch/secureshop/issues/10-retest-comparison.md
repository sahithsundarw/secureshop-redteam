---
id: 10
title: Retest scan and before-versus-after comparison
status: Backlog
priority: P1
depends_on: [09]
spec_ref: spec.md sections 6, 8
---

## Goal
Run the same scan command against the fixed build and produce the evidence that the remediation worked.

## Acceptance criteria
- [ ] Reports and the scan record are written to `evidence/after/`, with the same metadata fields as the before scan.
- [ ] A comparison table shows alert counts by severity, before and after, and per-vulnerability pass or fail (V1 to V8).
- [ ] Every alert that remains is explained (accepted risk, false positive, or a new ticket).
- [ ] The manual proofs from ticket 08 are rerun and the results saved under `evidence/after/manual/`.
- [ ] The after scan reaches the same authenticated pages as the before scan.

## Test plan
Show the scan command output, the comparison table, and the rerun proof outputs.

## Out of scope
Writing the final report.
