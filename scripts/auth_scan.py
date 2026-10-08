"""Authenticated, local-only ZAP scan of one SecureShop build.

    python scripts/auth_scan.py --build before    # tag v1-vulnerable -> evidence/before/
    python scripts/auth_scan.py --build after     # branch fixed      -> evidence/after/

The script checks the build out into its own git worktree and venv (so the old and the upgraded
dependency pins never mix), seeds a throwaway database, starts the app on 127.0.0.1:8080, logs in
as alice and as admin, then spiders and actively scans as anonymous, alice and admin. Session
cookies are injected through a ZAP replacer rule. Lab rule: only 127.0.0.1 / localhost is scanned.
"""
import argparse
import http.cookiejar
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from scripts.zap_scan import TOOLS, Zap, check_target, start_daemon  # noqa: E402
TARGET = "http://127.0.0.1:8080"
BUILDS = {"before": "v1-vulnerable", "after": "fixed"}
CREDENTIALS = {"alice": ("alice", "AliceLab#1"), "admin": ("admin", "AdminLab#1")}
AUTH_PATHS = ["/cart", "/profile", "/orders", "/orders/1", "/admin", "/admin/products", "/admin/users"]
# State-changing or session-ending endpoints the crawlers must not hit.
EXCLUDE = [r".*/logout.*", r".*/admin/products/\d+/delete.*"]
ACTIVE_MINUTES = 12


def run(cmd, **kwargs):
    subprocess.run([str(c) for c in cmd], check=True, **kwargs)


def prepare_build(ref):
    """Return (build_dir, python) for a git ref, creating the worktree and venv if needed."""
    build_dir = TOOLS / "builds" / ref
    if not build_dir.exists():
        run(["git", "worktree", "add", "--detach", build_dir, ref], cwd=REPO)
    python = build_dir / ".venv" / "Scripts" / "python.exe"
    if not (build_dir / ".venv" / "Lib" / "site-packages" / "flask" / "__init__.py").exists():
        run(["uv", "venv", "--allow-existing", "--python", "3.11", build_dir / ".venv"])
        run(["uv", "pip", "install", "--link-mode=copy", "--python", python,
             "-r", build_dir / "requirements.txt"])
    return build_dir, python


