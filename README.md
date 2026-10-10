# agent-task-bench10

Ten small, locally checkable tasks for timing coding agents end to end: wall time,
number of model calls, output tokens and whether the task was actually solved.
Built to compare Codex (GPT-6.1 Sol) and Claude Code (Opus 5.5) at the same effort level.

| Task | Type | Checked by |
|---|---|---|
| `t01-write-prompt` | fixed-volume text | word count, language, subject |
| `t02-video-sticker` | media tool action (ffmpeg) | codec, size, duration, no audio, correct segment |
| `t03-fix-intervals` | small bug fix | 10 hidden cases |
| `t04-fix-sales-report` | multi-file debugging | reference result on hidden data |
| `t05-add-output-format` | feature in existing code | three formats, ordering, old behaviour intact |
| `t06-edit-config` | precise TOML edit | every value, removed block, nothing else changed |
| `t07-log-report` | analysis of a 30k-line log | four exact numbers |
| `t08-transcript-actions` | extraction from a long transcript | 8 action items with final owner and date |
| `t09-rename-function` | mechanical multi-file change | tests, no leftovers, deprecated alias |
| `t10-dedupe-files` | write a script and run it | final tree state and manifest |

All tasks are offline and run in a throwaway copy of the task workspace.

## Usage

Python 3.11+ and `ffmpeg` are required.

```sh
python3 build_tasks.py     # regenerate tasks/ (deterministic, fixed seeds)
python3 validate.py        # every checker must fail on the untouched workspace and pass on a reference solution
python3 run_bench.py --agent sol --runs 2
python3 run_bench.py --agent opus --runs 2
python3 check.py t03-fix-intervals /path/to/workdir
```

`run_bench.py` copies each workspace to `~/harness-temp/bench10/<run>`, starts the agent headless
there with the text of `instruction.txt`, saves the timestamped event stream to `results/` and then
runs the checker. Finished runs are skipped, so the command can be repeated. The agents run with
their approval prompts disabled, so use a machine where that is acceptable.

Hidden reference data lives in `tasks/<id>/hidden/` and is read only by `check.py`; reference
solutions exist only inside `validate.py`. Do not point an agent at this repository itself.
