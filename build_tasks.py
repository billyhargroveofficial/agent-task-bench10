"""Builds the 10 benchmark tasks: a workspace template, an English instruction and
hidden reference data for each. Deterministic (fixed seeds). Run once:
    python3 build_tasks.py
Layout:
    tasks/<id>/workspace/      copied into a fresh directory for every run
    tasks/<id>/instruction.txt prompt given to the agent
    tasks/<id>/hidden/         data only the checker reads
"""
import csv, json, os, random, shutil, subprocess, textwrap, hashlib, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "tasks"
COMMON = ("Work only inside the current directory. Do not ask questions; "
          "when the result is ready, stop.")


def task(tid, instruction):
    d = ROOT / tid
    if d.exists():
        shutil.rmtree(d)
    (d / "workspace").mkdir(parents=True)
    (d / "hidden").mkdir()
    (d / "instruction.txt").write_text(textwrap.dedent(instruction).strip() + "\n\n" + COMMON + "\n")
    return d / "workspace", d / "hidden"


def w(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"))


# ---------------------------------------------------------------- T01 fixed-volume text
ws, hid = task("t01-write-prompt", """
    Write a very detailed English prompt for generating ONE image and save it to `prompt.txt`.
    Subject: one enormous, powerful old lilac bush in an abandoned manor park in central Russia
    at dawn after rain. Cover composition, light, botany, textures, colour, optics, atmosphere,
    surroundings and what to exclude. Length: 1200 to 1500 words. The file must contain only the
    prompt text.
""")

# ---------------------------------------------------------------- T02 media tool action
ws, hid = task("t02-video-sticker", """
    Make a Telegram video sticker from `input.mp4` and save it as `sticker.webm`.
    Requirements: use the LAST 3 seconds of the video; VP9 codec in a WebM container; no audio
    stream; the longer side exactly 512 px with the aspect ratio preserved; duration at most
    3.0 seconds; frame rate at most 30 fps; file size at most 256 KB. `ffmpeg` is installed.
""")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=10",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=10", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(ws / "input.mp4")], check=True)

# ---------------------------------------------------------------- T03 small bug fix
ws, hid = task("t03-fix-intervals", """
    `intervals.py` has a function `merge(intervals)` that does not behave as its docstring says;
    `python3 test_basic.py` shows a failure. Fix `merge` so that it fully matches the docstring.
    Do not change the function name or signature.
""")
w(ws / "intervals.py", '''
    def merge(intervals):
        """Merge closed integer intervals.

        `intervals` is a list of [start, end] pairs with start <= end, in any order.
        Two intervals are merged when they overlap or touch at a point: [1, 2] and [2, 3]
        become [1, 3]. Intervals that are merely adjacent integers are NOT merged:
        [1, 2] and [3, 4] stay separate. The input list must not be modified.
        Returns a new list of [start, end] lists sorted by start.
        """
        result = []
        for start, end in intervals:
            if result and start < result[-1][1]:
                result[-1][1] = end
            else:
                result.append([start, end])
        return result
''')
w(ws / "test_basic.py", '''
    from intervals import merge

    assert merge([[1, 3], [2, 6], [8, 10]]) == [[1, 6], [8, 10]]
    assert merge([[1, 2], [2, 3]]) == [[1, 3]], merge([[1, 2], [2, 3]])
    print("ok")
''')

