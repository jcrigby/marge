#!/usr/bin/env python3
"""A/B Structural JSON Diff — compares identical API calls to HA and Marge.

Strips volatile fields and reports structural differences (key sets, types,
shapes) rather than value differences. Useful for catching API divergences.

Usage:
    python3 scripts/ab-diff.py [--ha-url URL] [--marge-url URL] [--ha-token TOKEN]
                               [--endpoints FILTER] [--seed] [--verbose]
"""
import argparse, json, os, sys, time, urllib.error, urllib.request
from difflib import unified_diff

VOLATILE_FIELDS = frozenset({
    "last_changed", "last_updated", "last_reported", "context", "time_fired",
    "ha_version", "version", "uuid", "internal_url", "external_url",
    "safe_mode", "state", "recovery_mode", "allowlist_external_dirs",
    "allowlist_external_urls", "config_dir", "config_source", "components",
    "whitelist_external_dirs",
})
IDENTITY_FIELDS = frozenset({"entity_id", "domain"})


def _request(url, method="GET", body=None, token=None):
    """HTTP request -> (status, parsed_json|None, raw_text)."""
    hdrs = {"Content-Type": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        raw = r.read().decode("utf-8", errors="replace")
        return r.status, _try_json(raw), raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, _try_json(raw), raw
    except Exception as e:
        return None, None, str(e)


def _try_json(text):
    try:    return json.loads(text)
    except: return None  # noqa: E722


def api(base, path, method="GET", body=None, token=None):
    return _request(f"{base.rstrip('/')}{path}", method, body, token)


def strip_volatile(obj, depth=0):
    if depth > 30:  return obj
    if isinstance(obj, dict):
        return {k: strip_volatile(v, depth+1) for k, v in obj.items()
                if k not in VOLATILE_FIELDS}
    if isinstance(obj, list):
        return [strip_volatile(i, depth+1) for i in obj]
    return obj


def tname(v):
    for t, n in [(None,"null"),(True,"bool"),(1,"int"),(1.0,"float"),("","string"),
                 ([],"list"),({},"dict")]:
        if v is None and t is None: return "null"
        if t is not None and type(v) is type(t): return n
    return type(v).__name__


def sdiff(ha, mg, path="", out=None):
    """Structural diff — compare types and key sets, not values."""
    if out is None: out = []
    ht, mt = tname(ha), tname(mg)
    pfx = f"  {path}" if path else "  $"
    if ht != mt:
        out.append(f"{pfx}: HA type={ht}, Marge type={mt}"); return out
    if isinstance(ha, dict) and isinstance(mg, dict):
        hk, mk = set(ha), set(mg)
        miss, extra = sorted(hk - mk), sorted(mk - hk)
        if miss: out.append(f"{pfx}: Missing in Marge: {', '.join(miss)}")
        if extra: out.append(f"{pfx}: Extra in Marge: {', '.join(extra)}")
        for k in sorted(hk & mk): sdiff(ha[k], mg[k], f"{path}.{k}", out)
        return out
    if isinstance(ha, list) and isinstance(mg, list):
        if ha and mg:      sdiff(ha[0], mg[0], f"{path}[0]", out)
        elif ha:           out.append(f"{pfx}: HA has {len(ha)} items, Marge empty")
        elif mg:           out.append(f"{pfx}: HA empty, Marge has {len(mg)} items")
        return out
    if path:
        field = path.rsplit(".", 1)[-1] if "." in path else path
        if field in IDENTITY_FIELDS and ha != mg:
            out.append(f"{pfx}: value mismatch: HA={ha!r}, Marge={mg!r}")
    return out


def endpoints(groups):
    """Build endpoint catalog: (method, path, body, label, group)."""
    c = []
    if "core" in groups:
        c += [("GET","/api/",None,"API status","core"),
              ("GET","/api/config",None,"Configuration","core")]
    if "states" in groups:
        c += [("GET","/api/states",None,"All states","states"),
              ("POST","/api/states/sensor.ab_test_1",
               {"state":"42","attributes":{"unit":"C"}},"Create entity","states"),
              ("GET","/api/states/sensor.ab_test_1",None,"Get entity back","states")]
    if "services" in groups:
        c += [("GET","/api/services",None,"Service listing","services"),
              ("POST","/api/services/light/turn_on",
               {"entity_id":"light.ab_test_svc"},"Call service (known divergence)","services")]
    if "templates" in groups:
        c += [("POST","/api/template",
               {"template":"{{ states('sensor.ab_test_1') }}"},"Template render","templates")]
    if "events" in groups:
        c += [("POST","/api/events/test_ab_event",{"key":"value"},"Fire event","events")]
    return c


def resolve_groups(s):
    ALL = {"core","states","services","templates","events"}
    if s == "all": return ALL
    req = {g.strip() for g in s.split(",")}
    bad = req - ALL
    if bad: print(f"Warning: unknown groups: {', '.join(sorted(bad))}")
    return req & ALL


def seed(ha_url, mg_url, ha_tok, mg_tok):
    """Create test entities on both SUTs."""
    ents = [("/api/states/sensor.ab_test_1",
             {"state":"42","attributes":{"unit":"C","friendly_name":"AB Test Sensor"}}),
            ("/api/states/light.ab_test_svc",
             {"state":"off","attributes":{"friendly_name":"AB Test Light"}})]
    print("Seeding test entities...")
    for path, body in ents:
        s1,_,_ = api(ha_url, path, "POST", body, ha_tok)
        s2,_,_ = api(mg_url, path, "POST", body, mg_tok)
        eid = path.rsplit("/",1)[-1]
        f = lambda s: "ok" if s and 200<=s<300 else f"ERR({s})"
        print(f"  {eid}: HA={f(s1)} Marge={f(s2)}")
    time.sleep(0.5); print()


def run(ha_url, mg_url, ha_tok, mg_tok, groups, verbose):
    """Run all endpoints, compare, print report. Returns diff count."""
    eps = endpoints(groups)
    if not eps: print("No endpoints to test."); return 0
    results = []
    print("=== A/B Structural Diff: HA vs Marge ===\n")
    for method, path, body, label, grp in eps:
        mp = f"{method} {path}"
        print(f"--- {mp} ---\n  ({label})")
        hs, hj, hr = api(ha_url, path, method, body, ha_tok)
        ms, mj, mr = api(mg_url, path, method, body, mg_tok)
        sm = (hs == ms)
        print(f"  Status: HA={hs} Marge={ms} {'+'  if sm else 'MISMATCH'}")
        if hs is None:
            print(f"  HA connection failed: {hr}\n")
            results.append((sm, False)); continue
        if ms is None:
            print(f"  Marge connection failed: {mr}\n")
            results.append((sm, False)); continue
        if hj is None and mj is None:
            print("  Structure: MATCH (both non-JSON)\n")
            results.append((sm, True)); continue
        if hj is None or mj is None:
            print(f"  Structure: DIFF (HA={'JSON' if hj else 'non-JSON'}, "
                  f"Marge={'JSON' if mj else 'non-JSON'})\n")
            results.append((sm, False)); continue
        hc, mc = strip_volatile(hj), strip_volatile(mj)
        ht, mt = tname(hc), tname(mc)
        if ht != mt:
            d1 = f"HA returns: {ht}"
            d2 = f"Marge returns: {mt}"
            if mt == "dict" and isinstance(mc, dict):
                d2 += f" (keys: {', '.join(sorted(mc))})"
            if ht == "dict" and isinstance(hc, dict):
                d1 += f" (keys: {', '.join(sorted(hc))})"
            print(f"  Structure: DIFF\n    {d1}\n    {d2}")
            results.append((sm, False))
        else:
            diffs = sdiff(hc, mc)
            if diffs:
                print("  Structure: DIFF")
                for d in diffs: print(f"  {d}")
                results.append((sm, False))
            else:
                print("  Structure: MATCH")
                results.append((sm, True))
        if verbose and hc != mc:
            hl = json.dumps(hc, indent=2, sort_keys=True, default=str).splitlines(True)
            ml = json.dumps(mc, indent=2, sort_keys=True, default=str).splitlines(True)
            dl = list(unified_diff(hl, ml, fromfile="HA", tofile="Marge", n=3))
            if dl:
                print("  --- verbose diff ---")
                for ln in dl[:60]: print(f"    {ln.rstrip()}")
                if len(dl) > 60: print(f"    ... ({len(dl)-60} more lines)")
        print()
    total = len(results)
    sok = sum(r[0] for r in results)
    stok = sum(r[1] for r in results)
    print(f"=== Summary ===\nEndpoints tested: {total}\n"
          f"  Status match: {sok}/{total}\n  Structure match: {stok}/{total}\n"
          f"  Structural diffs: {total - stok}")
    return total - stok


def load_token(arg):
    if arg: return arg
    t = os.environ.get("HA_TOKEN")
    if t: return t
    p = os.path.join(os.getcwd(), "ha-config", ".ha_token")
    if os.path.isfile(p):
        with open(p) as f: return f.read().strip()
    return None


def main():
    p = argparse.ArgumentParser(
        description="A/B structural JSON diff: HA vs Marge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Groups: core, states, services, templates, events, all\n\n"
               "Examples:\n  python3 scripts/ab-diff.py --seed\n"
               "  python3 scripts/ab-diff.py --endpoints states,services --verbose")
    p.add_argument("--ha-url", default="http://localhost:8123",
                   help="HA URL (default: http://localhost:8123)")
    p.add_argument("--marge-url", default="http://localhost:8124",
                   help="Marge URL (default: http://localhost:8124)")
    p.add_argument("--ha-token", default=None,
                   help="HA token (reads ./ha-config/.ha_token if omitted)")
    p.add_argument("--endpoints", default="all",
                   help="Comma-separated: core,states,services,templates,events,all")
    p.add_argument("--seed", action="store_true",
                   help="Seed identical test entities on both SUTs first")
    p.add_argument("--verbose", action="store_true",
                   help="Show full JSON diffs (unified diff)")
    a = p.parse_args()
    ha_tok = load_token(a.ha_token)
    groups = resolve_groups(a.endpoints)
    print(f"HA:    {a.ha_url}\nMarge: {a.marge_url}")
    print(f"Token: {'set' if ha_tok else 'NOT SET (HA calls may fail)'}")
    print(f"Groups: {', '.join(sorted(groups))}\n")
    if a.seed:
        seed(a.ha_url, a.marge_url, ha_tok, None)
    dc = run(a.ha_url, a.marge_url, ha_tok, None, groups, a.verbose)
    sys.exit(0 if dc == 0 else 1)


if __name__ == "__main__":
    main()
