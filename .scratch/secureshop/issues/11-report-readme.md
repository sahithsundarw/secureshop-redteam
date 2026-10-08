---
id: 11
title: Final report and README
status: Backlog
priority: P2
depends_on: [10]
spec_ref: spec.md sections 7, 8
---

## Goal
Assemble everything into the deliverable: a report following the structure in the spec, and a README that lets anyone reproduce both builds and both scans.

## Acceptance criteria
- [ ] The report contains all seven sections from the spec, with links to the evidence files.
- [ ] The outdated component table includes name, version used, latest version, risk, and verified advisory reference.
- [ ] The README covers setup, how to run each build, seed credentials (lab-only), how to run the scan, and how to run the tests.
- [ ] The report states the local-only safety scope.
- [ ] Any rubric or due-date constraints from Sahith are checked off.

## Test plan
Follow the README on a fresh clone of the repository and confirm both builds start and the scan command runs.

## Out of scope
New findings or fixes. If something new turns up, it becomes a Backlog ticket.
