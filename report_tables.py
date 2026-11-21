# -*- coding: utf-8 -*-
"""
COMP3070 CW2 - turn benchmark CSVs from `coursework02.py --bench` into the
tables and chart for the report's Evaluation section.

Not part of the submitted solver; a helper for writing the report.

Usage:
    python report_tables.py results/results.csv
        -> results/report_tables.md (Tables 5.1-5.6) and results/scaling.png
    Options: --out FILE, --chart FILE, --limit SECONDS (time limit used, default 60)
"""

import argparse
import csv
import os
import re
import statistics
import sys
from collections import defaultdict

APPROACH = {"cpsat": "A CP-SAT", "z3-bool": "B Z3 Boolean",
            "z3-int": "C Z3 Integer", "brute": "Brute force"}
ORDER = ["cpsat", "z3-bool", "z3-int", "brute"]


# --------------------------------------------------------------------------
def load(paths):
    rows = []
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    for r in rows:
        r["time"] = float(r["time_ms"]) if r["time_ms"] not in ("", None) else None
        r["utime"] = float(r["unique_ms"]) if r["unique_ms"] not in ("", None) else None
        r["opt"] = r["optimise"] == "1"
    return rows


def methods_in(rows):
    present = {r["method"] for r in rows}
    return [m for m in ORDER if m in present] + sorted(present - set(ORDER))


def natural(text):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", text)]


def fmt_ms(x):
    if x is None:
        return "–"
    if x >= 1000:
        return f"{x / 1000:.1f} s"
    if x >= 10:
        return f"{x:.0f}"
    return f"{x:.1f}" if x >= 1 else f"{x:.2f}"


