---
id: 04
title: Authenticated features - cart, profile, order history
status: Backlog
priority: P1
depends_on: [03]
spec_ref: spec.md section 4.1
---

## Goal
Add the pages that require a logged-in user: the shopping cart (add, remove, view, checkout into an order), the user profile (view and edit), and order history (list and detail by order id).

## Acceptance criteria
- [ ] Anonymous requests to these pages redirect to login.
- [ ] A logged-in user can add and remove cart items and check out, which creates an order and its items.
- [ ] Profile shows and updates the user's own details.
- [ ] Order history lists the user's orders, and `/orders/<id>` shows an order's detail.
- [ ] Seeded users A and B each have distinct orders available for later access-control demonstrations.

## Test plan
Test-client tests for each flow, plus an anonymous-redirect test per page.

## Out of scope
Admin pages, deliberately missing ownership checks (those are planted in ticket 06).
