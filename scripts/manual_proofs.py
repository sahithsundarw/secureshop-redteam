"""Minimal, local-only manual proofs for V1, V3, V4 and V7 (and V5/V6/V8 observations).

    python scripts/manual_proofs.py --build before    # tag v1-vulnerable -> evidence/before/manual/
    python scripts/manual_proofs.py --build after     # branch fixed      -> evidence/after/manual/

Starts the chosen build on 127.0.0.1:8080 with a throwaway database, makes a handful of plain HTTP
requests (the same ones a person would type with curl), and saves each request and response summary.
Proofs read data that the lab seed already contains; nothing is modified or destroyed.
"""
import argparse
import json
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.auth_scan import (  # noqa: E402
    BUILDS, TARGET, CREDENTIALS, _NoRedirect, login, prepare_build, start_app,
)
from scripts.zap_scan import check_target  # noqa: E402


def fetch(path, cookie=None, data=None):
    """Return (status, headers, body) without following redirects."""
    request = urllib.request.Request(TARGET + path, data=data)
    if cookie:
        request.add_header("Cookie", f"session={cookie}")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        resp = opener.open(request, timeout=10)
    except urllib.error.HTTPError as err:
        resp = err
    return resp.status if hasattr(resp, "status") else resp.code, dict(resp.headers), resp.read().decode("utf-8", "replace")


def proof_v1(cookies):
    """Search with a quote-based string; compare with a normal search."""
    normal = fetch("/search?q=lamp")
    probe = fetch("/search?q=" + urllib.parse.quote("zzz%' UNION SELECT id, username, 'x', 1.0, 1 FROM users --"))
    names = [n for n in ("admin", "alice", "bob") if n in probe[2]]
    login_bypass = fetch("/login", data=urllib.parse.urlencode({"username": "admin'--", "password": "x"}).encode())
    return {
        "request_normal": "GET /search?q=lamp",
        "normal_status": normal[0],
        "request_probe": "GET /search?q=zzz%' UNION SELECT id, username, 'x', 1.0, 1 FROM users --",
        "probe_status": probe[0],
        "usernames_returned_in_product_list": names,
        "login_with_quote_and_comment": {"status": login_bypass[0], "location": login_bypass[1].get("Location")},
        "blocked": not names and login_bypass[0] != 302,
    }


def proof_v2(cookies):
    probe = fetch("/search?q=" + urllib.parse.quote("<script>alert(1)</script>"))
    return {"request": "GET /search?q=<script>alert(1)</script>", "status": probe[0],
            "reflected_unescaped": "<script>alert(1)</script>" in probe[2],
            "blocked": "<script>alert(1)</script>" not in probe[2]}


def proof_v3(cookies):
    """Alice (user) requests order ids until she reads one that is not hers."""
    own = fetch("/orders", cookies["alice"])[2]
    own_ids = {int(i) for i in re.findall(r"/orders/(\d+)", own)}
    results = {}
    for order_id in range(1, 5):
        status, _, body = fetch(f"/orders/{order_id}", cookies["alice"])
        results[order_id] = {"status": status, "own": order_id in own_ids}
    foreign = {i: r for i, r in results.items() if not r["own"]}
    return {"request": "GET /orders/<id> as alice, ids 1-4", "alice_own_order_ids": sorted(own_ids),
            "per_id": results, "blocked": all(r["status"] in (403, 404) for r in foreign.values())}


def proof_v4(cookies):
    paths = ["/admin", "/admin/users", "/admin/products"]
    per_role = {role: {p: fetch(p, cookie)[0] for p in paths}
                for role, cookie in (("anonymous", None), ("alice", cookies["alice"]), ("admin", cookies["admin"]))}
    leaked = "alice@secureshop.test" in fetch("/admin/users")[2]
    return {"statuses": per_role, "anonymous_sees_user_list": leaked,
            "blocked": per_role["anonymous"]["/admin/users"] != 200 and per_role["alice"]["/admin/users"] != 200
            and per_role["admin"]["/admin/users"] == 200}


def _login_response(username, password):
    request = urllib.request.Request(
        TARGET + "/login", data=urllib.parse.urlencode({"username": username, "password": password}).encode())
    try:
        return urllib.request.build_opener(_NoRedirect).open(request, timeout=10)
    except urllib.error.HTTPError as err:
        return err


def proof_v5(cookies):
    """Cookie flags, and whether eight wrong passwords lock the account (use a throwaway username)."""
    flags = [h for h in (_login_response("bob", "BobLab#1").headers.get_all("Set-Cookie") or []) if "session=" in h]
    attempts = [_login_response("carol", "wrong").status for _ in range(8)]
    return {"set_cookie_flags": [re.sub(r"session=[^;]+", "session=<value>", h) for h in flags],
            "eight_wrong_passwords_statuses": attempts,
            "blocked": attempts[-1] == 429 and all("HttpOnly" in h and "SameSite" in h for h in flags)}


def proof_v6(cookies):
    status, headers, _ = fetch("/")
    wanted = ["Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"]
    missing = [h for h in wanted if h not in headers]
    err_status, _, err_body = fetch("/search?q=" + urllib.parse.quote("x' OR"))
    return {"missing_security_headers": missing, "error_probe_status": err_status,
            "stack_trace_in_error_page": "Traceback" in err_body, "blocked": not missing and "Traceback" not in err_body}


def proof_v7(cookies):
    status, headers, body = fetch("/static/vendor/jquery-1.12.4.min.js")
    version = re.search(r"jQuery v([\d.]+)", body)
    return {"jquery_status": status, "jquery_version_banner": version.group(1) if version else None,
            "server_header": headers.get("Server"), "blocked": version is None or not version.group(1).startswith("1.")}


PROOFS = {"V1": proof_v1, "V2": proof_v2, "V3": proof_v3, "V4": proof_v4, "V5": proof_v5, "V6": proof_v6, "V7": proof_v7}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", choices=BUILDS, required=True)
    args = parser.parse_args()
    check_target(TARGET)
    build_dir, python = prepare_build(BUILDS[args.build])
    out = REPO / "evidence" / args.build / "manual"
    out.mkdir(parents=True, exist_ok=True)
    app = start_app(build_dir, python, Path(tempfile.mkdtemp(prefix="secureshop-proof-")) / "proof.db")
    try:
        cookies = {role: login(*creds) for role, creds in CREDENTIALS.items()}
        record = {"date": datetime.now().isoformat(timespec="seconds"), "build": args.build,
                  "git_ref": BUILDS[args.build], "proofs": {}}
        for name, proof in PROOFS.items():
            record["proofs"][name] = proof(cookies)
            (out / f"{name}.json").write_text(json.dumps(record["proofs"][name], indent=2), encoding="utf-8")
            print(name, json.dumps(record["proofs"][name])[:300])
        (out / "proofs.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    finally:
        app.kill()


if __name__ == "__main__":
    main()