# ---------------------------------------------------------------- T04 multi-file debugging
ws, hid = task("t04-fix-sales-report", """
    The `salesrep` tool prints wrong totals. `README.md` describes the intended behaviour.
    Run `python3 -m salesrep data/sales.csv` to see the current output. Find and fix every bug
    so the output follows the README exactly. Do not change the output format or the CLI.
""")
w(ws / "README.md", """
    # salesrep

    `python3 -m salesrep FILE.csv` prints a JSON report to stdout.

    Input columns: `date` (YYYY-MM-DD), `region`, `amount`, `currency`.

    Rules:
    - Convert every amount to USD with the rates in `salesrep/fx.py` (amount * rate).
    - A row with an empty `amount` counts as 0. Rows with an unknown currency are skipped.
    - Group by calendar month (`YYYY-MM`) and by region.
    - Sum the unrounded USD amounts, then round each total to 2 decimals.
    - Output: `{"by_month": {"YYYY-MM": total, ...}, "by_region": {"region": total, ...},
      "grand_total": total}` with keys sorted alphabetically.
""")
w(ws / "salesrep/__init__.py", "")
w(ws / "salesrep/__main__.py", """
    import sys

    from .cli import main

    sys.exit(main(sys.argv[1:]))
""")
w(ws / "salesrep/fx.py", """
    RATES = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "RUB": 0.011}


    def to_usd(amount, currency):
        return amount * RATES[currency]
""")
w(ws / "salesrep/loader.py", """
    import csv


    def load(path):
        rows = []
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                amount = row["amount"].strip()
                if not amount:
                    continue
                rows.append({"date": row["date"], "region": row["region"].strip(),
                             "amount": float(amount), "currency": row["currency"].strip()})
        return rows
""")
w(ws / "salesrep/report.py", """
    from .fx import RATES, to_usd


    def build(rows):
        by_month, by_region, grand = {}, {}, 0.0
        for row in rows:
            if row["currency"] not in RATES:
                continue
            usd = round(to_usd(row["amount"], row["currency"]))
            month = row["date"][5:7]
            by_month[month] = by_month.get(month, 0.0) + usd
            by_region[row["region"]] = by_region.get(row["region"], 0.0) + usd
            grand += usd
        return {
            "by_month": {k: round(v, 2) for k, v in sorted(by_month.items())},
            "by_region": {k: round(v, 2) for k, v in sorted(by_region.items())},
            "grand_total": round(grand, 2),
        }
""")
w(ws / "salesrep/cli.py", """
    import json

    from .loader import load
    from .report import build


    def main(argv):
        if len(argv) != 1:
            print("usage: python3 -m salesrep FILE.csv")
            return 2
        print(json.dumps(build(load(argv[0])), indent=2))
        return 0
""")


def sales_rows(seed, n):
    r = random.Random(seed)
    rows = []
    for _ in range(n):
        d = dt.date(2025, 1, 1) + dt.timedelta(days=r.randrange(0, 540))
        cur = r.choice(["USD", "EUR", "GBP", "RUB", "USD", "EUR", "JPY"])
        amt = "" if r.random() < 0.06 else f"{r.uniform(5, 4000):.2f}"
        rows.append([d.isoformat(), r.choice(["north", "south", "east", "west"]), amt, cur])
    return rows


def write_sales(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["date", "region", "amount", "currency"])
        cw.writerows(rows)


write_sales(ws / "data/sales.csv", sales_rows(11, 400))
write_sales(hid / "hidden_sales.csv", sales_rows(12, 900))

# ---------------------------------------------------------------- T05 feature in existing code
ws, hid = task("t05-add-output-format", """
    `wordfreq.py` counts words in a text file and prints a table. Add two options:

    - `--format table|json|csv` (default `table`, which must print exactly what it prints now).
      `json`: a JSON array of objects `{"word": ..., "count": ...}`.
      `csv`: a header line `word,count` followed by one `word,count` line per word.
    - `--top N`: output only the first N entries (default: all).

    In every format entries are ordered by count descending, then by word ascending.
    Usage stays `python3 wordfreq.py FILE [options]`.
""")
w(ws / "wordfreq.py", '''
    import re
    import sys


    def count_words(text):
        counts = {}
        for word in re.findall(r"[a-z']+", text.lower()):
            counts[word] = counts.get(word, 0) + 1
        return counts


    def main(argv):
        if len(argv) != 1:
            print("usage: python3 wordfreq.py FILE")
            return 2
        with open(argv[0]) as f:
            counts = count_words(f.read())
        for word, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{word:<20}{n:>6}")
        return 0


    if __name__ == "__main__":
        sys.exit(main(sys.argv[1:]))
''')
r = random.Random(5)
VOC = ("lilac rain dawn park manor branch leaf stone path fog light shadow bark root moss "
       "don't it's petal cluster wind silence gate fence bench water drop").split()
w(ws / "sample.txt", " ".join(r.choice(VOC) for _ in range(600)) + "\n")
w(hid / "hidden.txt", " ".join(random.Random(6).choice(VOC) for _ in range(1500)) + "\n")

