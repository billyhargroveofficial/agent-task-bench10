"""Checkers for the 10 tasks. Usage:
    python3 check.py <task-id> <workdir>      -> prints JSON {"pass": bool, "detail": str}
Each checker reads only the agent's workdir and tasks/<id>/hidden.
"""
import csv, hashlib, io, json, math, os, re, subprocess, sys, tomllib, warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "tasks"


def run(cmd, cwd, timeout=60):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def t01(wd, hid):
    p = wd / "prompt.txt"
    if not p.exists():
        return False, "prompt.txt missing"
    text = p.read_text()
    n = len(re.findall(r"\S+", text))
    if not 1200 <= n <= 1500:
        return False, f"{n} words, need 1200-1500"
    if "lilac" not in text.lower():
        return False, "subject missing"
    if re.search(r"[а-яА-Я]", text):
        return False, "not English"
    return True, f"{n} words"


def t02(wd, hid):
    p = wd / "sticker.webm"
    if not p.exists():
        return False, "sticker.webm missing"
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(p)], wd)
    info = json.loads(r.stdout or "{}")
    streams = info.get("streams", [])
    v = [s for s in streams if s.get("codec_type") == "video"]
    if len(v) != 1 or len(streams) != 1:
        return False, f"streams: {[s.get('codec_type') for s in streams]}"
    v = v[0]
    dur = float(info["format"].get("duration", 0))
    num, den = map(int, v["avg_frame_rate"].split("/"))
    fps = num / den if den else 0
    size = p.stat().st_size
    checks = {
        "vp9": v.get("codec_name") == "vp9",
        "webm": "webm" in info["format"].get("format_name", ""),
        "512 long side": max(v["width"], v["height"]) == 512,
        "aspect": abs(v["width"] / v["height"] - 16 / 9) < 0.02,
        "duration<=3.0": 2.5 <= dur <= 3.05,
        "fps<=30": 0 < fps <= 30.01,
        "size<=256KB": size <= 256 * 1024,
    }
    # last three seconds: testsrc2 burns a running timestamp; compare first frame to source at t=7s
    def frame_sig(src, ss):
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(ss), "-i", str(src), "-frames:v", "1", "-vf",
                            "scale=64:36,format=gray", "-f", "rawvideo", "-"], capture_output=True, timeout=60)
        return r.stdout
    a, b7, b0 = frame_sig(p, 0), frame_sig(wd / "input.mp4", 7), frame_sig(wd / "input.mp4", 0)
    if a and b7 and b0:
        d7 = sum(abs(x - y) for x, y in zip(a, b7)) / len(a)
        d0 = sum(abs(x - y) for x, y in zip(a, b0)) / len(a)
        checks["last 3 seconds"] = d7 < d0
    bad = [k for k, ok in checks.items() if not ok]
    return (not bad), ("ok" if not bad else "failed: " + ", ".join(bad)) + f" ({v['width']}x{v['height']}, {dur:.2f}s, {fps:.1f}fps, {size // 1024}KB)"


def t03(wd, hid):
    code = """
import json, copy
from intervals import merge
cases = [
 ([[1,3],[2,6],[8,10]], [[1,6],[8,10]]),
 ([[1,2],[2,3]], [[1,3]]),
 ([[1,2],[3,4]], [[1,2],[3,4]]),
 ([[5,7],[1,2],[2,4]], [[1,4],[5,7]]),
 ([[1,10],[2,3],[4,5]], [[1,10]]),
 ([[1,10],[2,3],[11,12]], [[1,10],[11,12]]),
 ([], []),
 ([[4,4],[4,4],[1,1]], [[1,1],[4,4]]),
 ([[3,5],[1,4],[0,0],[6,9],[5,6]], [[0,0],[1,9]]),
 ([[-5,-1],[-1,0],[2,2]], [[-5,0],[2,2]]),
]
bad = []
for inp, exp in cases:
    orig = copy.deepcopy(inp)
    out = merge(inp)
    if [list(x) for x in out] != exp: bad.append([orig, [list(x) for x in out]])
    elif inp != orig: bad.append([orig, 'input modified'])
print(json.dumps(bad))
"""
    r = run([sys.executable, "-c", code], wd)
    if r.returncode != 0:
        return False, r.stderr.strip()[-200:]
    bad = json.loads(r.stdout.strip().splitlines()[-1])
    return (not bad), "10/10" if not bad else f"{len(bad)} of 10 failed, e.g. {bad[0]}"


