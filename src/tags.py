#!/usr/bin/env python3
"""
Knowledge Graph Semantic Profiler & FAIR Metadata Generator
Computes analytical graph metrics and exports reusable W3C VoID metadata.
"""

import os
import sys
import math
import io
import base64
import argparse
from collections import defaultdict

# 1. Secure Dependency Imports
try:
    import rdflib
    from rdflib import RDF, URIRef, Literal, Namespace
except ImportError:
    print("\n[Error] Missing semantic runtime dependencies.")
    print("        Please run: pip install rdflib matplotlib\n")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('Agg')  # Headless cluster rendering path
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Establish standardized namespaces for export alignment
VOID = Namespace("https://schema.org/void#")
DCTERMS = Namespace("https://schema.org/dcterms#")
XSD = Namespace("https://schema.org/xsd#")


def analyze_knowledge_graph(ttl_file):
    """
    Parses turtle graph via RDFLib to calculate semantic and topological analytics.
    """
    g = rdflib.Graph()
    try:
        g.parse(ttl_file, format="turtle")
    except Exception as e:
        print(f"[Parser Error] Failed to parse {ttl_file}: {e}")
        return None

    M1 = len(g)
    if M1 == 0:
        return None

    # Structural metrics initialization
    subjects = set()
    predicates = set()
    objects = set()
    classes = defaultdict(int)
    
    taxonomic_triples = 0
    structural_edges = set()
    adj = defaultdict(set)
    predicate_by_subject = defaultdict(set)

    for s, p, o in g:
        subjects.add(s)
        predicates.add(p)
        objects.add(o)
        
        if p == RDF.type:
            taxonomic_triples += 1
            classes[o] += 1
        else:
            # Isolate topological object property layout paths
            if isinstance(o, (URIRef, rdflib.BNode)):
                structural_edges.add(tuple(sorted([str(s), str(o)])))
                adj[str(s)].add(str(o))
                adj[str(o)].add(str(s))
            predicate_by_subject[str(s)].add(str(p))

    M2 = len(subjects)
    M3 = len(structural_edges)
    M4 = taxonomic_triples
    M15 = len(predicates)

    # Core Metric Matrix Formulations
    M5 = (2.0 * M3) / M2 if M2 > 0 else 0.0
    M6 = (2.0 * M3) / (M2 * (M2 - 1)) if M2 > 1 else 0.0
    M7 = float(M3) / M4 if M4 > 0 else 0.0

    # M8 & M9: Local and Global Clustering Coefficients
    local_cluster_coeffs = {}
    for node in adj:
        neighbors = adj[node]
        k_i = len(neighbors)
        if k_i < 2:
            local_cluster_coeffs[node] = 0.0
            continue
        
        # Count links between neighbors
        e_i = 0
        neighbors_list = list(neighbors)
        for i in range(len(neighbors_list)):
            for j in range(i + 1, len(neighbors_list)):
                if neighbors_list[j] in adj[neighbors_list[i]]:
                    e_i += 1
        local_cluster_coeffs[node] = (2.0 * e_i) / (k_i * (k_i - 1))

    M8 = np.mean(list(local_cluster_coeffs.values())) if local_cluster_coeffs else 0.0
    M9 = M8  

    # M10: Degree Centrality Polarization
    max_degree = max(len(neighbors) for neighbors in adj.values()) if adj else 0
    M10 = max_degree / M5 if M5 > 0 else 0.0

    # Information Entropy calculation across schemas (M16)
    total_types = sum(classes.values())
    M16 = 0.0
    if total_types > 0:
        for c, count in classes.items():
            p_c = float(count) / total_types
            M16 -= p_c * math.log2(p_c)

    # Topological component tracing via Breadth-First Traversal
    visited = set()
    components = []
    all_nodes = set(adj.keys()) | {str(s) for s in subjects if str(s) in adj}
    
    for node in all_nodes:
        if node not in visited:
            comp = []
            queue = [node]
            visited.add(node)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for nbr in adj[curr]:
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(nbr)
            components.append(comp)

    M11 = len(components)
    max_comp_size = max(len(comp) for comp in components) if components else 0
    M14 = float(max_comp_size) / M2 if M2 > 0 else 0.0

    # M12 Type-Only Orphan Count calculation
    all_subjects_str = {str(s) for s in subjects}
    structural_nodes = set(adj.keys())
    M12 = len([s for s in all_subjects_str if s not in structural_nodes])

    # M13 Prunable Weak Islands Count
    M13 = sum(1 for comp in components if len(comp) <= 2)

    sorted_hubs = sorted(adj.items(), key=lambda x: len(x[1]), reverse=True)[:5]

    return {
        "raw_counts": {"triples": M1, "subjects": M2, "properties": M15, "objects": len(objects), "classes": len(classes)},
        "metrics": {
            "M1": [M1, "Total Asserted Triples", "Total explicit statements parsed from data."],
            "M2": [M2, "Unique Entity Nodes", "Total graph instances exclusive of abstract schemas."],
            "M3": [M3, "Structural Object Links", "Total unique undirected object property graph edges."],
            "M4": [M4, "Taxonomic Type Assertions", "Total core classification declarations (rdf:type)."],
            "M5": [M5, "Average Node Connection", "Mean edge connection weight across target nodes."],
            "M6": [M6, "Graph Density Factor", "Observed density vs absolute mathematical complete graph limits."],
            "M7": [M7, "Structural-to-Semantic Ratio", "Proportion match balancing connections against descriptive metadata labels."],
            "M8": [M8, "Local Clustering Coefficient (Avg)", "Quantifies how close neighborhoods are to forming complete cliques."],
            "M9": [M9, "Global Clustering Coefficient", "Mathematical mean of localized operational clustering patterns."],
            "M10": [M10, "Degree Centrality Polarization", "Exposes whether critical hub nodes dominate network routing."],
            "M11": [M11, "Total Disconnected Components", "Isolated sub-mesh cluster partition groupings."],
            "M12": [M12, "Type-Only Orphan Count", "Subjects possessing classification declarations but lacking structural properties."],
            "M13": [M13, "Prunable Weak Islands Count", "Isolated component subgraphs containing two or fewer nodes."],
            "M14": [M14, "Maximum Component Dominance Ratio", "Size ratio of the primary Giant Connected Component (GCC)."],
            "M15": [M15, "Dynamic Predicate Diversity Factor", "Total unique object properties/predicates evaluated."],
            "M16": [M16, "Class Imbalance Entropy", "Information metric indicating instance density spreading weights across schema classes."]
        },
        "hubs": sorted_hubs,
        "classes": classes,
        "predicates": predicates,
        "pred_by_sub": predicate_by_subject
    }


