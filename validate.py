"""Validates the task set: every checker must FAIL on the untouched workspace and
PASS after a reference solution is applied. Reference solutions live only here."""
import csv, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check import check, ROOT  # noqa: E402


def sub(path, old, new, count=1):
    s = path.read_text()
    assert old in s, f"{old!r} not in {path}"
    path.write_text(s.replace(old, new, count))


def s01(wd):
    words = ("one enormous old lilac bush in an abandoned manor park at dawn after rain " * 200).split()[:1300]
    (wd / "prompt.txt").write_text(" ".join(words) + "\n")


def s02(wd):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-3", "-i", "input.mp4", "-an", "-vf", "scale=512:-2,fps=30",
                    "-c:v", "libvpx-vp9", "-b:v", "400k", "-t", "3", "sticker.webm"], cwd=wd, check=True)


def s03(wd):
    (wd / "intervals.py").write_text(textwrap.dedent('''
        def merge(intervals):
            result = []
            for start, end in sorted(intervals):
                if result and start <= result[-1][1]:
                    result[-1][1] = max(result[-1][1], end)
                else:
                    result.append([start, end])
            return result
    '''))


def s04(wd):
    sub(wd / "salesrep/report.py", 'usd = round(to_usd(row["amount"], row["currency"]))', 'usd = to_usd(row["amount"], row["currency"])')
    sub(wd / "salesrep/report.py", 'row["date"][5:7]', 'row["date"][:7]')


def s05(wd):
    (wd / "wordfreq.py").write_text(textwrap.dedent('''
        import argparse, json, re, sys

        def count_words(text):
            counts = {}
            for word in re.findall(r"[a-z']+", text.lower()):
                counts[word] = counts.get(word, 0) + 1
            return counts

        def main(argv):
            ap = argparse.ArgumentParser()
            ap.add_argument("file")
            ap.add_argument("--format", choices=["table", "json", "csv"], default="table")
            ap.add_argument("--top", type=int)
            a = ap.parse_args(argv)
            with open(a.file) as f:
                items = sorted(count_words(f.read()).items(), key=lambda kv: (-kv[1], kv[0]))
            if a.top is not None:
                items = items[:a.top]
            if a.format == "json":
                print(json.dumps([{"word": w, "count": n} for w, n in items]))
            elif a.format == "csv":
                print("word,count")
                for w, n in items:
                    print(f"{w},{n}")
            else:
                for w, n in items:
                    print(f"{w:<20}{n:>6}")
            return 0

        if __name__ == "__main__":
            sys.exit(main(sys.argv[1:]))
    '''))


def s06(wd):
    p = wd / "config.toml"
    s = p.read_text()
    s = re.sub(r"# \[model_providers\.proxy\]\n(# .*\n)+", "", s)
    s = s.replace('model_reasoning_effort = "medium"', 'model_reasoning_effort = "high"')
    s = s.replace("max_concurrent_threads_per_session = 16", "max_concurrent_threads_per_session = 8")
    s = s.replace('url = "http://127.0.0.1:8787/mcp"\nenabled = false', 'url = "http://127.0.0.1:8787/mcp"\nenabled = true')
    s = s.replace('url = "https://mcp.example-pods.io/"\nenabled = true', 'url = "https://mcp.example-pods.io/"\nenabled = false')
    s = s.replace('url = "https://example.com/mcp"\n', 'url = "https://example.com/mcp"\nenabled = false\n')
    s = s.replace('command = "/usr/local/bin/blender-mcp"\n', 'command = "/usr/local/bin/blender-mcp"\nenabled = false\n')
    s = s.replace('command = "/usr/local/bin/cinema-mcp"\n', 'command = "/usr/local/bin/cinema-mcp"\nenabled = false\n')
    p.write_text(s)


def s07(wd):
    n, ipc, hours, lat = 0, {}, {}, []
    for line in open(wd / "access.log"):
        ts, ip, _m, path, status, ms = line.split()
        n += 1
        if status.startswith("5"):
            ipc[ip] = ipc.get(ip, 0) + 1
            h = ts[:10] + " " + ts[11:13]
            hours[h] = hours.get(h, 0) + 1
        if path == "/api/orders":
            lat.append(int(ms))
    lat.sort()
    (wd / "report.json").write_text(json.dumps({
        "total_requests": n,
        "top_5xx_ips": [{"ip": i, "count": c} for i, c in sorted(ipc.items(), key=lambda kv: (-kv[1], kv[0]))[:5]],
        "peak_error_hour": sorted(hours.items(), key=lambda kv: (-kv[1], kv[0]))[0][0],
        "p95_latency_orders_ms": lat[math.ceil(0.95 * len(lat)) - 1]}))


def s08(wd):
    exp = json.loads((ROOT / "t08-transcript-actions/hidden/expected.json").read_text())
    (wd / "actions.json").write_text(json.dumps([{"owner": e["owner"], "task": f"do the {e['kw']} work", "due": e["due"]} for e in exp]))


def s09(wd):
    for f in list((wd / "geomkit").rglob("*.py")) + list((wd / "tests").rglob("*.py")) + [wd / "README.md"]:
        f.write_text(f.read_text().replace("calc_dist", "distance"))
    init = wd / "geomkit/__init__.py"
    init.write_text(init.read_text() + textwrap.dedent('''

        def calc_dist(a, b):
            import warnings
            warnings.warn("calc_dist is deprecated, use distance", DeprecationWarning, stacklevel=2)
            return distance(a, b)
    '''))


def s10(wd):
    (wd / "dedupe.py").write_text("# reference\n")
    groups = {}
    for p in sorted((wd / "tree").rglob("*")):
        if p.is_file():
            groups.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), []).append(p)
    rows = []
    for h, files in groups.items():
        if len(files) < 2:
            continue
        files.sort(key=lambda p: (p.stat().st_mtime, str(p.relative_to(wd))))
        for p in files[1:]:
            dst = wd / "dupes" / p.relative_to(wd / "tree")
            dst.parent.mkdir(parents=True, exist_ok=True)
            rows.append([str(files[0].relative_to(wd)), str(p.relative_to(wd)), h])
            shutil.move(str(p), str(dst))
    with open(wd / "manifest.csv", "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["kept", "moved", "sha256"])
        cw.writerows(sorted(rows, key=lambda r: r[1]))


SOLVE = dict(zip(sorted(p.name for p in ROOT.iterdir()), [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10]))
ok_all = True
for tid, solve in SOLVE.items():
    tmp = Path(tempfile.mkdtemp(prefix="bench10-")) / "w"
    shutil.copytree(ROOT / tid / "workspace", tmp, copy_function=shutil.copy2)
    before = check(tid, tmp)
    solve(tmp)
    after = check(tid, tmp)
    good = (not before["pass"]) and after["pass"]
    ok_all &= good
    print(f"{'OK ' if good else 'BAD'} {tid:26s} pristine: {before['pass']} ({before['detail'][:60]}) | solved: {after['pass']} ({after['detail'][:70]})")
    shutil.rmtree(tmp.parent)
print("ALL VALID" if ok_all else "PROBLEMS FOUND")
