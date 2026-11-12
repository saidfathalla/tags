#!/usr/bin/env python3
"""
Benchmark harness for TAGS (reproduces the scalability results of the paper).

Each measurement runs TAGS in a fresh process (multiprocessing 'spawn'), so runs
do not share memory. For every run we record
  * wall-clock time of analyze_knowledge_graph(), and
  * peak RSS delta: peak resident set size observed while TAGS runs, minus the
    RSS measured in the same process immediately before ingestion starts
    (sampled every 5 ms with psutil).
Each configuration is repeated --runs times (default 5) and reported as mean,
sample standard deviation (SD) and 95% confidence interval of the mean
(Student t, n-1 degrees of freedom).

Usage
-----
  # Synthetic scalability benchmark (Tables 5 and 6, scalability figure)
  python benchmarks/benchmark.py synthetic --sizes 1000 10000 100000 1000000 --runs 5

  # Any RDF file (e.g., the DBpedia Berlin sample or the ORKG dump)
  python benchmarks/benchmark.py file examples/DBpedia-mini-samples-Berlin.ttl --runs 5
  python benchmarks/benchmark.py file data/rdf-export-orkg.nt -f nt --runs 5

Results are written as CSV files to --out (default: results/).
"""

import argparse
import csv
import math
import multiprocessing as mp
import os
import platform
import random
import statistics
import sys
import threading
import time

import psutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

# Two-sided 95% critical values of Student's t for df = 1..30
T_975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
         2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
         2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


# ---------------------------------------------------------------- statistics
def summarize(values):
    """Return mean, sample SD and 95% CI half-width of the mean."""
    n = len(values)
    mean = statistics.fmean(values)
    if n < 2:
        return mean, 0.0, 0.0
    sd = statistics.stdev(values)
    t = T_975[n - 2] if n - 1 <= len(T_975) else 1.960
    return mean, sd, t * sd / math.sqrt(n)


# ---------------------------------------------------------- synthetic data
def generate_chain_graph(num_triples, path, seed=42, type_ratio=0.2, num_classes=7):
    """Chain-like synthetic RDF graph in N-Triples with exactly num_triples triples.

    Triple i is either a type assertion  ex:entity_i rdf:type ex:Class_k
    (probability type_ratio) or a chain link ex:entity_i ex:relatesTo ex:entity_{i+1}.
    The result is a set of paths with low clustering, as described in the paper.
    """
    rng = random.Random(seed)
    ex = "http://example.org/"
    rdf_type = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>"
    with open(path, "w", encoding="utf-8") as f:
        for i in range(num_triples):
            if rng.random() < type_ratio:
                f.write(f"<{ex}entity_{i}> {rdf_type} <{ex}Class_{rng.randrange(num_classes)}> .\n")
            else:
                f.write(f"<{ex}entity_{i}> <{ex}relatesTo> <{ex}entity_{i + 1}> .\n")


# ------------------------------------------------------------ measurement
def _worker(path, fmt, tau, queue):
    """Runs one TAGS profile in a fresh process and reports time and peak RSS delta."""
    import io
    import contextlib
    import tags

    proc = psutil.Process(os.getpid())
    baseline = proc.memory_info().rss
    peak = [baseline]
    done = threading.Event()

    def sampler():
        while not done.is_set():
            rss = proc.memory_info().rss
            if rss > peak[0]:
                peak[0] = rss
            time.sleep(0.005)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        res = tags.analyze_knowledge_graph(path, file_format=fmt, tau=tau)
    elapsed = time.perf_counter() - t0
    done.set()
    th.join()
    peak[0] = max(peak[0], proc.memory_info().rss)
    m1 = res["metrics"]["M1"][0] if isinstance(res, dict) and "metrics" in res else None
    queue.put({"time_s": elapsed, "peak_rss_delta_mb": (peak[0] - baseline) / 2**20, "M1": m1})


def measure(path, fmt=None, tau=2, runs=5):
    ctx = mp.get_context("spawn")
    rows = []
    for r in range(1, runs + 1):
        q = ctx.Queue()
        p = ctx.Process(target=_worker, args=(path, fmt, tau, q))
        p.start()
        p.join()
        if p.exitcode != 0:
            raise RuntimeError(f"run {r} failed (exit code {p.exitcode}; possibly out of memory)")
        row = q.get()
        row["run"] = r
        rows.append(row)
        print(f"    run {r}: {row['time_s']:.3f} s, peak RSS delta {row['peak_rss_delta_mb']:.2f} MB")
    return rows