def export_void_statistics(results, base_name, output_dir):
    """
    Generates a fully valid, machine-readable W3C VoID metadata dataset profile.
    """
    void_g = rdflib.Graph()
    
    void_g.bind("void", VOID)
    void_g.bind("dcterms", DCTERMS)
    void_g.bind("xsd", XSD)
    
    dataset_uri = URIRef(f"http://purls.helmholtz-metadaten.de/helmholtzkg/{base_name}")
    
    void_g.add((dataset_uri, RDF.type, VOID.Dataset))
    void_g.add((dataset_uri, DCTERMS.title, Literal(f"Topological Profile for {base_name}", lang="en")))
    void_g.add((dataset_uri, VOID.triples, Literal(results['raw_counts']['triples'], datatype=XSD.integer)))
    void_g.add((dataset_uri, VOID.properties, Literal(results['raw_counts']['properties'], datatype=XSD.integer)))
    void_g.add((dataset_uri, VOID.classes, Literal(results['raw_counts']['classes'], datatype=XSD.integer)))
    void_g.add((dataset_uri, VOID.distinctSubjects, Literal(results['raw_counts']['subjects'], datatype=XSD.integer)))
    void_g.add((dataset_uri, VOID.distinctObjects, Literal(results['raw_counts']['objects'], datatype=XSD.integer)))

    for cls_uri, count in results['classes'].items():
        if isinstance(cls_uri, URIRef):
            partition = rdflib.BNode()
            void_g.add((dataset_uri, VOID.classPartition, partition))
            void_g.add((partition, VOID.class_, cls_uri))
            void_g.add((partition, VOID.entities, Literal(count, datatype=XSD.integer)))

    void_out_path = os.path.join(output_dir, f"{base_name}_void.ttl")
    void_g.serialize(destination=void_out_path, format="turtle")
    return void_out_path


