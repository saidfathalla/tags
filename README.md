# TAGS: Topological Analysis of Graph Structure

**TAGS** is an automated, two-pass profiling framework designed to decouple taxonomic classification schemas from core structural topologies in Scholarly Knowledge Graphs (SKGs). 

Unlike standard network profilers that treat all RDF triples as structural edges—leading to "semantic inflation"—TAGS isolates pure relational instance data to calculate meaningful topological metrics for quality assurance, index tuning, and database optimization.

## Key Features
* **Two-Pass Architecture:** Separates abstract ontological classifications (e.g., `rdf:type`) from instance relationships, ensuring accurate structural metrics.
* **16 Topological Metrics:** Computes a comprehensive suite of metrics ranging from graph density to structural fragmentation.
* **FAIR Data Generation:** Automatically exports machine-reusable metadata compliant with W3C VoID standards.
* **Database Tuning Engine:** Provides actionable insights for SPARQL index optimization based on graph polarization.


## Installation

### Prerequisites
* Python 3.8+
* `pip` package manager

### Steps
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/your-username/TAGS.git](https://github.com/your-username/TAGS.git)
   cd TAGS
   ```
   
### Install dependencies:
We recommend using a virtual environment.

   ```bash
	pip install -r requirements.txt
   ```

### Usage
TAGS is designed as a command-line tool. Run the profiler by pointing it to your RDF Turtle (.ttl) file:

   ```bash
	python3 kgstats-fair.py hkg_subgraph1_triples_56.ttl
   ```
   
### Outputs
Upon execution, TAGS generates three distinct outputs:

* Terminal Dashboard: A real-time overview of the 16 calculated metrics.

* W3C VoID Metadata: A machine-readable file (void_stats.ttl) that can be ingested into data catalogs to describe the graph’s structural properties.

* Visual Analytics: If matplotlib is installed, TAGS generates summary plots (e.g., class distribution histograms) for quick structural visual assessment. 
   
### Citation
If you use TAGS in your research, please cite our paper:

Said Fathalla. "TAGS: A Two-Pass Topological Profiling Framework for Scholarly Knowledge Graphs—Advanced Structural and Semantic Metrics for Quality Assurance in Metadata Repositories." (2026).

### License
Distributed under the MIT License. See LICENSE for more information.



