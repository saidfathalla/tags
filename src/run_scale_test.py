import time
import os
import sys
import psutil

# Import your main execution function
try:
    from tags import main as profile_graph
except ImportError:
    print("Error: Could not locate 'main()' function inside tags.py.")
    sys.exit(1)

def test_scale():
    # Enforce terminal argument check
    if len(sys.argv) < 2:
        print("Usage: python3 run_scale_test.py <path_to_rdf_file.ttl>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
        
    print(f"=== TAGS SCALE TEST: {os.path.basename(file_path)} ===")
    
    # 1. Capture initial baseline memory profile
    process = psutil.Process(os.getpid())
    mem_before = process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
    
    # 2. Execute pipeline and time it
    start_time = time.time()
    try:
        # Simply execute your main function; it will read from sys.argv natively
        metrics = profile_graph()
    except Exception as e:
        print(f"Pipeline execution failed: {e}")
        return
    end_time = time.time()
    
    # 3. Capture post-execution memory profile
    mem_after = process.memory_info().rss / (1024 * 1024)   # Convert bytes to MB
    
    # 4. Calculate performance deltas
    execution_time = end_time - start_time
    memory_used = mem_after - mem_before
    
    # 5. Output performance logs
    print("\n[PERFORMANCE METRICS]")
    print(f"Total Processing Time : {execution_time:.4f} seconds")
    print(f"Peak RAM Consumption  : {memory_used:.2f} MB")
    print("-" * 40)
    
    # Note: If your main() prints directly to terminal instead of returning a dict,
    # the metrics will already display right above this performance summary block!
    if isinstance(metrics, dict):
        print("\n[GRAPH TOPOLOGY RESULTS]")
        target_metrics = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M8', 'M11', 'M14', 'M15', 'M16']
        for metric_id in target_metrics:
            if metric_id in metrics:
                print(f" │ {metric_id:<4} │ {metrics[metric_id]:<30} │")

if __name__ == "__main__":
    test_scale()
