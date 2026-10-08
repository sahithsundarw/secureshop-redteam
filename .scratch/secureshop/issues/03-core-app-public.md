---
id: 03
title: Core app - data model, seed data, public pages, registration and login
status: Backlog
priority: P1
depends_on: [01]
spec_ref: spec.md sections 4.1, 4.2
---

## Goal
Build the functional baseline of SecureShop: SQLite schema, seed data, and the public and login flows. At this stage the code is written plainly and works; weaknesses are planted later in ticket 06, so that the planting is a deliberate, reviewable step rather than an accident.

## Acceptance criteria
- [ ] Schema for users, products, cart_items, orders and order_items is created by an init script, and a seed script loads about 10 products, one admin, and at least two ordinary users who each have orders.
- [ ] Pages work: home, product listing, product details, product search, registration, login, logout.
- [ ] Registration creates a user; login establishes a session; logout ends it.
- [ ] Seed credentials are documented in the README as lab-only.
- [ ] Error handling is explicit and pages share one base template.

## Test plan
Flask test-client tests for each page (status code and key content), registration then login, wrong password rejected, search returns matching products.

## Out of scope
Cart, profile, order history, admin area, any deliberate vulnerability.
