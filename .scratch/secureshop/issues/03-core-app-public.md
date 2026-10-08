---
id: 03
title: Core app - data model, seed data, public pages, registration and login
status: Done
priority: P1
depends_on: [01]
spec_ref: spec.md sections 4.1, 4.2
---

## History
An earlier unattended run was blocked: the guard hook denied a heredoc whose schema contained `DROP TABLE`, and auto mode then refused the rewrite. Implemented in a fresh session with the no-drops design (`CREATE TABLE IF NOT EXISTS`, seed refuses a non-empty database), files written with the Write tool. Note 03 depends on 01, which is still In Review, not Done.

## Result (In Review)
- 23 pytest tests pass. Live check: 200 on `/`, `/products`, `/products/1`, `/search?q=lamp`, `/login`, `/register`; 404 on an unknown path; alice login returns 302; netstat shows only 127.0.0.1:8080.
- Seed run twice: first succeeds, second exits 1 with "Database is not empty".
- `SECRET_KEY` is read from the environment with a random fallback, after a security-guidance warning.
- Fresh-context review found no code defects; its two tracking-file notes are fixed.

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