def t04(wd, hid):
    rates = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "RUB": 0.011}
    bm, br, g = {}, {}, 0.0
    for row in csv.DictReader(open(hid / "hidden_sales.csv", newline="")):
        if row["currency"] not in rates:
            continue
        usd = (float(row["amount"]) if row["amount"].strip() else 0.0) * rates[row["currency"]]
        bm[row["date"][:7]] = bm.get(row["date"][:7], 0.0) + usd
        br[row["region"]] = br.get(row["region"], 0.0) + usd
        g += usd
    exp = {"by_month": {k: round(v, 2) for k, v in sorted(bm.items())},
           "by_region": {k: round(v, 2) for k, v in sorted(br.items())}, "grand_total": round(g, 2)}
    r = run([sys.executable, "-m", "salesrep", str(hid / "hidden_sales.csv")], wd)
    try:
        out = json.loads(r.stdout)
    except Exception:
        return False, "output is not JSON: " + (r.stderr or r.stdout)[-160:]
    if list(out) != ["by_month", "by_region", "grand_total"]:
        return False, f"keys {list(out)}"
    for sec in ("by_month", "by_region"):
        if list(out[sec]) != list(exp[sec]):
            return False, f"{sec} keys differ: {list(out[sec])[:4]}..."
        for k in exp[sec]:
            if abs(out[sec][k] - exp[sec][k]) > 0.011:
                return False, f"{sec}[{k}] = {out[sec][k]}, expected {exp[sec][k]}"
    if abs(out["grand_total"] - exp["grand_total"]) > 0.011:
        return False, f"grand_total {out['grand_total']} != {exp['grand_total']}"
    return True, "matches reference"


def t05(wd, hid):
    text = (hid / "hidden.txt").read_text()
    counts = {}
    for wd_ in re.findall(r"[a-z']+", text.lower()):
        counts[wd_] = counts.get(wd_, 0) + 1
    order = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    f = str(hid / "hidden.txt")
    table = "".join(f"{w_:<20}{n:>6}\n" for w_, n in order)
    r = run([sys.executable, "wordfreq.py", f], wd)
    if r.stdout != table:
        return False, "default output changed"
    r = run([sys.executable, "wordfreq.py", f, "--format", "table", "--top", "3"], wd)
    if r.stdout != "".join(f"{w_:<20}{n:>6}\n" for w_, n in order[:3]):
        return False, "--format table --top 3 wrong"
    r = run([sys.executable, "wordfreq.py", f, "--format", "json"], wd)
    try:
        j = json.loads(r.stdout)
    except Exception:
        return False, "json output invalid"
    if j != [{"word": w_, "count": n} for w_, n in order]:
        return False, "json content or order wrong"
    r = run([sys.executable, "wordfreq.py", f, "--top", "5", "--format", "json"], wd)
    try:
        if json.loads(r.stdout) != [{"word": w_, "count": n} for w_, n in order[:5]]:
            return False, "json --top 5 wrong"
    except Exception:
        return False, "json --top output invalid"
    r = run([sys.executable, "wordfreq.py", f, "--format", "csv", "--top", "4"], wd)
    rows = [l.strip() for l in r.stdout.strip().splitlines()]
    if rows != ["word,count"] + [f"{w_},{n}" for w_, n in order[:4]]:
        return False, f"csv wrong: {rows[:3]}"
    return True, "all formats ok"


