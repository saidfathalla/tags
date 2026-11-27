#!/usr/bin/env python3
"""
Flat-NetworkX baselines and taxonomic-isolation ablation.

Compares four ways of building the structural graph from the same RDF file:
  flat          single-pass NetworkX graph from every triple with an IRI/blank-node
                object, rdf:type triples included (class nodes become hubs)
  posthoc       the flat graph after removing the edges created only by rdf:type
                triples; class nodes remain as (isolated) vertices
  construction  single-pass NetworkX graph that skips rdf:type triples while it is
                built (the straightforward rdf:type-filtered implementation); vertices
                enter the graph only through edges, so type-only entities are lost
  tags          the two-pass TAGS projection (src/tags.py)

All variants exclude literals, collapse parallel and inverse links, and ignore
self-loops, so differences arise only from how the taxonomic layer is handled.
Each variant runs --runs times in a fresh process; we report the metrics, the mean
and SD of the runtime (including parsing), and the mean peak RSS delta (peak RSS
while the variant runs minus RSS just before it starts, sampled every 5 ms).

Usage:
  python benchmarks/flat_networkx_baseline.py tests/test_baseline.ttl
  python benchmarks/flat_networkx_baseline.py examples/kg-sample_triples_3171.ttl --runs 5
  python benchmarks/flat_networkx_baseline.py examples/DBpedia-mini-samples-Berlin.ttl --runs 5
"""

import argparse
import contextlib
import io
import multiprocessing as mp
import os
import statistics
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

METRICS = ["M2", "M3", "M5", "M6", "M8", "M9", "M10", "M11", "M12", "M13", "M14"]
VARIANTS = ["flat", "posthoc", "construction", "tags"]


def _nid(t):
    from rdflib import BNode
    return f"_:{t}" if isinstance(t, BNode) else str(t)


def networkx_variant(path, fmt, tau, mode):
    """Build a single-pass NetworkX graph and compute the metrics with NetworkX."""
    import networkx as nx
    import rdflib
    from rdflib import RDF, URIRef, BNode

    g = rdflib.Graph()
    g.parse(path, format=fmt) if fmt else g.parse(path)
    G = nx.Graph()
    typed, type_only_edges, other_edges = set(), set(), set()
    for s, p, o in g:
        if p == RDF.type:
            typed.add(_nid(s))
            if mode == "construction":
                continue                       # filter rdf:type while building
        if not isinstance(o, (URIRef, BNode)):
            if mode != "construction":
                G.add_node(_nid(s))            # flat variants keep literal-only subjects
            continue
        a, b = _nid(s), _nid(o)
        if a == b:
            if mode != "construction":
                G.add_node(a)
            continue
        G.add_edge(a, b)
        e = (a, b) if a < b else (b, a)
        (type_only_edges if p == RDF.type else other_edges).add(e)
    if mode == "posthoc":
        G.remove_edges_from(type_only_edges - other_edges)

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
        "M12": sum(1 for v in typed if v in deg and deg[v] == 0),
        "M13": sum(1 for c in comps if c <= tau),
        "M14": comps[0] / n if n else 0.0,
    }


def tags_variant(path, fmt, tau):
    import tags
    with contextlib.redirect_stdout(io.StringIO()):
        res = tags.analyze_knowledge_graph(path, file_format=fmt, tau=tau)
    return {k: res["metrics"][k][0] for k in METRICS}


def _worker(variant, path, fmt, tau, queue):
    import psutil
    import rdflib                 # noqa: F401  (import before measuring, so library
    import networkx               # noqa: F401   loading is not counted as runtime or memory)
    import tags                   # noqa: F401
    proc = psutil.Process(os.getpid())
    baseline = proc.memory_info().rss
    peak = [baseline]
    done = threading.Event()

    def sampler():
        while not done.is_set():
            peak[0] = max(peak[0], proc.memory_info().rss)
            time.sleep(0.005)

    th = threading.Thread(target=sampler, daemon=True)
    th.start()
    t0 = time.perf_counter()
    metrics = tags_variant(path, fmt, tau) if variant == "tags" else networkx_variant(path, fmt, tau, variant)
    elapsed = time.perf_counter() - t0
    done.set()
    th.join()
    peak[0] = max(peak[0], proc.memory_info().rss)
    queue.put({"metrics": metrics, "time_s": elapsed, "rss_mb": (peak[0] - baseline) / 2**20})


def run(variant, path, fmt, tau, runs):
    ctx = mp.get_context("spawn")
    out = []
    for _ in range(runs):
        q = ctx.Queue()
        p = ctx.Process(target=_worker, args=(variant, path, fmt, tau, q))
        p.start()
        p.join()
        if p.exitcode != 0:
            raise RuntimeError(f"{variant} failed (exit code {p.exitcode})")
        out.append(q.get())
    times = [r["time_s"] for r in out]
    return {"metrics": out[-1]["metrics"],
            "time_mean": statistics.fmean(times),
            "time_sd": statistics.stdev(times) if runs > 1 else 0.0,
            "rss_mean": statistics.fmean(r["rss_mb"] for r in out)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("-f", "--format", default=None)
    ap.add_argument("--tau", type=int, default=2)
    ap.add_argument("--runs", type=int, default=5)
    a = ap.parse_args()

    res = {}
    for v in VARIANTS:
        print(f"running {v} ...", flush=True)
        res[v] = run(v, a.path, a.format, a.tau, a.runs)

    print(f"\nFile: {a.path}   (tau = {a.tau}, runs = {a.runs})\n")
    print(f"{'Metric':<18}" + "".join(f"{v:>16}" for v in VARIANTS))
    for k in METRICS:
        print(f"{k:<18}" + "".join(f"{res[v]['metrics'][k]:>16.5g}" for v in VARIANTS))
    print(f"{'Time mean (s)':<18}" + "".join(f"{res[v]['time_mean']:>16.3f}" for v in VARIANTS))
    print(f"{'Time SD (s)':<18}" + "".join(f"{res[v]['time_sd']:>16.3f}" for v in VARIANTS))
    print(f"{'Peak RSS delta (MB)':<18}" + "".join(f"{res[v]['rss_mean']:>16.2f}" for v in VARIANTS))


if __name__ == "__main__":
    main()
