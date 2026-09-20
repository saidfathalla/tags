#!/usr/bin/env python3
"""
benchmark_tags.py
-----------------
Automated benchmarking suite for the TAGS framework.
Measures execution time, peak RSS memory consumption, and per-triple throughput 
across scaled synthetic RDF graph sizes.

Uses Process Isolation (multiprocessing) to guarantee memory cleanup between runs
and gracefully intercept OS Out-Of-Memory (OOM / SIGKILL) terminations.
"""

import os
import sys
import time
import psutil
import numpy as np
import matplotlib.pyplot as plt
from multiprocessing import Process, Queue
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

# Import core TAGS entry point
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from src.tags import analyze_knowledge_graph
except ImportError:
    print("[Error] Could not import 'analyze_knowledge_graph' from 'src/tags.py'.")
    print("Ensure script is executed from project root or test directory.")
    sys.exit(1)


# ==========================================
# 1. Dataset Generation Helper
# ==========================================
def generate_synthetic_turtle(num_triples: int, output_file: str):
    """
    Generates a synthetic RDF Turtle dataset with a specified number of triples.
    """
    ex = Namespace("http://example.org/tags/benchmark/")
    g = Graph()
    g.bind("ex", ex)
    
    num_entities = max(1, num_triples // 5)
    for i in range(num_triples):
        subj = ex[f"entity_{i % num_entities}"]
        pred = ex[f"property_{i % 10}"]
        obj = ex[f"value_{i}"]
        g.add((subj, pred, obj))
        
        # Add lightweight schema assertions to simulate dual-pass separation
        if i % 10 == 0:
            g.add((subj, RDF.type, ex[f"Class_{i % 5}"]))
            
    g.serialize(destination=output_file, format="turtle")


# ==========================================
# 2. Worker Process (Isolated Memory Space)
# ==========================================
def worker_benchmark(scale: int, tmp_dir: str, result_queue: Queue):
    """
    Runs in a dedicated process to ensure 100% memory reclamation upon termination.
    """
    turtle_path = os.path.join(tmp_dir, f"data_{scale}.ttl")
    process = psutil.Process(os.getpid())

    try:
        print(f"  [Process {process.pid}] Generating {scale:,} synthetic triples...")
        generate_synthetic_turtle(scale, turtle_path)

        print(f"  [Process {process.pid}] Executing core dual-pass matrix projection...")
        mem_before = process.memory_info().rss / (1024 * 1024)
        start_time = time.perf_counter()

        # Execute core framework pipeline
        analyze_knowledge_graph(turtle_path)

        elapsed_time = time.perf_counter() - start_time
        mem_after = process.memory_info().rss / (1024 * 1024)
        peak_memory = max(mem_after, mem_before)
        normalized_time_us = (elapsed_time / scale) * 1e6  # Microseconds per triple

        result_queue.put({
            'triples': scale,
            'time_s': elapsed_time,
            'peak_ram_mb': peak_memory,
            'throughput_us': normalized_time_us,
            'status': 'Completed'
        })

    except MemoryError:
        result_queue.put({
            'triples': scale,
            'time_s': None,
            'peak_ram_mb': None,
            'throughput_us': None,
            'status': 'MemoryError'
        })
    except Exception as e:
        result_queue.put({
            'triples': scale,
            'time_s': None,
            'peak_ram_mb': None,
            'throughput_us': None,
            'status': f'Error: {str(e)}'
        })
    finally:
        if os.path.exists(turtle_path):
            os.remove(turtle_path)


# ==========================================
# 3. Main Benchmark Orchestrator
# ==========================================
def run_benchmarks():
    # Target scale points requested
    scale_points = [1000, 10000, 100000, 1000000]
    
    results = []
    tmp_dir = "tmp_benchmark_data"
    os.makedirs(tmp_dir, exist_ok=True)

    print("==========================================================================")
    print("        TAGS Framework Scalability Suite (Isolated Process Execution)      ")
    print("==========================================================================")

    for scale in scale_points:
        print(f"\nProfiling TAGS on scale point: {scale:,} triples...")
        
        result_queue = Queue()
        p = Process(target=worker_benchmark, args=(scale, tmp_dir, result_queue))
        p.start()
        p.join()  # Block until the child process terminates

        # Check process exit codes
        if p.exitcode == -9 or p.exitcode == 137:
            # -9 / 137 represents SIGKILL sent by Linux OOM Killer
            print(f"  [OOM INTERCEPTED] Scale point {scale:,} exceeded system RAM limits.")
            print(f"                    Child process killed by OS (SIGKILL/137). Script continuing safely.")
            results.append({
                'triples': scale,
                'time_s': None,
                'peak_ram_mb': None,
                'throughput_us': None,
                'status': 'OOM Killed (OS Limit)'
            })
        elif p.exitcode != 0:
            print(f"  [FAILED] Process exited with non-zero status code: {p.exitcode}")
            results.append({
                'triples': scale,
                'time_s': None,
                'peak_ram_mb': None,
                'throughput_us': None,
                'status': f'Failed (Exit Code {p.exitcode})'
            })
        else:
            res = result_queue.get()
            print(f"  [SUCCESS] Time: {res['time_s']:.3f}s | Peak RAM: {res['peak_ram_mb']:.2f} MB | {res['throughput_us']:.2f} µs/triple")
            results.append(res)

    # Cleanup temp directory
    if os.path.exists(tmp_dir):
        os.rmdir(tmp_dir)

    # ==========================================
    # 4. Results Reporting & Linear Regression
    # ==========================================
    completed = [r for r in results if r['status'] == 'Completed']
    
    if not completed:
        print("\n[Error] No benchmark scale points completed successfully.")
        return

    x_data = np.array([r['triples'] for r in completed])
    y_time = np.array([r['time_s'] for r in completed])

    # Ordinary Least Squares Regression T(|T|) = a * |T| + b
    if len(completed) > 1:
        slope, intercept = np.polyfit(x_data, y_time, 1)
        y_pred = slope * x_data + intercept
        ss_res = np.sum((y_time - y_pred) ** 2)
        ss_tot = np.sum((y_time - np.mean(y_time)) ** 2)
        r2_score = 1 - (ss_res / ss_tot) if ss_tot != 0 else 1.0
    else:
        slope, intercept, r2_score = 0.0, 0.0, 0.0

    print("\n" + "="*85)
    print("                           SUMMARY BENCHMARK RESULTS                      ")
    print("="*85)
    print(f"{'Triples (|T|)':>15} | {'Time (s)':>10} | {'Peak RAM (MB)':>15} | {'Overhead (µs/triple)':>22} | {'Status':<20}")
    print("-" * 85)
    for r in results:
        if r['status'] == 'Completed':
            print(f"{r['triples']:>15,} | {r['time_s']:>10.3f} | {r['peak_ram_mb']:>15.2f} | {r['throughput_us']:>22.2f} | {r['status']:<20}")
        else:
            print(f"{r['triples']:>15,} | {'N/A':>10} | {'N/A':>15} | {'N/A':>22} | {r['status']:<20}")
    print("-" * 85)
    if len(completed) > 1:
        print(f"Linear Fit Equation : T(|T|) = {slope:.7e} * |T| + {intercept:.3f}")
        print(f"Coefficient of Det. : R² = {r2_score:.4f}")
    print("="*85)

    # ==========================================
    # 5. Diagnostic Plot Generation
    # ==========================================
    if len(completed) > 1:
        generate_plot(completed, x_data, y_time, slope, intercept, r2_score)


def generate_plot(completed, x_data, y_time, slope, intercept, r2_score):
    """
    Generates and saves the tags_scalability.png plot (single-panel execution time scalability).
    """
    # 1. Transform empirical data to Log10 space for accurate log-log regression fitting
    log_x = np.log10(x_data)
    log_y = np.log10(y_time)

    # 2. Fit linear model in log-log space: log10(y) = slope * log10(x) + intercept
    slope_log, intercept_log = np.polyfit(log_x, log_y, 1)

    # Compute R^2 in log space to treat all scale points with equal relative weight
    log_y_pred = slope_log * log_x + intercept_log
    ss_res = np.sum((log_y - log_y_pred) ** 2)
    ss_tot = np.sum((log_y - np.mean(log_y)) ** 2)
    r2_log = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 1.0

    # 3. Create single-panel figure
    plt.figure(figsize=(7, 5))

    # Plot empirical measurement points
    plt.plot(x_data, y_time, 'bo-', linewidth=2, markersize=7, label='Empirical Measured Time')

    # Generate continuous domain line for smooth regression curve
    log_x_line = np.linspace(min(log_x), max(log_x), 200)
    log_y_line = slope_log * log_x_line + intercept_log
    
    x_line = 10**log_x_line
    y_line = 10**log_y_line

    plt.plot(x_line, y_line, 'r--', linewidth=1.8, 
             label=f'Log-Log Linear Fit ($R^2 = {r2_log:.4f}$)')

    # Chart formatting
    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Dataset Size (|T| Triples)', fontsize=11, fontweight='bold')
    plt.ylabel('Execution Time (seconds)', fontsize=11, fontweight='bold')
    plt.title('TAGS Execution Time Scalability', fontsize=12, fontweight='bold', pad=12)
    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.legend(loc='upper left', frameon=True)

    plt.tight_layout()
    output_plot = "tags_scalability.png"
    plt.savefig(output_plot, dpi=300)
    print(f"\n[Plot Saved] Scalability plot saved successfully as '{output_plot}'.")


if __name__ == "__main__":
    run_benchmarks()
