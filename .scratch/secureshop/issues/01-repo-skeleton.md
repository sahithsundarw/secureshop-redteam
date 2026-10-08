---
id: 01
title: Repo init, uv venv and hello-world Flask app
status: In Review
priority: P1
depends_on: []
spec_ref: spec.md sections 2, 4.4, 10
---

## Goal
Turn this folder into a git repository with a working Python environment and a minimal Flask app that answers on 127.0.0.1:8080. This also settles the Python version question: confirm which Python (3.10 or 3.11 expected) lets the old Flask and Werkzeug pins install and run, since the machine default is 3.14.

## Acceptance criteria
- [ ] `git init` done, a `.gitignore` excludes the venv, database file, and ZAP session files, and an initial commit exists on the main branch.
- [ ] A `uv` virtual environment exists on a Python version that can install the old Flask and Werkzeug pins, and that version is written in the README.
- [ ] `requirements.txt` exists (final old pins are chosen in ticket 06; here a temporary working pin is acceptable and noted as such).
- [ ] The app starts and `curl http://127.0.0.1:8080/` returns HTTP 200.
- [ ] `netstat` shows the listener bound to 127.0.0.1 only, not 0.0.0.0.

## Test plan
Run the app, run the curl command, run netstat, and paste the outputs. Add one pytest that uses the Flask test client to assert the home page returns 200.

## Out of scope
Database, real pages, vulnerabilities, ZAP.
