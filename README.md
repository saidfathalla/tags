[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Build Status](https://github.com/saidfathalla/TAGS/actions/workflows/pytest.yml/badge.svg)](https://github.com/saidfathalla/TAGS/actions)
[![FAIR Principles](https://img.shields.io/badge/FAIR-Supported-brightgreen.svg)](https://www.go-fair.org/fair-principles/)
[![RDF/Semantic Web](https://img.shields.io/badge/Semantic-RDF-orange.svg)](https://www.w3.org/RDF/)

# TAGS: Topological Analysis of Graph Structure

TAGS is a two-pass graph profiling framework that computes **16 topological and semantic metrics** (combining standard network-science measures with RDF-specific quality indicators) on the instance-level structure of an RDF graph, after separating it from the taxonomic (`rdf:type`) layer.

Profilers that treat every RDF triple as a graph edge let class nodes act as artificial hubs ("semantic inflation"). TAGS keeps the taxonomic layer out of the structural graph, so the topological metrics describe how instances are actually connected.

---

## Features

- **Two-pass taxonomic isolation**: pass 1 identifies schema classes (objects of `rdf:type`); pass 2 builds the instance-level structural graph without them.
- **Explicit projection rules**: the structural graph is a simple undirected graph over instance nodes. Literals are excluded, parallel and inverse links between the same pair of nodes are collapsed into one edge, and self-loops are ignored.
- **16 metrics** ($M_1$–$M_{16}$) for size, connectivity, clustering, fragmentation, and vocabulary usage (see the table below).
- **Machine-actionable profiles**: standard statistics as W3C VoID properties, and all 16 metrics as W3C DQV quality measurements, described by the TAGS metric vocabulary ([`vocab/tags_vocab.ttl`](vocab/tags_vocab.ttl)).
- **HTML dashboard** with a predicate co-occurrence matrix and class distribution plot.
- **Tested**: the test suite checks all 16 metrics against the hand-derived values for the reference graph $G_{ref}$ and covers 13 edge cases.

---

## Metric Summary

| ID      | Metric                               | Range                                      | Definition                                                                   |
| :------ | :----------------------------------- | :----------------------------------------- | :--------------------------------------------------------------------------- |
| **M1**  | Total Asserted Triples               | $[0, \infty)$                              | Number of triples                                                            |
| **M2**  | Unique Entity Nodes                  | $[0, \infty)$                              | Instance nodes (IRIs and blank nodes, excluding schema classes and literals) |
| **M3**  | Structural Object Links              | $[0, \infty)$                              | Undirected instance-level edges (collapsed)                                  |
| **M4**  | Taxonomic Type Assertions            | $[0, \infty)$                              | Number of `rdf:type` triples                                                 |
| **M5**  | Average Node Connection              | $[0, \vert V\vert-1]$                      | $2\vert E\vert/\vert V\vert$                                                 |
| **M6**  | Graph Density Factor                 | $[0, 1]$                                   | $2\vert E\vert/(\vert V\vert(\vert V\vert-1))$                               |
| **M7**  | Structural-to-Semantic Ratio         | $[0, \infty)$                              | $M_3 / M_4$                                                                  |
| **M8**  | Maximum Local Clustering Coefficient | $[0, 1]$                                   | Maximum local clustering coefficient                                         |
| **M9**  | Average Clustering Coefficient       | $[0, 1]$                                   | Mean local clustering coefficient                                            |
| **M10** | Degree Centrality Polarization       | $[1, \vert V\vert/2]$ for connected graphs | Maximum degree / average degree                                              |
| **M11** | Total Disconnected Components        | $[1, \vert V\vert]$                        | Number of connected components                                               |
| **M12** | Type-Only Orphan Count               | $[0, \vert V\vert]$                        | `rdf:type`-annotated instance nodes with no structural edge                  |
| **M13** | Prunable Weak Islands Count          | $[0, M_{11}]$                              | Components with at most $\tau$ nodes (`--tau`, default 2)                    |
| **M14** | Maximum Component Dominance Ratio    | $[1/\vert V\vert, 1]$                      | Share of instance nodes in the largest component                             |
| **M15** | Dynamic Predicate Diversity Factor   | $[0, 1]$                                   | Distinct object properties / object-property triples                         |
| **M16** | Class Imbalance Entropy              | $[0, \log_2 \vert C\vert]$                 | Shannon entropy of `rdf:type` assertions over classes                        |

Instance nodes with no structural edge and no `rdf:type` are not counted in $M_{12}$; they are reported separately as a diagnostic.

---

## Installation

Python 3.12 is recommended (the experiments in the paper used Python 3.12.3).

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins the exact versions used (rdflib 7.0.0, psutil 5.9.5, NetworkX 2.8.8, ...). NetworkX is only needed for the Flat-NetworkX baseline; TAGS itself uses plain Python data structures.

---

## Usage

```bash
python3 src/tags.py <rdf_file> [-o OUTPUT_DIR] [-f FORMAT] [--tau TAU] [--flat]
```

| Option               | Meaning                                                                                   |
| :------------------- | :---------------------------------------------------------------------------------------- |
| `-o`, `--output-dir` | Output folder (default: `output/` in the repository)                                      |
| `-f`, `--format`     | RDF format (`turtle`, `nt`, `xml`, `json-ld`, ...); guessed from the extension if omitted |
| `--tau`              | Threshold for prunable weak islands $M_{13}$ (default: 2)                                 |
| `--flat`             | Ablation mode: keep `rdf:type` triples as edges (no taxonomic isolation)                  |

Example:

```bash
python3 src/tags.py tests/test_baseline.ttl -o output/
```

### Outputs

For an input `name.ttl`, TAGS writes to the output folder:

- `name_void.ttl`: VoID profile with standard statistics (`void:triples`, `void:classPartition`, ...) and all 16 metrics as `dqv:QualityMeasurement`s; the threshold $\tau$ is recorded as `tags:weakIslandThreshold`.
- `tags_vocab.ttl`: the TAGS metric vocabulary (one `dqv:Metric` per metric).
- `name_dashboard.html`: self-contained HTML dashboard.

The 16 metrics are also printed in the terminal, together with the top hubs and diagnostics (untyped isolated nodes, ignored self-loops).

---

## Testing

```bash
python3 -m pytest tests
```

The suite checks all 16 metrics on $G_{ref}$ (`tests/test_baseline.ttl`) within $\varepsilon = 10^{-5}$, the projection example from the paper (`tests/projection_example.ttl`), the 13 edge-case graphs in `tests/edge-Case-validation/`, and the VoID/DQV export. It runs on every push via GitHub Actions.

---

## Reproducing the Results of the Paper

All commands are run from the repository root after installation. Timing results depend on hardware; the paper's measurements were taken on an Intel Core Ultra 5 225U (14 logical cores), 32 GB RAM, 1 TB NVMe SSD, Ubuntu 24.04.5 LTS, Python 3.12.3.

**1. Datasets**

```bash
python3 scripts/fetch_datasets.py
```

$G_{ref}$ and the edge cases are in `tests/`; the DBpedia Berlin sample (the Linked Data description of `dbr:Berlin`) is bundled in `examples/`. The script downloads the ORKG N-Triples dump into `data/` and verifies all files against `data/CHECKSUMS.sha256`. ORKG dumps are not versioned, so a newer dump will not match the checksum of the snapshot used in the paper (retrieved 2026-09-07). No preprocessing is applied to any dataset.

**2. Metric validation (validation table, edge cases)**

```bash
python3 -m pytest tests
python3 src/tags.py tests/test_baseline.ttl -o output/
```

**3. Synthetic scalability benchmark (measured and extrapolated tables, scalability figure)**

```bash
python3 benchmarks/benchmark.py synthetic --sizes 1000 10000 100000 1000000 --runs 5
```

Generates chain-like synthetic graphs (fixed seed 42), runs TAGS five times per size in separate processes, and reports mean time, SD, 95% confidence interval, peak RSS delta, the linear and log-log fits, extrapolations to 5M–50M triples, and `results/tags_scalability.png`. Raw per-run values are saved in `results/`.

**4. DBpedia Berlin and ORKG profiles and runtime**

```bash
python3 src/tags.py examples/DBpedia-mini-samples-Berlin.ttl -o output/
python3 benchmarks/benchmark.py file examples/DBpedia-mini-samples-Berlin.ttl --runs 5

python3 src/tags.py data/rdf-export-orkg.nt -f nt -o output/
python3 benchmarks/benchmark.py file data/rdf-export-orkg.nt -f nt --runs 5
```

**5. Sensitivity of $M_{13}$ to $\tau$**

```bash
python3 benchmarks/tau_sensitivity.py data/rdf-export-orkg.nt -f nt --taus 1 2 3 5 10 20
```

**6. Flat-NetworkX baseline and taxonomic-isolation ablation**

```bash
python3 benchmarks/flat_networkx_baseline.py tests/test_baseline.ttl
python3 benchmarks/flat_networkx_baseline.py examples/kg-sample_triples_3171.ttl --runs 5
```

Compares a single-pass NetworkX graph with `rdf:type` edges, the same graph after post-hoc removal of `rdf:type` edges, and TAGS.

---

## Example: DBpedia Berlin Sample

```bash
python3 src/tags.py examples/DBpedia-mini-samples-Berlin.ttl
```

| Metric                                    | Value   |
| :---------------------------------------- | :------ |
| Total Asserted Triples ($M_1$)            | 53,228  |
| Unique Entity Nodes ($M_2$)               | 41,208  |
| Structural Object Links ($M_3$)           | 41,207  |
| Taxonomic Type Assertions ($M_4$)         | 15      |
| Average Node Connection ($M_5$)           | 1.99995 |
| Degree Centrality Polarization ($M_{10}$) | 20,604  |
| Total Disconnected Components ($M_{11}$)  | 1       |

The file describes a single resource, so almost every triple has `dbr:Berlin` as subject or object: the structural graph is a star with `dbr:Berlin` as hub (degree 41,207) and $M_{10} = |V|/2$, the maximum for a connected graph. One self-loop is ignored.

---

## Citation

If you use TAGS in your research, please cite our paper (TBD) or the software via `CITATION.cff`.

## License

Code: MIT License (see `LICENSE`). The ORKG data is published under CC0 1.0 (Papers With Code–derived parts under CC BY-SA); DBpedia data under CC BY-SA 3.0 and GFDL.