def table(header, body):
    out = ["| " + " | ".join(header) + " |",
           "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in body]
    return "\n".join(out)


def is_example(r):
    return re.fullmatch(r"example\d+\.txt", os.path.basename(r["file"])) is not None


def folder_label(r):
    return "examples 1–19" if is_example(r) else r["folder"]


def base(rows, keep_skipped=False):
    """Plain runs (no optimisation) with the default At-most-k encoding.
    Brute-force runs skipped as too large are left out unless asked for."""
    return [r for r in rows if not r["opt"] and r["amk"] in ("pattern", "-")
            and (keep_skipped or r["status"] != "skipped")]


# --------------------------------------------------------------------------
def t_examples(rows):
    rows = [r for r in base(rows, keep_skipped=True) if is_example(r)]
    if not rows:
        return None
    ms = methods_in(rows)
    by = {(r["file"], r["method"]): r for r in rows}
    body = []
    for f in sorted({r["file"] for r in rows}, key=natural):
        any_r = next(r for r in rows if r["file"] == f)
        cells = [os.path.basename(f)[:-4], any_r["expected"] or "?"]
        for m in ms:
            r = by.get((f, m))
            if r is None:
                cells.append("–")
            elif r["status"] == "unknown":
                cells.append("timeout")
            elif r["status"] == "skipped":
                cells.append("too large")
            else:
                mark = "✓" if r["correct"] == "1" else "✗"
                flaky = (f" ({r['timeouts']}/{r['runs']} runs timed out)"
                         if r.get("timeouts") not in (None, "", "0") else "")
                cells.append(f"{r['status']} {mark} {fmt_ms(r['time'])}{flaky}")
        body.append(cells)
    return ("Table 5.1: Answer and median time (ms unless marked s) on examples 1–19.",
            table(["File", "Expected"] + [APPROACH.get(m, m) for m in ms], body))


def t_correctness(rows):
    rows = base(rows)
    ms = methods_in(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(folder_label(r), r["method"])].append(r)
    body = []
    for fl in sorted({k[0] for k in groups}, key=natural):
        cells = [fl]
        for m in ms:
            g = groups.get((fl, m), [])
            if not g:
                cells.append("–")
                continue
            decided = [r for r in g if r["status"] in ("sat", "unsat")]
            correct = sum(r["correct"] == "1" for r in decided)
            sat = [r for r in decided if r["status"] == "sat"]
            valid = sum(r["checker_ok"] == "1" for r in sat)
            to = sum(r["status"] == "unknown" for r in g)
            cell = f"{correct}/{len(g)} ({valid}/{len(sat)} valid)"
            cells.append(cell + (f", {to} timeout" if to else ""))
        body.append(cells)
    total = []
    for m in ms:
        g = [r for r in rows if r["method"] == m]
        decided = [r for r in g if r["status"] in ("sat", "unsat")]
        wrong = sum(r["correct"] == "0" for r in decided)
        bad = sum(r["checker_ok"] == "0" for r in decided if r["status"] == "sat")
        total.append(f"{m}: {len(decided)}/{len(g)} decided, {wrong} wrong, {bad} invalid")
    return ("Table 5.2: Answers matching the official answer, and solutions accepted "
            "by the independent checker, per folder.\n\nTotals: " + "; ".join(total),
            table(["Folder"] + [APPROACH.get(m, m) for m in ms], body))


def t_timing(rows):
    rows = base(rows)
    ms = methods_in(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(folder_label(r), r["method"])].append(r)
    body = []
    for fl in sorted({k[0] for k in groups}, key=natural):
        any_r = next(r for r in rows if folder_label(r) == fl)
        size = f"{any_r['steps']} × {any_r['users']}"
        cells = [fl, size]
        for m in ms:
            g = groups.get((fl, m), [])
            t = [r["time"] for r in g if r["status"] in ("sat", "unsat")]
            to = sum(r["status"] == "unknown" for r in g)
            if not g:
                cells.append("–")
            elif not t:
                cells.append(f"all {to} timeout")
            else:
                cell = (f"{fmt_ms(statistics.mean(t))} / {fmt_ms(statistics.median(t))}"
                        f" / {fmt_ms(max(t))}")
                cells.append(cell + (f" (+{to} timeout)" if to else ""))
        body.append(cells)
    return ("Table 5.3: Mean / median / max time (ms unless marked s) of the "
            "instances solved within the limit, per folder. Size = steps × users "
            "of the first file.",
            table(["Folder", "Size"] + [APPROACH.get(m, m) for m in ms], body))


def t_amk(rows):
    plain = [r for r in rows if not r["opt"]]
    pairs = defaultdict(dict)
    for r in plain:
        if r["amk"] in ("pattern", "users"):
            pairs[(r["file"], r["method"])][r["amk"]] = r
    pairs = {k: v for k, v in pairs.items() if len(v) == 2
             and "skipped" not in (v["pattern"]["status"], v["users"]["status"])}
    if not pairs:
        return None
    body = []
    for (f, m), v in sorted(pairs.items(), key=lambda kv: (natural(kv[0][0]), kv[0][1])):
        p, u = v["pattern"], v["users"]
        def cell(r):
            return "timeout" if r["status"] == "unknown" else fmt_ms(r["time"])
        speed = ""
        if p["time"] and u["status"] != "unknown" and p["status"] != "unknown":
            speed = f"{u['time'] / max(p['time'], 1):.1f}×"
        elif u["status"] == "unknown" and p["status"] != "unknown":
            speed = "users timed out"
        body.append([f, APPROACH.get(m, m), p["status"], cell(p), cell(u), speed])
    return ("Table 5.4: At-most-k encodings, pattern (user-independent) vs users "
            "(one helper per user). Speed-up = users time / pattern time.",
            table(["File", "Approach", "Answer", "Pattern", "Users", "Speed-up"], body))


def t_unique(rows):
    rows = [r for r in base(rows) if r["status"] == "sat"]
    if not rows:
        return None
    ms = methods_in(rows)
    groups = defaultdict(list)
    for r in rows:
        groups[(folder_label(r), r["method"])].append(r)
    body = []
    for fl in sorted({k[0] for k in groups}, key=natural):
        for m in ms:
            g = groups.get((fl, m), [])
            if not g:
                continue
            uniq = sum(r["unique"] == "1" for r in g)
            t = statistics.median(r["time"] for r in g)
            ut = [r["utime"] for r in g if r["utime"] is not None]
            body.append([fl, APPROACH.get(m, m), len(g), uniq, len(g) - uniq
                         - sum(r["unique"] == "" for r in g),
                         fmt_ms(t), fmt_ms(statistics.median(ut)) if ut else "–"])
    return ("Table 5.5: Uniqueness check on the satisfiable instances: number with "
            "exactly one solution, and median first-solve time vs median "
            "uniqueness-check time (ms unless marked s).",
            table(["Folder", "Approach", "Sat", "Only solution", "Other solutions exist",
                   "First solve", "Uniqueness check"], body))


def t_optimise(rows):
    plain = {(r["file"], r["method"], r["amk"]): r for r in rows if not r["opt"]}
    pairs = [(plain.get((r["file"], r["method"], r["amk"])), r)
             for r in rows if r["opt"] and r["status"] == "sat"]
    pairs = [(p, o) for p, o in pairs if p is not None and p["status"] == "sat"]
    if not pairs:
        return None
    body = []
    improved = 0
    for p, o in sorted(pairs, key=lambda po: (natural(po[0]["file"]), po[0]["method"])):
        better = int(o["users_used"]) < int(p["users_used"])
        improved += better
        body.append([p["file"], APPROACH.get(p["method"], p["method"]),
                     p["users_used"], o["users_used"] + (" ←" if better else ""),
                     fmt_ms(p["time"]), fmt_ms(o["time"])])
    return (f"Table 5.6: Users in the first solution found (plain) vs the optimised "
            f"solution (E4). Fewer users in {improved} of {len(pairs)} runs (←).",
            table(["File", "Approach", "Users (plain)", "Users (optimised)",
                   "Time plain", "Time optimised"], body))


# --------------------------------------------------------------------------
def chart(rows, path, limit_ms):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: pip install matplotlib (chart skipped)",
              file=sys.stderr)
        return False
    rows = base(rows)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    markers = {"cpsat": "o", "z3-bool": "s", "z3-int": "^", "brute": "x"}
    for m in methods_in(rows):
        g = [r for r in rows if r["method"] == m and r["status"] in ("sat", "unsat", "unknown")]
        xs = [int(r["steps"]) * int(r["users"]) for r in g]
        ys = [max(r["time"] if r["status"] != "unknown" else limit_ms, 0.01) for r in g]
        ax.scatter(xs, ys, label=APPROACH.get(m, m), marker=markers.get(m, "o"),
                   alpha=0.6, s=22)
    ax.axhline(limit_ms, linestyle="--", linewidth=1, color="grey")
    ax.text(0.99, limit_ms * 1.15, f"time limit ({limit_ms / 1000:.0f} s)",
            transform=ax.get_yaxis_transform(), ha="right", va="bottom",
            color="grey", fontsize=8)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Instance size (steps × users, log scale)")
    ax.set_ylabel("Time to first answer (ms, log scale)")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, which="major", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--out", default=None,
                    help="tables file (default: report_tables.md next to the first CSV)")
    ap.add_argument("--chart", default=None,
                    help="chart file (default: scaling.png next to the first CSV)")
    ap.add_argument("--limit", type=float, default=60.0,
                    help="time limit used in the benchmark, seconds (for the chart)")
    args = ap.parse_args(argv)
    rows = load(args.csv)
    here = os.path.dirname(args.csv[0])
    args.out = args.out or os.path.join(here, "report_tables.md")
    args.chart = args.chart or os.path.join(here, "scaling.png")

    parts = []
    meta = args.csv[0] + ".meta.txt"
    if os.path.exists(meta):
        parts.append("Setup (from " + meta + "):\n\n```\n" + open(meta).read() + "```")
    for fn in (t_examples, t_correctness, t_timing, t_amk, t_unique, t_optimise):
        res = fn(rows)
        if res:
            caption, tbl = res
            parts.append(tbl + "\n\n" + caption)
    text = "\n\n".join(parts) + "\n"
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    if chart(rows, args.chart, args.limit * 1000):
        print(f"Chart written to {args.chart}")
    print(f"Tables written to {args.out}")


if __name__ == "__main__":
    main()
