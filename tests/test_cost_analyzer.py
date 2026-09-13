# tests/test_cost_analyzer.py
# Stage 2: Cost Analyzer Validation Tests
#
# Run from project root:
#   python -m tests.test_cost_analyzer

import sys
import os

# Ensure project root is on Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cost_analyzer import load_resources, find_underutilized, CPU_THRESHOLD, MEM_THRESHOLD


def test_load_resources():
    """Verify that cloud resources are loaded with correct types."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(project_root, "data", "cloud_resources.csv")

    resources = load_resources(csv_path)
    assert len(resources) == 12, f"Expected 12 resources, got {len(resources)}"

    for r in resources:
        assert isinstance(r["resource_name"], str)
        assert isinstance(r["resource_type"], str)
        assert isinstance(r["monthly_cost"], float)
        assert isinstance(r["avg_cpu_percent"], float)
        assert isinstance(r["avg_memory_percent"], float)
        assert isinstance(r["monthly_hours"], float)
        assert r["monthly_cost"] > 0
        assert 0 <= r["avg_cpu_percent"] <= 100
        assert 0 <= r["avg_memory_percent"] <= 100
    print("  [OK] Load resources data integrity")


def test_find_underutilized_logic():
    """Verify underutilized detection: BOTH CPU < threshold AND Mem < threshold."""
    sample = [
        {"resource_name": "both-low",  "avg_cpu_percent": 10.0, "avg_memory_percent": 15.0},
        {"resource_name": "cpu-high",  "avg_cpu_percent": 25.0, "avg_memory_percent": 15.0},
        {"resource_name": "mem-high",  "avg_cpu_percent": 10.0, "avg_memory_percent": 35.0},
        {"resource_name": "both-high", "avg_cpu_percent": 50.0, "avg_memory_percent": 60.0},
    ]
    flagged = find_underutilized(sample, cpu_thresh=20.0, mem_thresh=30.0)
    assert len(flagged) == 1
    assert flagged[0]["resource_name"] == "both-low"
    print("  [OK] Underutilized filtering logic")


def test_threshold_boundaries():
    """Verify strict inequality (<) at threshold boundaries."""
    sample = [
        {"resource_name": "exact-cpu", "avg_cpu_percent": 20.0, "avg_memory_percent": 10.0},
        {"resource_name": "exact-mem", "avg_cpu_percent": 10.0, "avg_memory_percent": 30.0},
        {"resource_name": "just-below", "avg_cpu_percent": 19.9, "avg_memory_percent": 29.9},
    ]
    flagged = find_underutilized(sample, cpu_thresh=20.0, mem_thresh=30.0)
    assert len(flagged) == 1
    assert flagged[0]["resource_name"] == "just-below"
    print("  [OK] Threshold boundary behavior")


def test_live_dataset_summary():
    """Verify Stage 2 analysis on live dataset."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(project_root, "data", "cloud_resources.csv")

    resources = load_resources(csv_path)
    flagged = find_underutilized(resources)

    assert len(flagged) == 7, f"Expected 7 underutilized resources, got {len(flagged)}"
    total_cost = round(sum(r["monthly_cost"] for r in resources), 2)
    assert total_cost == 1823.85, f"Expected $1823.85, got {total_cost}"
    print("  [OK] Live dataset Stage 2 summary checks")


def main():
    print()
    print("=" * 50)
    print("  Stage 2 — Cost Analyzer Validation Tests")
    print("=" * 50)

    test_load_resources()
    test_find_underutilized_logic()
    test_threshold_boundaries()
    test_live_dataset_summary()

    print()
    print("  All Stage 2 tests passed.")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
