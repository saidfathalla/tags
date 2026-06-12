[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Build Status](https://github.com/saidfathalla/TAGS/actions/workflows/pytest.yml/badge.svg)](https://github.com/saidfathalla/TAGS/actions)
[![FAIR Principles](https://img.shields.io/badge/FAIR-Supported-brightgreen.svg)](https://www.go-fair.org/fair-principles/)
[![RDF/Semantic Web](https://img.shields.io/badge/Semantic-RDF-orange.svg)](https://www.w3.org/RDF/)

# TAGS: Topological Analysis of Graph Structure

**TAGS** (Topological Analysis of Graph Structure), an extended multi-pass graph profiling framework containing sixteen topological and semantic metrics designed specifically to decouple classification vocabularies from instance graph topologies. 

Unlike standard network profilers that treat all RDF triples as structural edges—leading to "semantic inflation"— TAGS isolates pure relational instance data to calculate meaningful topological metrics for quality assurance, index tuning, and database optimization.

## Key Features

* **Multi-Pass Decoupling Architecture:** Isolates abstract taxonomic classifications (e.g., `rdf:type` or provenance assertions) from the underlying instance-level adjacency map. This filters structural noise and protects the mathematical validity of downstream network macro-properties against taxonomic inflation.
* **16 Topological Graph Diagnostics:** Computes a comprehensive suite of structural metrics—spanning sparsity profiles, connectivity transitivity, and fragmentation analysis—serving as a quantitative, machine-actionable instrumentation layer for dataset validation.
* **FAIR Data & Provenance Generation:** Automatically generates and serializes machine-reusable metadata profiles compliant with W3C VoID standards, embedding structural graph characteristics directly into the data lifecycle to maximize downstream discoverability and reproducibility.
* **Systems & Storage Optimization Engine:** Translates topological indicators (such as Degree Centrality Polarization and Class Imbalance Entropy) into actionable performance tuning primitives for physical triplestore caching, cost-based SPARQL query planning, and join-ordering acceleration.
* **Empirical Scientometric Utility:** Recovers genuine scientific relationships, collaboration networks, and dataset cross-linkages in large-scale scholarly knowledge graphs (SKGs), ensuring that empirical indicators computed for research evaluation remain statistically robust and free from ingestion artifacts.


## Installation

### Prerequisites
* Python 3.8+
* `pip` package manager
* Virtual environment framework (`venv` or `conda`, recommended)

### Core Dependencies
The pipeline engine automatically manages or builds upon the following foundational semantic and analytical runtimes:
* **`rdflib`**: For core W3C RDF parsing, graph manipulation, and Turtle serialization.
* **`numpy`**: For optimized array indexing and matrix computation within topology loops.
* **`matplotlib`** (Optional): For rendering high-impact matrix co-occurrence and class density visualizations in headless environments.

### Install dependencies:
We recommend using a virtual environment.

   ```bash
	pip install -r requirements.txt
   ```

### Usage
TAGS is designed as a command-line tool. Run the profiler by pointing it to your RDF Turtle (.ttl) file. 
- **Default output:** By default, the pipeline automatically resolves an absolute path relative to the script location and safely routes all outputs directly to `../output/`:

   ```bash
	python3 tags.py ./examples/kg-sample-1.ttl 
   ```
- **Custom Output:** To explicitly direct all generated payloads, visualizations, and summary files into a targeted storage destination, use the `-o` or `--output-dir` parameter:

   ```bash
  python3 tags.py path/to/your_dataset.ttl -o /path/to/custom_output/
   ```
 - **Help Configuration Options:** To view the command-line interface helper configurations and flags, run:
  
  	```bash
  	python3 tags.py --help
   ```
   
   

 
### Outputs
Upon compilation, the TAGS engine writes three unified output layers to your chosen output directory:

* Terminal Dashboard: A structurally aligned terminal printout mapping out calculated values for all 16 indicators alongside top discovered high-degree topological hubs.

* W3C VoID Metadata (`*_void.ttl`): A fully compliant, machine-actionable Turtle semantic file indexing distinct nodes, subject/object properties, and sub-class partitions for catalog ingestion.

* Visual Analytics Dashboard (`*_dashboard.html`): A responsive, self-contained HTML report embedding Base64-encoded visual frameworks, including the Dynamic Predicate Co-occurrence Matrix and Taxonomic Class Density Profiles. 


## Testing & Quality Assurance

This project utilizes `pytest` to ensure structural analysis metrics remain consistent across updates. We maintain a CI/CD pipeline using GitHub Actions to validate code integrity on every push automatically.

``bash
pip install pytest
python3 -m pytest
```
The test suite validates the core `analyze_knowledge_graph` logic against a synthetic graph to ensure parsing accuracy and stability of metric computation. The following figure shows the results of the baseline test graph.
<img width="1104" height="710" alt="image" src="https://github.com/user-attachments/assets/7a99bce7-67cd-4a56-8ce2-5256c436f642" />

### Running Tests Locally
We recommend running tests before submitting changes to ensure local logic parity. Ensure you have installed the development dependencies:

```bash
pip install -r requirements.txt
python3 -m pytest
```
The test suite validates the core analyze_knowledge_graph logic against a synthetic graph to ensure parsing accuracy and stability of metric computation. 

   
### Citation
If you use TAGS in your research, please cite our paper:

TBD.

### License
Distributed under the MIT License. See the `LICENSE` file in the root directory for more information.