def environment():
    import rdflib
    return (f"Python {platform.python_version()}, rdflib {rdflib.__version__}, psutil {psutil.__version__}, "
            f"{platform.system()} {platform.release()}, CPU: {platform.processor() or platform.machine()}, "
            f"{os.cpu_count()} logical cores, RAM {psutil.virtual_memory().total / 2**30:.1f} GB")


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------- commands
def cmd_synthetic(args):
    os.makedirs(args.out, exist_ok=True)
    data_dir = os.path.join(args.out, "synthetic_data")
    os.makedirs(data_dir, exist_ok=True)
    per_run, summary = [], []
    for n in args.sizes:
        path = os.path.join(data_dir, f"chain_{n}.nt")
        if not os.path.exists(path):
            generate_chain_graph(n, path, seed=args.seed)
        print(f"[{n:,} triples]")
        rows = measure(path, "nt", args.tau, args.runs)
        for r in rows:
            per_run.append({"triples": n, **r})
        t = summarize([r["time_s"] for r in rows])
        m = summarize([r["peak_rss_delta_mb"] for r in rows])
        summary.append({"triples": n, "runs": args.runs,
                        "time_mean_s": t[0], "time_sd_s": t[1], "time_ci95_low": t[0] - t[2], "time_ci95_high": t[0] + t[2],
                        "rss_mean_mb": m[0], "rss_sd_mb": m[1], "rss_ci95_low": m[0] - m[2], "rss_ci95_high": m[0] + m[2]})
        if not args.keep_data:
            os.remove(path)

    write_csv(os.path.join(args.out, "synthetic_runs.csv"), per_run,
              ["triples", "run", "time_s", "peak_rss_delta_mb", "M1"])
    write_csv(os.path.join(args.out, "synthetic_summary.csv"), summary, list(summary[0].keys()))

    # Linear fit (time and memory vs. triples) and extrapolation (Table 6)
    xs = [s["triples"] for s in summary]
    fit_t = linfit(xs, [s["time_mean_s"] for s in summary])
    fit_m = linfit(xs, [s["rss_mean_mb"] for s in summary])
    extra = [{"triples": n, "projected_time_s": fit_t[0] * n + fit_t[1],
              "projected_peak_rss_delta_mb": fit_m[0] * n + fit_m[1]} for n in args.extrapolate]
    if extra:
        write_csv(os.path.join(args.out, "synthetic_extrapolation.csv"), extra, list(extra[0].keys()))
    loglog = linfit([math.log10(x) for x in xs], [math.log10(s["time_mean_s"]) for s in summary])

    print("\nEnvironment:", environment())
    print(f"\nMeasured ({args.runs} runs per size)")
    print(f"{'triples':>12} {'mean time (s)':>14} {'SD (s)':>9} {'95% CI (s)':>22} {'peak RSS delta (MB)':>20}")
    for s in summary:
        ci = f"[{s['time_ci95_low']:.3f}, {s['time_ci95_high']:.3f}]"
        print(f"{s['triples']:>12,} {s['time_mean_s']:>14.3f} {s['time_sd_s']:>9.3f} {ci:>22} {s['rss_mean_mb']:>20.2f}")
    print(f"\nLinear fit (time):   t = {fit_t[0]:.4e} * |T| + {fit_t[1]:.4f}   (R^2 = {fit_t[2]:.4f})")
    print(f"Log-log fit (time):  slope = {loglog[0]:.4f}   (R^2 = {loglog[2]:.4f})")
    if extra:
        print("\nExtrapolated from the linear fits")
        print(f"{'triples':>12} {'projected time (s)':>19} {'projected peak RSS delta (MB)':>30}")
        for e in extra:
            print(f"{e['triples']:>12,} {e['projected_time_s']:>19.3f} {e['projected_peak_rss_delta_mb']:>30.2f}")
    plot(summary, loglog, os.path.join(args.out, "tags_scalability.png"))


def cmd_file(args):
    os.makedirs(args.out, exist_ok=True)
    print(f"[{os.path.basename(args.path)}]")
    rows = measure(args.path, args.format, args.tau, args.runs)
    t = summarize([r["time_s"] for r in rows])
    m = summarize([r["peak_rss_delta_mb"] for r in rows])
    name = os.path.splitext(os.path.basename(args.path))[0]
    write_csv(os.path.join(args.out, f"{name}_runs.csv"), rows, ["run", "time_s", "peak_rss_delta_mb", "M1"])
    print("\nEnvironment:", environment())
    print(f"Time:            mean {t[0]:.3f} s, SD {t[1]:.3f} s, 95% CI [{t[0] - t[2]:.3f}, {t[0] + t[2]:.3f}] s")
    print(f"Peak RSS delta:  mean {m[0]:.2f} MB, SD {m[1]:.2f} MB, 95% CI [{m[0] - m[2]:.2f}, {m[0] + m[2]:.2f}] MB")


# ---------------------------------------------------------------- helpers
def linfit(xs, ys):
    """Ordinary least squares y = a x + b; returns (a, b, R^2)."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    b = my - a * mx
    ss_res = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return a, b, (1 - ss_res / ss_tot) if ss_tot else 1.0


def plot(summary, loglog, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    xs = [s["triples"] for s in summary]
    ys = [s["time_mean_s"] for s in summary]
    err = [s["time_ci95_high"] - s["time_mean_s"] for s in summary]
    fig, ax = plt.subplots(figsize=(6, 4.2))
    ax.errorbar(xs, ys, yerr=err, fmt="o-", capsize=3, label="Measured (mean, 95% CI)")
    fx = [xs[0] * (xs[-1] / xs[0]) ** (i / 100) for i in range(101)]
    ax.plot(fx, [10 ** (loglog[0] * math.log10(x) + loglog[1]) for x in fx], "--",
            label=f"Log-log fit (slope {loglog[0]:.3f}, $R^2$ = {loglog[2]:.4f})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Dataset size |T| (triples)")
    ax.set_ylabel("Execution time (s)")
    ax.grid(True, which="both", ls=":", alpha=0.6)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    print(f"\nFigure saved to {os.path.relpath(path)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synthetic", help="scalability benchmark on generated chain-like graphs")
    s.add_argument("--sizes", type=int, nargs="+", default=[1000, 10000, 100000, 1000000])
    s.add_argument("--extrapolate", type=int, nargs="*", default=[5000000, 10000000, 50000000])
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--keep-data", action="store_true", help="keep generated N-Triples files")
    f = sub.add_parser("file", help="benchmark TAGS on an existing RDF file")
    f.add_argument("path")
    f.add_argument("-f", "--format", default=None)
    for p in (s, f):
        p.add_argument("--runs", type=int, default=5)
        p.add_argument("--tau", type=int, default=2)
        p.add_argument("--out", default=os.path.join(ROOT, "results"))
    args = ap.parse_args()
    cmd_synthetic(args) if args.cmd == "synthetic" else cmd_file(args)


if __name__ == "__main__":
    main()
