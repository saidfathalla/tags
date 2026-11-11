#!/usr/bin/env python3
"""
Sensitivity of the prunable weak islands count (M13) to the threshold tau.

The file is profiled once; N_weak(tau) is then computed from the component
size distribution for every requested tau.

Usage:
  python benchmarks/tau_sensitivity.py data/rdf-export-orkg.nt -f nt
  python benchmarks/tau_sensitivity.py examples/kg-sample_triples_3171.ttl --taus 1 2 3 5 10 20
"""

import argparse
import contextlib
import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import tags  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("-f", "--format", default=None)
    ap.add_argument("--taus", type=int, nargs="+", default=[1, 2, 3, 5, 10, 20])
    a = ap.parse_args()

    with contextlib.redirect_stdout(io.StringIO()):
        res = tags.analyze_knowledge_graph(a.path, file_format=a.format)
    sizes = res["component_sizes"]
    m11 = len(sizes)
    print(f"File: {a.path}   M11 = {m11:,} components\n")
    print(f"{'tau':>5} {'N_weak':>12} {'% of M11':>10}")
    for t in a.taus:
        n = sum(1 for s in sizes if s <= t)
        print(f"{t:>5} {n:>12,} {100.0 * n / m11 if m11 else 0.0:>9.1f}%")
    print("\nLaTeX rows:")
    for t in a.taus:
        n = sum(1 for s in sizes if s <= t)
        print(f"{t} & {n:,} & {100.0 * n / m11 if m11 else 0.0:.1f} \\\\")


if __name__ == "__main__":
    main()
