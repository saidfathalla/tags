#!/usr/bin/env python3
"""
Flat-NetworkX baseline and taxonomic-isolation ablation.

Compares three projections of the same RDF file:
  1. Flat (no filtering): a single-pass NetworkX graph in which every triple with
     an IRI/blank-node object becomes an edge, including rdf:type triples, so
     class nodes act as hubs.
  2. Flat + post-hoc filter: the same NetworkX graph after removing the edges
     created only by rdf:type triples; class nodes stay in the graph as vertices.
  3. TAGS: the two-pass projection of src/tags.py (classes and rdf:type triples
     are separated before the graph is built).

In all three, literals are excluded, parallel and inverse links are collapsed
into one undirected edge, and self-loops are ignored, so differences come only
from how the taxonomic layer is handled. Metrics for (1) and (2) are computed
with NetworkX; runtime is the mean over --runs repetitions.

Usage:
  python benchmarks/flat_networkx_baseline.py tests/test_baseline.ttl
  python benchmarks/flat_networkx_baseline.py examples/kg-sample_triples_3171.ttl --runs 5
"""

import argparse
import contextlib
import io
import os
import statistics
import sys
import time

import networkx as nx
import rdflib
from rdflib import RDF, URIRef, BNode

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import tags  # noqa: E402

METRICS = ["M2", "M3", "M5", "M6", "M8", "M9", "M10", "M11", "M12", "M13", "M14"]


def nid(t):
    return f"_:{t}" if isinstance(t, BNode) else str(t)


def flat_networkx(path, fmt=None, tau=2, post_hoc_filter=False):
    """Single-pass NetworkX projection; optionally drop rdf:type edges afterwards."""
    g = rdflib.Graph()
    g.parse(path, format=fmt) if fmt else g.parse(path)
    G = nx.Graph()
    typed, type_only_edges = set(), set()
    non_type_edges = set()
    for s, p, o in g:
        if not isinstance(o, (URIRef, BNode)):
            G.add_node(nid(s))
            continue
        a, b = nid(s), nid(o)
        if a == b:
            G.add_node(a)
            continue
        G.add_edge(a, b)
        e = (a, b) if a < b else (b, a)
        if p == RDF.type:
            typed.add(a)
            type_only_edges.add(e)
        else:
            non_type_edges.add(e)
    if post_hoc_filter:
        G.remove_edges_from(type_only_edges - non_type_edges)
    return metrics_nx(G, typed, tau)


def metrics_nx(G, typed, tau):
    n, m = G.number_of_nodes(), G.number_of_edges()
    deg = dict(G.degree())
    avg = 2 * m / n if n else 0.0
    clust = nx.clustering(G)
    comps = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
    return {
        "M2": n, "M3": m, "M5": avg, "M6": nx.density(G),
        "M8": max(clust.values()) if clust else 0.0,
        "M9": sum(clust.values()) / n if n else 0.0,
        "M10": max(deg.values()) / avg if avg else 0.0,
        "M11": len(comps),
        "M12": sum(1 for v in typed if deg.get(v, 0) == 0),
        "M13": sum(1 for c in comps if c <= tau),
        "M14": comps[0] / n if n else 0.0,
    }


def run_tags(path, fmt, tau):
    with contextlib.redirect_stdout(io.StringIO()):
        res = tags.analyze_knowledge_graph(path, file_format=fmt, tau=tau)
    return {k: res["metrics"][k][0] for k in METRICS}


def timed(fn, runs):
    times, out = [], None
    for _ in range(runs):
        t0 = time.perf_counter()
        out = fn()
        times.append(time.perf_counter() - t0)
    sd = statistics.stdev(times) if runs > 1 else 0.0
    return out, statistics.fmean(times), sd


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("-f", "--format", default=None)
    ap.add_argument("--tau", type=int, default=2)
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()

    flat, t_flat, sd_flat = timed(lambda: flat_networkx(a.path, a.format, a.tau), a.runs)
    filt, t_filt, sd_filt = timed(lambda: flat_networkx(a.path, a.format, a.tau, True), a.runs)
    tg, t_tags, sd_tags = timed(lambda: run_tags(a.path, a.format, a.tau), a.runs)

    print(f"File: {a.path}   (tau = {a.tau}, runs = {a.runs})\n")
    print(f"{'Metric':<6} {'Flat (no filter)':>18} {'Flat + post-hoc':>18} {'TAGS':>14}")
    for k in METRICS:
        print(f"{k:<6} {flat[k]:>18.5g} {filt[k]:>18.5g} {tg[k]:>14.5g}")
    print(f"\n{'Time (s)':<6} {t_flat:>14.3f}±{sd_flat:.3f} {t_filt:>14.3f}±{sd_filt:.3f} {t_tags:>10.3f}±{sd_tags:.3f}")
    print("\nAll time values are mean ± SD over the runs and include parsing.")


if __name__ == "__main__":
    main()
