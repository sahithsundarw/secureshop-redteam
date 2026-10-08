"""Run a local-only OWASP ZAP baseline scan (spider + passive) and write a report.

Lab rule: the target must be 127.0.0.1 or localhost. Anything else is refused.
"""
import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ALLOWED_HOSTS = {"127.0.0.1", "localhost"}
ZAP_HOST = "127.0.0.1"
ZAP_PORT = 8090
TOOLS = Path(r"C:\Users\sahit\tools")
JAVA = next((TOOLS / "jdk17").glob("jdk-*/bin/java.exe"), None)
ZAP_DIR = next((TOOLS / "zap").glob("ZAP_*"), None)
ZAP_HOME = TOOLS / "zap-home"


def check_target(url):
    """Return the url if it points at the local lab, else raise ValueError."""
    host = urllib.parse.urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing to scan {url!r}: only 127.0.0.1 or localhost is allowed")
    return url


class Zap:
    def __init__(self, key):
        self.key = key
        self.base = f"http://{ZAP_HOST}:{ZAP_PORT}"

    def call(self, path, raw=False, **params):
        query = urllib.parse.urlencode({**params, "apikey": self.key})
        with urllib.request.urlopen(f"{self.base}/{path}?{query}", timeout=60) as resp:
            body = resp.read().decode("utf-8")
        return body if raw else json.loads(body)

    def wait_until_ready(self, seconds=120):
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                return self.call("JSON/core/view/version/")["version"]
            except OSError:
                time.sleep(2)
        raise TimeoutError("ZAP did not start in time")


def start_daemon(key):
    jar = next(ZAP_DIR.glob("zap-*.jar"))
    ZAP_HOME.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(JAVA), "-Xmx1g", "-jar", str(jar), "-daemon",
        "-host", ZAP_HOST, "-port", str(ZAP_PORT), "-dir", str(ZAP_HOME),
        "-config", f"api.key={key}",
        "-config", "start.checkForUpdates=false",
    ]
    return subprocess.Popen(cmd, cwd=ZAP_DIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def spider(zap, target):
    scan_id = zap.call("JSON/spider/action/scan/", url=target, recurse="true")["scan"]
    while int(zap.call("JSON/spider/view/status/", scanId=scan_id)["status"]) < 100:
        time.sleep(1)


def wait_for_passive(zap):
    while int(zap.call("JSON/pscan/view/recordsToScan/")["recordsToScan"]) > 0:
        time.sleep(1)


def summarize(zap, target, version, scan_type):
    alerts = zap.call("JSON/core/view/alerts/", baseurl=target)["alerts"]
    by_risk = {}
    for alert in alerts:
        by_risk[alert["risk"]] = by_risk.get(alert["risk"], 0) + 1
    return {
        "scan_date": datetime.now().isoformat(timespec="seconds"),
        "target_url": target,
        "zap_version": version,
        "scan_type": scan_type,
        "alert_count": len(alerts),
        "alerts_by_severity": by_risk,
        "alerts": [
            {"name": a["alert"], "risk": a["risk"], "url": a["url"], "evidence": a["evidence"]}
            for a in alerts
        ],
    }


def run(target, out_dir):
    check_target(target)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(16)
    proc = start_daemon(key)
    zap = Zap(key)
    try:
        version = zap.wait_until_ready()
        spider(zap, target)
        wait_for_passive(zap)
        (out / "report.html").write_text(
            zap.call("OTHER/core/other/htmlreport/", raw=True), encoding="utf-8")
        summary = summarize(zap, target, version, "baseline (spider + passive)")
        (out / "scan-record.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return summary
    finally:
        try:
            zap.call("JSON/core/action/shutdown/")
        except OSError:
            pass
        proc.wait(timeout=60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="http://127.0.0.1:8080")
    parser.add_argument("--out", default="evidence/baseline")
    args = parser.parse_args()
    try:
        summary = run(args.target, args.out)
    except ValueError as err:
        print(err, file=sys.stderr)
        return 2
    print(f"ZAP {summary['zap_version']} scanned {summary['target_url']}: "
          f"{summary['alert_count']} alerts {summary['alerts_by_severity']}")
    print(f"Report written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
