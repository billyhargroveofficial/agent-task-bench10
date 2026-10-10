"""Runs the 10 tasks. Example:
    python3 run_bench.py --agent sol --runs 2
    python3 run_bench.py --agent opus --runs 2 --tasks t03-fix-intervals t07-log-report
Each run gets a fresh copy of the task workspace under ~/harness-temp/bench10/, the agent's
event stream is saved with timestamps to results/, and the checker verdict to results/*.result.json.
Finished runs are skipped, so the command can be repeated after a limit reset."""
import argparse, json, os, shutil, subprocess, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from check import check, ROOT  # noqa: E402

AGENTS = {
    "sol": lambda p: ["codex", "exec", "-p", "fast", "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="medium"',
                      "-c", 'service_tier="default"', "--skip-git-repo-check", "--json", p],
    "opus": lambda p: ["claude", "-p", p, "--model", "claude-opus-5-5", "--effort", "medium", "--permission-mode",
                       "bypassPermissions", "--output-format", "stream-json", "--verbose", "--include-partial-messages"],
}
ap = argparse.ArgumentParser()
ap.add_argument("--agent", choices=list(AGENTS), required=True)
ap.add_argument("--runs", type=int, default=2)
ap.add_argument("--tasks", nargs="*")
ap.add_argument("--timeout", type=int, default=1800)
a = ap.parse_args()
res = HERE / "results"; res.mkdir(exist_ok=True)
work = Path.home() / "harness-temp" / "bench10"
for i in range(1, a.runs + 1):
    for tid in a.tasks or sorted(p.name for p in ROOT.iterdir()):
        tag = f"{a.agent}__{tid}__r{i}"
        if (res / f"{tag}.result.json").exists():
            continue
        wd = work / tag
        if wd.exists():
            shutil.rmtree(wd)
        shutil.copytree(ROOT / tid / "workspace", wd, copy_function=shutil.copy2)
        prompt = (ROOT / tid / "instruction.txt").read_text().strip()
        env = dict(os.environ, RUST_LOG="codex_otel=info")
        t0 = time.time(); status = ["ok"]
        with open(res / f"{tag}.jsonl", "w") as out, open(res / f"{tag}.err", "w") as err:
            p = subprocess.Popen(AGENTS[a.agent](prompt), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err, text=True, cwd=wd, env=env)
            tm = threading.Timer(a.timeout, lambda: (status.__setitem__(0, "timeout"), p.kill())); tm.start()
            for line in p.stdout:
                out.write(f"{time.time() - t0:9.3f}\t{line}"); out.flush()
            p.wait(); tm.cancel()
        wall = time.time() - t0
        verdict = check(tid, wd)
        json.dump(dict(tag=tag, agent=a.agent, task=tid, run=i, start=t0, wall=wall, status=status[0], rc=p.returncode, **verdict),
                  open(res / f"{tag}.result.json", "w"), ensure_ascii=False)
        print(f"{tag:44s} {wall:6.1f}s {'PASS' if verdict['pass'] else 'FAIL'}  {verdict['detail'][:70]}", flush=True)
        time.sleep(5)