def generate_advanced_plots(results, output_dir, base_name):
    """
    Renders high-impact diagnostic figures tailored for provenance analysis.
    """
    if not HAS_MATPLOTLIB:
        return "", ""

    preds = list(results['predicates'])
    p_len = min(len(preds), 12)
    preds_subset = preds[:p_len]
    matrix = np.zeros((p_len, p_len))
    
    for i in range(p_len):
        for j in range(p_len):
            if i == j:
                matrix[i][j] = sum(1 for s, p_set in results['pred_by_sub'].items() if str(preds_subset[i]) in p_set)
            else:
                matrix[i][j] = sum(1 for s, p_set in results['pred_by_sub'].items() if str(preds_subset[i]) in p_set and str(preds_subset[j]) in p_set)

    fig, ax = plt.subplots(figsize=(6, 5.5))
    cax = ax.matshow(matrix, cmap="YlGnBu")
    fig.colorbar(cax, fraction=0.046, pad=0.04)
    
    labels = [str(p).split('/')[-1].split('#')[-1] for p in preds_subset]
    ax.set_xticks(range(p_len))
    ax.set_yticks(range(p_len))
    ax.set_xticklabels(labels, rotation=45, ha='left', fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("Predicate Co-occurrence Matrix", fontsize=10, fontweight='bold', pad=20)
    plt.tight_layout()
    
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png', dpi=150)
    buf1.seek(0)
    plot1_b64 = base64.b64encode(buf1.read()).decode('utf-8')
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    classes_sorted = sorted(results['classes'].items(), key=lambda x: x[1], reverse=True)[:8]
    c_labels = [str(c[0]).split('/')[-1].split('#')[-1] for c in classes_sorted]
    c_vals = [c[1] for c in classes_sorted]
    
    ax.barh(c_labels, c_vals, color='#475569', edgecolor='#1e293b')
    ax.invert_yaxis()
    ax.set_title("Top Instance Density Classes", fontsize=10, fontweight='bold')
    ax.set_xlabel("Instance Counts")
    ax.grid(axis='x', linestyle=':', alpha=0.6)
    plt.tight_layout()

    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png', dpi=150)
    buf2.seek(0)
    plot2_b64 = base64.b64encode(buf2.read()).decode('utf-8')
    plt.close(fig)

    return plot1_b64, plot2_b64


def display_terminal_dashboard(results, base_name):
    """
    Renders cleanly aligned metrics and detected structural hubs to terminal standard output.
    """
    tw = 67
    print("\n" + "═" * tw)
    print(f" FAIR STRUCTURAL METRICS ENGINE PROFILE REPORT: {base_name}.ttl".ljust(tw - 1) + "║")
    print("═" * tw)
    print(f" │ {'Code':<5} │ {'Metric Profile Structural Indicator':<38} │ {'Value':<13} │")
    print("─" * tw)
    
    sorted_metrics = sorted(results['metrics'].items(), key=lambda x: int(x[0][1:]))
    for code, values in sorted_metrics:
        val_str = f"{values[0]:,}" if isinstance(values[0], int) else f"{values[0]:.5f}"
        print(f" │ {code:<5} │ {values[1]:<38} │ {val_str:>13} │")
        
    print("─" * tw)
    print(f" │ TOPOLOGICAL HUBS DISCOVERED (HIGHEST CENTRALITY DEGREE PATHS)")
    print("─" * tw)
    for i, (hub, neighbors) in enumerate(results['hubs'], 1):
        trunc_hub = hub if len(hub) <= 48 else hub[:45] + "..."
        print(f" │ Rank [{i:02d}]  Degree: {len(neighbors):<4}  URI: <{trunc_hub:<48}>")
    print("═" * tw + "\n")


def generate_html_dashboard(results, base_name, output_dir, p1_b64, p2_b64, void_path):
    """
    Assembles a self-contained HTML dashboard incorporating results and VoID provenance references.
    """
    html_path = os.path.join(output_dir, f"{base_name}_dashboard.html")
    
    rows_html = ""
    sorted_metrics = sorted(results['metrics'].items(), key=lambda x: int(x[0][1:]))
    for k, v in sorted_metrics:
        val = v[0]
        fmt_spec = ",d" if isinstance(val, int) else ".5f"
        val_str = f"{val:{fmt_spec}}"
        rows_html += f'<tr><td class="code"><b>{k}</b></td><td>{v[1]}</td><td class="value"><code>{val_str}</code></td><td class="desc">{v[2]}</td></tr>'

    hubs_html = "".join([f'<div class="hub-item"><span class="hub-rank">#{i:02d}</span><span class="hub-uri">&lt;{h}&gt;</span><span class="hub-degree">Degree: <b>{len(n)}</b></span></div>' for i, (h, n) in enumerate(results['hubs'], 1)])

    html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>FAIR Graph Dashboard</title><style>body {{ font-family: -apple-system, sans-serif; color: #1e293b; background: #f8fafc; padding: 25px; }} .container {{ max-width: 1150px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }} h1 {{ color: #0f172a; margin-bottom: 5px; }} .meta-badge {{ inline-block; background: #e2e8f0; color: #334155; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-family: monospace; }} table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }} th, td {{ padding: 12px; border-bottom: 1px solid #e2e8f0; text-align: left; font-size: 14px; }} th {{ background: #f1f5f9; color: #475569; }} .code {{ color: #0f766e; font-family: monospace; }} .value {{ text-align: right; font-weight: bold; font-family: monospace; }} .grid {{ display: flex; gap: 25px; margin-top: 25px; }} .card {{ flex: 1; border: 1px solid #e2e8f0; padding: 20px; border-radius: 6px; text-align: center; background: #fff; }} .card img {{ max-width: 100%; height: auto; }} .hub-list {{ background: #fafafa; padding: 15px; border: 1px solid #e2e8f0; border-radius: 6px; }} .hub-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dashed #e2e8f0; font-family: monospace; font-size: 13px; }} .hub-rank {{ color: #0ea5e9; font-weight: bold; }} .missing {{ padding: 40px; background: #f8fafc; color: #94a3b8; font-style: italic; }}</style></head><body><div class="container"><h1>Knowledge Graph FAIR Topological Profile</h1><p>Source Asset: <b>{base_name}.ttl</b> | Linked Provenance Summary: <span class="meta-badge">{os.path.basename(void_path)}</span></p><table><thead><tr><th>Code</th><th>Indicator Description</th><th style="text-align:right;">Measured Value</th><th>Theoretical Explanation Context</th></tr></thead><tbody>{rows_html}</tbody></table><h2>Topological Hubs Discovered</h2><div class="hub-list">{hubs_html}</div><h2>Advanced Profiling Visual Frameworks</h2><div class="grid"><div class="card"><h3>Dynamic Predicate Co-occurrence Matrix</h3>{f'<img src="data:image/png;base64,{p1_b64}">' if p1_b64 else '<div class="missing">Matplotlib omitted. Execution configuration missing.</div>'}</div><div class="card"><h3>Taxonomic Class Density Profile</h3>{f'<img src="data:image/png;base64,{p2_b64}">' if p2_b64 else '<div class="missing">Matplotlib omitted. Execution configuration missing.</div>'}</div></div></div></body></html>"""
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def main():
    parser = argparse.ArgumentParser(description="FAIR Knowledge Graph Analytics Profiler Pipeline Engine.")
    parser.add_argument("ttl_file", help="Path to targeted RDF Turtle file.")
    parser.add_argument("-o", "--output-dir", default=None, help="Target output directory folder path.")
    args = parser.parse_args()
    
    if not os.path.exists(args.ttl_file):
        print(f"Error: Target graph path '{args.ttl_file}' does not exist.")
        return

    # Set up default fallback out path to project root folder: `../output`
    if args.output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.abspath(os.path.join(script_dir, "..", "output"))
    else:
        target_dir = args.output_dir

    # Guarantee target directory existence safely
    os.makedirs(target_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(args.ttl_file))[0]
    
    print(f"[System Execution] Commencing programmatic parsing of structural schema graph...")
    results = analyze_knowledge_graph(args.ttl_file)
    if not results:
        return

    # Mirror metric analysis arrays straight to standard terminal display
    display_terminal_dashboard(results, base_name)
    
    # 2. Export standardized machine-reusable W3C VoID metadata graph file
    void_path = export_void_statistics(results, base_name, target_dir)
    print(f"[FAIR Data Success] Reusable W3C VoID stats exported to: {void_path}")
    
    p1_b64, p2_b64 = "", ""
    if HAS_MATPLOTLIB:
        p1_b64, p2_b64 = generate_advanced_plots(results, target_dir, base_name)
    
    # 3. Assemble structural dashboard HTML report
    generate_html_dashboard(results, base_name, target_dir, p1_b64, p2_b64, void_path)
    print(f"[System Success] Responsive analytics dashboard updated successfully to: {target_dir}\n")


if __name__ == "__main__":
    main()