# ---------------------------------------------------------------- T06 precise config edit
ws, hid = task("t06-edit-config", """
    Edit `config.toml`:

    1. Disable every MCP server except `telegram` by setting `enabled = false` in its section.
       Do not delete any server section. `telegram` must end up enabled.
    2. Set `model_reasoning_effort` to "high".
    3. Set `max_concurrent_threads_per_session` to 8.
    4. Delete the commented-out `[model_providers.proxy]` block completely, including its token line.

    Everything else must stay as it is. The file must remain valid TOML.
""")
CONFIG = """
    model = "gpt-6.1-sol"
    model_reasoning_effort = "medium"
    service_tier = "default"
    approval_policy = "never"

    [model_providers]

    # [model_providers.proxy]
    # name = "Proxy"
    # base_url = "http://127.0.0.1:8317/v1"
    # experimental_bearer_token = "FAKE-TOKEN-FOR-BENCHMARK-0000"
    # wire_api = "responses"

    [features]
    memories = false
    apps = true

    [features.multi_agent_v2]
    enabled = true
    max_concurrent_threads_per_session = 16

    [mcp_servers.docs]
    url = "https://example.com/mcp"

    [mcp_servers.telegram]
    url = "http://127.0.0.1:8787/mcp"
    enabled = false

    [mcp_servers.blender]
    command = "/usr/local/bin/blender-mcp"

    [mcp_servers.blender.env]
    BLENDER_MCP_PORT = "9876"

    [mcp_servers.runpod]
    url = "https://mcp.example-pods.io/"
    enabled = true

    [mcp_servers.cinema]
    command = "/usr/local/bin/cinema-mcp"
    startup_timeout_sec = 90.0

    [tui]
    theme = "ansi"
    status_line = ["model", "branch"]
"""
w(ws / "config.toml", CONFIG)
w(hid / "original.toml", CONFIG)

# ---------------------------------------------------------------- T07 analysis of a large input
ws, hid = task("t07-log-report", """
    `access.log` has one request per line:
    `<ISO timestamp> <ip> <METHOD> <path> <status> <latency_ms>`.

    Write `report.json` with exactly these keys:
    - `total_requests`: number of lines.
    - `top_5xx_ips`: the 5 IPs with the most responses whose status is 500-599, as a list of
      `{"ip": ..., "count": ...}` ordered by count descending, ties by ip ascending (string order).
    - `peak_error_hour`: the hour with the most 5xx responses, formatted `YYYY-MM-DD HH`
      (ties: the earliest hour).
    - `p95_latency_orders_ms`: the 95th percentile of latency for requests whose path is exactly
      `/api/orders`, using the nearest-rank method (sort ascending, take the value at position
      ceil(0.95 * n), 1-based), as an integer.
""")
r = random.Random(77)
ips = [f"10.0.{r.randrange(0, 4)}.{r.randrange(1, 250)}" for _ in range(60)]
bad = r.sample(ips, 6)
paths = ["/api/orders", "/api/users", "/api/orders/items", "/health", "/api/search", "/static/app.js"]
t0 = dt.datetime(2026, 9, 14, 0, 0, 0)
lines = []
for i in range(30000):
    ts = t0 + dt.timedelta(seconds=i * 6 + r.randrange(0, 6))
    ip = r.choice(bad) if r.random() < 0.12 else r.choice(ips)
    path = r.choice(paths)
    burst = dt.datetime(2026, 9, 15, 13) <= ts < dt.datetime(2026, 9, 15, 14)
    p5 = 0.35 if burst else (0.09 if ip in bad else 0.015)
    status = r.choice([500, 502, 503, 504]) if r.random() < p5 else r.choice([200, 200, 200, 201, 204, 301, 404])
    lat = int(r.lognormvariate(4.6, 0.7)) + (400 if path == "/api/orders" and r.random() < 0.05 else 0)
    lines.append(f"{ts.isoformat()} {ip} {r.choice(['GET', 'POST'])} {path} {status} {lat}")
(ws / "access.log").write_text("\n".join(lines) + "\n")

