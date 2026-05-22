import pytest
import os
from src.tags import analyze_knowledge_graph

def test_analyze_graph_returns_results():
    """Verify that a minimal RDF turtle file parses correctly."""
    # Create a minimal test file
    test_ttl = "test_data.ttl"
    with open(test_ttl, "w") as f:
        f.write("@prefix ex: <http://example.org/> .\n")
        f.write("ex:Subject ex:predicate ex:Object .")
    
    # Run analysis
    results = analyze_knowledge_graph(test_ttl)
    
    # Clean up
    if os.path.exists(test_ttl):
        os.remove(test_ttl)
    
    # Assertions
    assert results is not None
    assert results["raw_counts"]["triples"] == 1
    assert "metrics" in results
