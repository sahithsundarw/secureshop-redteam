# Lab setup

Everything runs on this one machine and only against http://127.0.0.1:8080. Nothing else is scanned.

## Tool versions
| Tool | Version | Location | Source and verification |
|---|---|---|---|
| Python | 3.11.14 | `.venv` (via `uv`) | Needed because old Flask/Werkzeug pins may not support the default 3.14 |
| JDK | Temurin 17.0.20.1+1 (portable zip, no admin install) | `C:\Users\sahit\tools\jdk17` | Downloaded from Adoptium; SHA-256 matches the published `.sha256.txt` (e53a79c3...c7cb0) |
| OWASP ZAP | 2.17.0 (cross-platform zip) | `C:\Users\sahit\tools\zap` | Downloaded from the zaproxy GitHub release; SHA-256 94c8f767...fbff0 matches the release page |

`java -version` output:
```
openjdk version "17.0.20.1" 2026-08-18
OpenJDK Runtime Environment Temurin-17.0.20.1+1 (build 17.0.20.1+1)
OpenJDK 64-Bit Server VM Temurin-17.0.20.1+1 (build 17.0.20.1+1, mixed mode, sharing)
```

ZAP's own working data lives in `C:\Users\sahit\tools\zap-home`, outside the project and OneDrive.

## Running a scan
1. Start the app: `.venv\Scripts\python.exe app.py`
2. In another shell: `.venv\Scripts\python.exe scripts\zap_scan.py --target http://127.0.0.1:8080 --out evidence/baseline`

The script starts ZAP headless on 127.0.0.1:8090 with a random API key, spiders the target, waits for the passive scan, writes `report.html` and `scan-record.json`, then shuts ZAP down. It refuses any target whose host is not `127.0.0.1` or `localhost` (exit code 2).

## First baseline (ticket 02)
Unauthenticated spider plus passive scan of the hello-world app: 8 alerts (4 Medium, 4 Low). These are generic header and configuration alerts from a bare Flask page, not SecureShop findings. See `evidence/baseline/`.