# ---------------------------------------------------------------- T08 extraction from a long text
ws, hid = task("t08-transcript-actions", """
    `transcript.txt` is a transcript of a design review call held on Tuesday 2026-10-06.
    Extract every action item that is still valid at the end of the call and write
    `actions.json`: a JSON array of objects `{"owner": <first name>, "task": <short description>,
    "due": "YYYY-MM-DD"}`. Resolve relative deadlines against the call date. Items that were
    cancelled or replaced later in the call must not appear; if an item was reassigned or its
    deadline moved, record the final owner and deadline. The work week is Monday to Friday.
""")
ITEMS = [  # owner, keyword, due, sentence
    ("Marta", "storyboard", "2026-10-09", "Marta: I'll redo the storyboard for the opening and send it by this Friday."),
    ("Oleg", "font", "2026-10-13", "Oleg: Licensing for the new font is on me, I will have it sorted one week from today."),
    ("Dina", "export", "2026-10-07", "Dina: I can re-export the hero shot in 4K by tomorrow."),
    ("Pavel", "color", "2026-10-12", "Pavel: I'll take the color pass on scenes three to five, give me until next Monday."),
    ("Marta", "subtitle", "2026-10-20", "Marta: Subtitles for the English cut, two weeks from today, I'll own that."),
    ("Ilya", "budget", "2026-10-08", "Ilya: I'll send the updated budget table on Thursday this week."),
    ("Dina", "thumbnail", "2026-10-16", "Dina: Thumbnails, three variants, by Friday next week."),
    ("Oleg", "music", "2026-10-14", "Oleg: I'll get the music cue sheet to the client on the fourteenth."),
]
NOISE = [
    "Pavel: The second scene still feels too long to me, the pan drags a bit.",
    "Ilya: Client liked the last cut, mostly comments on pacing and the logo sting.",
    "Marta: We could try a cooler grade, but I'm not convinced yet.",
    "Dina: Render farm was slow yesterday, queue was around forty minutes.",
    "Oleg: I looked at three typefaces, the geometric one reads best at small sizes.",
    "Pavel: Let's not decide on the outro today, we need the voiceover first.",
    "Ilya: Reminder that the office is closed on the fourth of November.",
    "Marta: The reference from the perfume ad is nice but too glossy for us.",
    "Dina: Audio sync drifted by two frames in the last export, I fixed the preset.",
    "Oleg: Can everyone drop their notes into the shared doc instead of chat?",
]
r = random.Random(3)
body = []
slots = sorted(r.sample(range(40, 520), len(ITEMS)))
k = 0
for i in range(560):
    if k < len(slots) and i == slots[k]:
        body.append(ITEMS[k][3]); k += 1
    else:
        body.append(r.choice(NOISE))
# distractors and changes, inserted after the items they refer to
body.insert(slots[2] + 30, "Ilya: Pavel, could you also rebuild the title animation by Wednesday?")
body.insert(slots[2] + 31, "Pavel: Honestly no, scratch that, we agreed the title stays as is. Dropping it.")
body.insert(slots[5] + 40, "Ilya: Actually the budget table moves, I can only send it on Friday this week, not Thursday.")
body.insert(slots[7] + 20, "Oleg: I'm out next week after all. Dina, can you take the music cue sheet, same date?")
body.insert(slots[7] + 21, "Dina: Yes, the cue sheet is mine now, the fourteenth stands.")
body.append("Ilya: Great, that's everything. Thanks all.")
(ws / "transcript.txt").write_text("Design review call, Tuesday 2026-10-06\n\n" + "\n".join(body) + "\n")
FINAL = [
    {"owner": "Marta", "kw": "storyboard", "due": "2026-10-09"},
    {"owner": "Oleg", "kw": "font", "due": "2026-10-13"},
    {"owner": "Dina", "kw": "export", "due": "2026-10-07"},
    {"owner": "Pavel", "kw": "color", "due": "2026-10-12"},
    {"owner": "Marta", "kw": "subtitle", "due": "2026-10-20"},
    {"owner": "Ilya", "kw": "budget", "due": "2026-10-09"},
    {"owner": "Dina", "kw": "thumbnail", "due": "2026-10-16"},
    {"owner": "Dina", "kw": "music", "due": "2026-10-14"},
]
(hid / "expected.json").write_text(json.dumps(FINAL, indent=1))

