---
id: 05
title: Admin area - admin login, product management, user listing
status: In Review
priority: P1
depends_on: [03]
spec_ref: spec.md section 4.1
---

## Goal
Build the administrative functionality required by the brief: an admin login, product management (create, edit, delete), and a user listing.

## Acceptance criteria
- [x] The seeded admin can log in and reach `/admin`.
- [x] Admin can create, edit and delete a product, and changes show in the public catalogue.
- [x] Admin can view a list of users (username, email, role).
- [x] Admin pages are linked from an admin navigation area that ordinary users do not see.

## Test plan
Test-client tests as admin for each action. Role enforcement is deliberately not complete here; ticket 06 plants the weakness, and ticket 09 fixes it.

## Out of scope
Role-checking hardening, logging of admin actions.
