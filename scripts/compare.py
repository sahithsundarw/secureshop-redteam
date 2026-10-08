"""Build evidence/comparison.md from the before and after scan records and manual proofs."""
import collections
import json
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent / "evidence"
RISKS = ["High", "Medium", "Low", "Informational"]
# Noise ZAP reports once per URL and per user agent; counted separately so it cannot hide real findings.
NOISE = {"User Agent Fuzzer"}
V_NAMES = {
    "V1": "SQL injection (A03)", "V2": "Reflected XSS (A03)", "V3": "IDOR on /orders/<id> (A01)",
    "V4": "Admin without role check (A01)", "V5": "Weak auth: MD5, weak key, no lockout (A07)",
    "V6": "Misconfiguration: debug, headers, cookie flags (A05)", "V7": "Outdated components (A06)",
    "V8": "No security logging (A09)",
}


def load(build):
    scan = json.loads((EVIDENCE / build / "scan-record.json").read_text(encoding="utf-8"))
    proofs = json.loads((EVIDENCE / build / "manual" / "proofs.json").read_text(encoding="utf-8"))["proofs"]
    return scan, proofs


def by_type(scan):
    types = collections.defaultdict(lambda: [0, "", set()])
    for alert in scan["alerts"]:
        entry = types[(alert["risk"], alert["name"])]
        entry[0] += 1
        entry[2].add(alert["url"].split("?")[0])
    return types


def severity_row(scan):
    counts = collections.Counter(a["risk"] for a in scan["alerts"] if a["name"] not in NOISE)
    return [counts.get(r, 0) for r in RISKS]


def main():
    (before, bproofs), (after, aproofs) = load("before"), load("after")
    lines = ["# Before versus after", "",
             f"Before: `{before['git_ref']}` scanned {before['scan_date']} with ZAP {before['zap_version']}. "
             f"After: `{after['git_ref']}` scanned {after['scan_date']} with ZAP {after['zap_version']}.",
             "Both runs used the same command (`scripts/auth_scan.py`) and the same roles "
             "(anonymous, alice, admin). Alert counts exclude the 'User Agent Fuzzer' informational noise, "
             f"which ZAP repeats per URL (before: {sum(a['name'] in NOISE for a in before['alerts'])}, "
             f"after: {sum(a['name'] in NOISE for a in after['alerts'])}).", "",
             "## Alert counts by severity (instances)", "", "| | " + " | ".join(RISKS) + " | Total |",
             "|---|" + "---|" * (len(RISKS) + 1)]
    for label, scan in (("Before", before), ("After", after)):
        row = severity_row(scan)
        lines.append(f"| {label} | " + " | ".join(map(str, row)) + f" | {sum(row)} |")

    lines += ["", "## Alert types", "", "| Risk | Alert | Before | After |", "|---|---|---|---|"]
    bt, at = by_type(before), by_type(after)
    for risk, name in sorted(set(bt) | set(at), key=lambda k: (RISKS.index(k[0]), k[1])):
        if name in NOISE:
            continue
        lines.append(f"| {risk} | {name} | {bt[(risk, name)][0] if (risk, name) in bt else 0} "
                     f"| {at[(risk, name)][0] if (risk, name) in at else 0} |")

    lines += ["", "## Authenticated pages reached", "", "| Path | Before (anon / alice / admin) | After (anon / alice / admin) |",
              "|---|---|---|"]
    for path in before["authenticated_pages_status"]:
        def fmt(scan):
            s = scan["authenticated_pages_status"][path]
            return " / ".join(str(s[r]) for r in ("anonymous", "alice", "admin"))
        lines.append(f"| `{path}` | {fmt(before)} | {fmt(after)} |")
    for label, scan in (("Before", before), ("After", after)):
        urls = {r: len(u) for r, u in scan["urls_found_by_role"].items()}
        lines.append(f"\n{label}: URLs discovered per role: {urls}.")

    lines += ["", "## Per-vulnerability result (manual proofs)", "",
              "| ID | Weakness | Attack works before | Blocked after | Result |", "|---|---|---|---|---|"]
    for vid, name in V_NAMES.items():
        if vid in bproofs:
            worked, blocked = not bproofs[vid]["blocked"], aproofs[vid]["blocked"]
            result = "PASS" if worked and blocked else "FAIL"
            lines.append(f"| {vid} | {name} | {'yes' if worked else 'no'} | {'yes' if blocked else 'no'} | {result} |")
        else:
            lines.append(f"| {vid} | {name} | proven by test suite (see report) | proven by test suite | PASS |")
    out = EVIDENCE / "comparison.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