# ---------------------------------------------------------------- T09 mechanical multi-file change
ws, hid = task("t09-rename-function", """
    In the `geomkit` package rename the function `calc_dist` to `distance` everywhere: its
    definition, all imports and calls, `__all__`, and `README.md`. Keep backward compatibility:
    `geomkit.calc_dist` must still work as an alias defined in `geomkit/__init__.py` that emits
    a `DeprecationWarning` and returns the same result as `distance`. Apart from that alias the
    name `calc_dist` must not appear anywhere in the package or the README.
    `python3 -m unittest -q` must still pass (update the tests to the new name).
""")
w(ws / "README.md", """
    # geomkit

    Small geometry helpers. `calc_dist(a, b)` returns the Euclidean distance between two points.
    Everything else (`perimeter`, `nearest`, `path_length`, `centroid_spread`) builds on `calc_dist`.
""")
w(ws / "geomkit/__init__.py", """
    from .core import calc_dist
    from .shapes import perimeter
    from .search import nearest
    from .paths import path_length
    from .stats import centroid_spread

    __all__ = ["calc_dist", "perimeter", "nearest", "path_length", "centroid_spread"]
""")
w(ws / "geomkit/core.py", '''
    import math


    def calc_dist(a, b):
        """Euclidean distance between points a and b."""
        return math.hypot(a[0] - b[0], a[1] - b[1])
''')
w(ws / "geomkit/shapes.py", """
    from .core import calc_dist


    def perimeter(points):
        return sum(calc_dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points)))
""")
w(ws / "geomkit/search.py", """
    from . import core


    def nearest(target, points):
        return min(points, key=lambda p: core.calc_dist(target, p))
""")
w(ws / "geomkit/paths.py", """
    from .core import calc_dist as _d


    def path_length(points):
        # uses calc_dist pairwise
        return sum(_d(a, b) for a, b in zip(points, points[1:]))
""")
w(ws / "geomkit/stats.py", """
    from .core import calc_dist


    def centroid_spread(points):
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        return max(calc_dist((cx, cy), p) for p in points)
""")
w(ws / "tests/__init__.py", "")
w(ws / "tests/test_geomkit.py", """
    import unittest

    from geomkit import calc_dist, centroid_spread, nearest, path_length, perimeter


    class TestGeomkit(unittest.TestCase):
        def test_calc_dist(self):
            self.assertEqual(calc_dist((0, 0), (3, 4)), 5.0)

        def test_perimeter(self):
            self.assertEqual(perimeter([(0, 0), (3, 0), (3, 4)]), 12.0)

        def test_nearest(self):
            self.assertEqual(nearest((0, 0), [(5, 5), (1, 1), (2, 2)]), (1, 1))

        def test_path_length(self):
            self.assertEqual(path_length([(0, 0), (3, 4), (3, 0)]), 9.0)

        def test_centroid_spread(self):
            self.assertAlmostEqual(centroid_spread([(0, 0), (2, 0)]), 1.0)
""")

# ---------------------------------------------------------------- T10 write a script and run it
ws, hid = task("t10-dedupe-files", """
    The `tree/` directory contains files, some of which are byte-identical duplicates stored under
    different names. Write `dedupe.py` and run it so that:

    - For every group of identical files exactly one stays in `tree/`: the one with the oldest
      modification time (ties: the path that sorts first as a string).
    - Every other copy is moved to `dupes/`, keeping its path relative to `tree/`
      (`tree/a/b.txt` goes to `dupes/a/b.txt`).
    - `manifest.csv` is written with the header `kept,moved,sha256` and one line per moved file:
      the path of the kept file, the original path of the moved file (both relative to the
      current directory, starting with `tree/`), and the SHA-256 of the content. Lines are sorted
      by the `moved` column.

    Files that have no duplicates must not be touched.
""")
r = random.Random(21)
contents = [("unique-%02d\n" % i) * r.randrange(3, 40) for i in range(22)]
dups = [("dup-%02d\n" % i) * r.randrange(5, 60) for i in range(7)]
dirs = ["", "a", "a/b", "c", "c/d/e", "photos", "photos/raw"]
used, plan = set(), []


def fresh(ext):
    while True:
        p = f"{r.choice(dirs)}/{r.choice(['note','img','data','copy','final','draft','scan'])}_{r.randrange(100, 999)}.{ext}".lstrip("/")
        if p not in used:
            used.add(p); return p


for c in contents:
    plan.append((fresh("txt"), c, r.randrange(0, 4000)))
expect = []
for c in dups:
    n = r.randrange(2, 5)
    group = [(fresh("txt"), c, m) for m in r.sample([100, 100, 2500, 3100, 3900], n)]
    plan += group
    keep = sorted(group, key=lambda g: (g[2], "tree/" + g[0]))[0]
    for g in group:
        if g is not keep:
            expect.append({"kept": "tree/" + keep[0], "moved": "tree/" + g[0], "sha256": hashlib.sha256(c.encode()).hexdigest()})
base = dt.datetime(2026, 1, 1).timestamp()
for rel, c, m in plan:
    p = ws / "tree" / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(c)
    os.utime(p, (base + m * 3600, base + m * 3600))
(hid / "expected.json").write_text(json.dumps({"moves": sorted(expect, key=lambda e: e["moved"]),
                                                "all": sorted("tree/" + rel for rel, _, _ in plan),
                                                "mtimes": {"tree/" + rel: base + m * 3600 for rel, _, m in plan}}, indent=1))

print("built", len(list(ROOT.iterdir())), "tasks in", ROOT)