def start_app(build_dir, python, db_path):
    env = {**os.environ, "SECURESHOP_DB": str(db_path)}
    run([python, "-c", "import seed, sys; seed.seed(sys.argv[1])", db_path], cwd=build_dir, env=env)
    proc = subprocess.Popen([python, "app.py"], cwd=build_dir, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(TARGET + "/", timeout=2)
            return proc
        except OSError:
            time.sleep(1)
    proc.kill()
    raise TimeoutError("app did not start")


def login(username, password):
    """Log in directly and return the session cookie value, or None if login failed."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    data = urllib.parse.urlencode({"username": username, "password": password}).encode()
    try:
        opener.open(TARGET + "/login", data, timeout=10)
    except urllib.error.HTTPError:
        return None
    return next((c.value for c in jar if c.name == "session"), None)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def page_status(path, cookie):
    """HTTP status of a page for one role, without following redirects."""
    request = urllib.request.Request(TARGET + path)
    if cookie:
        request.add_header("Cookie", f"session={cookie}")
    try:
        return urllib.request.build_opener(_NoRedirect).open(request, timeout=10).status
    except urllib.error.HTTPError as err:
        return err.code


def set_role(zap, cookie):
    for rule in zap.call("JSON/replacer/view/rules/")["rules"]:
        zap.call("JSON/replacer/action/removeRule/", description=rule["description"])
    if cookie:
        zap.call("JSON/replacer/action/addRule/", description="role-cookie", enabled="true",
                 matchType="REQ_HEADER", matchRegex="false", matchString="Cookie",
                 replacement=f"session={cookie}", initiators="")


def crawl(zap):
    scan_id = zap.call("JSON/spider/action/scan/", url=TARGET, recurse="true")["scan"]
    while int(zap.call("JSON/spider/view/status/", scanId=scan_id)["status"]) < 100:
        time.sleep(1)
    while int(zap.call("JSON/pscan/view/recordsToScan/")["recordsToScan"]) > 0:
        time.sleep(1)
    return zap.call("JSON/spider/view/results/", scanId=scan_id)["results"]


def active_scan(zap):
    scan_id = zap.call("JSON/ascan/action/scan/", url=TARGET, recurse="true")["scan"]
    deadline = time.time() + ACTIVE_MINUTES * 60
    while int(zap.call("JSON/ascan/view/status/", scanId=scan_id)["status"]) < 100:
        if time.time() > deadline:
            zap.call("JSON/ascan/action/stop/", scanId=scan_id)
            return "stopped at time limit"
        time.sleep(3)
    return "completed"


def summarize(zap, version, build, ref, roles, crawled, ascan_state, pages):
    alerts = zap.call("JSON/core/view/alerts/", baseurl=TARGET)["alerts"]
    by_risk = {}
    for alert in alerts:
        by_risk[alert["risk"]] = by_risk.get(alert["risk"], 0) + 1
    return {
        "scan_date": datetime.now().isoformat(timespec="seconds"),
        "build": build,
        "git_ref": ref,
        "target_url": TARGET,
        "zap_version": version,
        "scan_type": "authenticated: spider + passive + active, as anonymous, alice and admin",
        "active_scan_results": ascan_state,
        "roles_scanned": roles,
        "alert_count": len(alerts),
        "alerts_by_severity": by_risk,
        "authenticated_pages_status": pages,
        "urls_found_by_role": crawled,
        "alerts": [
            {"name": a["alert"], "risk": a["risk"], "confidence": a["confidence"], "url": a["url"],
             "param": a["param"], "cweid": a["cweid"], "evidence": a["evidence"]}
            for a in alerts
        ],
    }


def scan(build, out_dir):
    check_target(TARGET)
    ref = BUILDS[build]
    build_dir, python = prepare_build(ref)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    db_path = Path(tempfile.mkdtemp(prefix="secureshop-scan-")) / "scan.db"
    app = start_app(build_dir, python, db_path)
    cookies = {"anonymous": None}
    for role, (user, password) in CREDENTIALS.items():
        cookies[role] = login(user, password)
        if cookies[role] is None:
            raise RuntimeError(f"login failed for {role}; refusing to run an unauthenticated 'authenticated' scan")
    pages = {path: {role: page_status(path, c) for role, c in cookies.items()} for path in AUTH_PATHS}

    key = secrets.token_hex(16)
    daemon = start_daemon(key)
    zap = Zap(key)
    try:
        version = zap.wait_until_ready()
        zap.call("JSON/core/action/newSession/", overwrite="true")
        for pattern in EXCLUDE:
            zap.call("JSON/spider/action/excludeFromScan/", regex=pattern)
            zap.call("JSON/ascan/action/excludeFromScan/", regex=pattern)
        zap.call("JSON/ascan/action/setOptionThreadPerHost/", Integer="8")
        crawled = {}
        for role, cookie in cookies.items():
            set_role(zap, cookie)
            crawled[role] = sorted(crawl(zap))
        ascan_state = {}
        for role in ("alice", "admin"):
            set_role(zap, cookies[role])
            ascan_state[role] = active_scan(zap)
        set_role(zap, None)
        while int(zap.call("JSON/pscan/view/recordsToScan/")["recordsToScan"]) > 0:
            time.sleep(1)
        (out / "report.html").write_text(zap.call("OTHER/core/other/htmlreport/", raw=True), encoding="utf-8")
        (out / "report.json").write_text(zap.call("OTHER/core/other/jsonreport/", raw=True), encoding="utf-8")
        record = summarize(zap, version, build, ref, list(cookies), crawled, ascan_state, pages)
        (out / "scan-record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        return record
    finally:
        try:
            zap.call("JSON/core/action/shutdown/")
        except OSError:
            pass
        daemon.wait(timeout=60)
        app.kill()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--build", choices=BUILDS, required=True)
    parser.add_argument("--out", help="default: evidence/<build>")
    parser.add_argument("--target", default=TARGET, help="must be 127.0.0.1 or localhost")
    args = parser.parse_args()
    try:
        check_target(args.target)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 2
    record = scan(args.build, args.out or REPO / "evidence" / args.build)
    print(f"ZAP {record['zap_version']} scanned {record['git_ref']} at {record['target_url']}: "
          f"{record['alert_count']} alerts {record['alerts_by_severity']}")
    for path, statuses in record["authenticated_pages_status"].items():
        print(f"  {path}: {statuses}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