def t06(wd, hid):
    raw = (wd / "config.toml").read_text()
    try:
        new = tomllib.loads(raw)
    except Exception as e:
        return False, f"invalid TOML: {e}"
    old = tomllib.loads((hid / "original.toml").read_text())
    if "experimental_bearer_token" in raw or "model_providers.proxy" in raw or "FAKE-TOKEN" in raw:
        return False, "proxy block not removed"
    exp = json.loads(json.dumps(old))
    exp["model_reasoning_effort"] = "high"
    exp["features"]["multi_agent_v2"]["max_concurrent_threads_per_session"] = 8
    for name, s in exp["mcp_servers"].items():
        s["enabled"] = (name == "telegram")
    got = json.loads(json.dumps(new))
    # telegram may be enabled either by enabled=true or by removing the key
    got.get("mcp_servers", {}).get("telegram", {}).setdefault("enabled", True)
    if got != exp:
        diffs = []
        def walk(a, b, path=""):
            if isinstance(a, dict) and isinstance(b, dict):
                for k in sorted(set(a) | set(b)):
                    walk(a.get(k, "<missing>"), b.get(k, "<missing>"), f"{path}.{k}")
            elif a != b:
                diffs.append(f"{path[1:]}: got {a!r}, want {b!r}")
        walk(got, exp)
        return False, "; ".join(diffs[:3])
    return True, "config matches"


