---
id: 02
title: Install JDK and ZAP, run one unauthenticated scan
status: Ready
priority: P1
depends_on: [01]
spec_ref: spec.md sections 2, 3, 6, 10
---

## Goal
Retire the biggest external risk first. Sahith installs a JDK 17 or newer (Temurin) and OWASP ZAP by hand from the official sites, following exact steps I provide. I then prove ZAP can be driven from a script by running a baseline scan against the hello-world app from ticket 01.

## Acceptance criteria
- [ ] Written install steps (download pages, installer choices, how to verify) are given to Sahith, who confirms the installs.
- [ ] `java -version` and the ZAP version are recorded in a `docs/lab-setup.md` file.
- [ ] A script starts ZAP headless (daemon mode) on a local port, runs a scan against http://127.0.0.1:8080 only, and writes an HTML report.
- [ ] The script refuses to run against any target other than 127.0.0.1 or localhost.
- [ ] The report file exists and opens.

## Test plan
Run the script, show the command and its output, list the report file. Run it once with a non-local target and show it refusing.

## Out of scope
Authenticated scanning, the vulnerable app, before and after comparison.