def t07(wd, hid):
    p = wd / "report.json"
    if not p.exists():
        return False, "report.json missing"
    try:
        rep = json.loads(p.read_text())
    except Exception:
        return False, "report.json invalid"
    n, ipc, hours, lat = 0, {}, {}, []
    for line in open(wd / "access.log"):
        ts, ip, _m, path, status, ms = line.split()
        n += 1
        if 500 <= int(status) <= 599:
            ipc[ip] = ipc.get(ip, 0) + 1
            h = ts[:10] + " " + ts[11:13]
            hours[h] = hours.get(h, 0) + 1
        if path == "/api/orders":
            lat.append(int(ms))
    lat.sort()
    exp = {
        "total_requests": n,
        "top_5xx_ips": [{"ip": ip, "count": c} for ip, c in sorted(ipc.items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
        "peak_error_hour": sorted(hours.items(), key=lambda kv: (-kv[1], kv[0]))[0][0],
        "p95_latency_orders_ms": lat[math.ceil(0.95 * len(lat)) - 1],
    }
    bad = [k for k in exp if rep.get(k) != exp[k]]
    if set(rep) != set(exp):
        bad.append(f"keys {sorted(rep)}")
    return (not bad), "all four values correct" if not bad else "wrong: " + ", ".join(map(str, bad))


def t08(wd, hid):
    p = wd / "actions.json"
    if not p.exists():
        return False, "actions.json missing"
    try:
        acts = json.loads(p.read_text())
        assert isinstance(acts, list)
    except Exception:
        return False, "actions.json invalid"
    exp = json.loads((hid / "expected.json").read_text())
    used, missing = set(), []
    for e in exp:
        hit = None
        for i, a in enumerate(acts):
            if i in used or not isinstance(a, dict):
                continue
            if str(a.get("owner", "")).strip().lower() == e["owner"].lower() and a.get("due") == e["due"] \
                    and e["kw"] in str(a.get("task", "")).lower().replace("colour", "color"):
                hit = i
                break
        if hit is None:
            missing.append(f"{e['owner']}/{e['kw']}/{e['due']}")
        else:
            used.add(hit)
    extra = len(acts) - len(used)
    ok = not missing and extra == 0
    return ok, f"{len(used)}/8 found, {extra} extra" + (f"; missing {missing[:3]}" if missing else "")


def t09(wd, hid):
    r = run([sys.executable, "-m", "unittest", "-q"], wd)
    if r.returncode != 0:
        return False, "unittest fails: " + r.stderr.strip()[-160:]
    code = """
import warnings, json
import geomkit
from geomkit import distance, perimeter, nearest, path_length, centroid_spread
from geomkit.core import distance as d2
res = {'dist': distance((0,0),(3,4)) == 5.0, 'all': 'distance' in geomkit.__all__ and 'calc_dist' not in geomkit.__all__,
       'funcs': perimeter([(0,0),(3,0),(3,4)]) == 12.0 and nearest((0,0),[(5,5),(1,1)]) == (1,1) and path_length([(0,0),(3,4)]) == 5.0}
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter('always')
    v = geomkit.calc_dist((0,0),(3,4))
    res['alias'] = v == 5.0 and any(issubclass(x.category, DeprecationWarning) for x in w)
print(json.dumps(res))
"""
    r = run([sys.executable, "-c", code], wd)
    if r.returncode != 0:
        return False, r.stderr.strip()[-200:]
    res = json.loads(r.stdout.strip().splitlines()[-1])
    bad = [k for k, v in res.items() if not v]
    left = []
    for f in list((wd / "geomkit").rglob("*.py")) + [wd / "README.md"]:
        if f.name == "__init__.py" and f.parent.name == "geomkit":
            continue
        if "calc_dist" in f.read_text():
            left.append(str(f.relative_to(wd)))
    if left:
        bad.append("old name left in " + ", ".join(left))
    if "distance" not in (wd / "README.md").read_text():
        bad.append("README not updated")
    return (not bad), "ok" if not bad else "failed: " + ", ".join(bad)


def t10(wd, hid):
    exp = json.loads((hid / "expected.json").read_text())
    moved = {e["moved"] for e in exp["moves"]}
    bad = []
    for path in exp["all"]:
        in_tree = (wd / path).exists()
        in_dupes = (wd / ("dupes/" + path[len("tree/"):])).exists()
        if path in moved and (in_tree or not in_dupes):
            bad.append(f"{path} should be in dupes/")
        if path not in moved and not in_tree:
            bad.append(f"{path} should stay")
        if path not in moved and in_tree and abs((wd / path).stat().st_mtime - exp["mtimes"][path]) > 1:
            bad.append(f"{path} was modified")
    extra = [str(p.relative_to(wd)) for p in (wd / "dupes").rglob("*") if p.is_file()] if (wd / "dupes").exists() else []
    if len(extra) != len(moved):
        bad.append(f"dupes/ has {len(extra)} files, expected {len(moved)}")
    m = wd / "manifest.csv"
    if not m.exists():
        bad.append("manifest.csv missing")
    else:
        rows = list(csv.reader(io.StringIO(m.read_text().strip())))
        want = [["kept", "moved", "sha256"]] + [[e["kept"], e["moved"], e["sha256"]] for e in exp["moves"]]
        if [[c.strip() for c in r] for r in rows] != want:
            bad.append("manifest.csv content differs")
    if not (wd / "dedupe.py").exists():
        bad.append("dedupe.py missing")
    return (not bad), "ok" if not bad else "; ".join(bad[:3])


CHECKS = {"t01-write-prompt": t01, "t02-video-sticker": t02, "t03-fix-intervals": t03, "t04-fix-sales-report": t04,
          "t05-add-output-format": t05, "t06-edit-config": t06, "t07-log-report": t07, "t08-transcript-actions": t08,
          "t09-rename-function": t09, "t10-dedupe-files": t10}


def check(tid, workdir):
    try:
        ok, detail = CHECKS[tid](Path(workdir), ROOT / tid / "hidden")
    except Exception as e:  # a crash in the agent's output is a failed task, not a crashed checker
        ok, detail = False, f"checker error: {type(e).__name__}: {e}"
    return {"task": tid, "pass": bool(ok), "detail": detail}


if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1], sys.argv[2]), ensure_ascii=False))
