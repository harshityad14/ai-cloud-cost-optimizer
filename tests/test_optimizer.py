# tests/test_optimizer.py
# Basic validation tests for the Stage 3 optimisation engine.
# Uses only assert statements — no external test framework required.
#
# Run from the project root:
#   python -m tests.test_optimizer

import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.optimizer import (
    calculate_required_resources,
    calculate_monthly_cost,
    calculate_savings,
    find_best_candidate,
    load_catalog,
    generate_recommendations,
    get_current_resource_cost,
)
from src.cost_analyzer import load_resources


def test_monthly_cost_calculation():
    """Verify: monthly_cost = hourly_cost × monthly_hours."""
    assert calculate_monthly_cost(0.10, 730) == 73.0
    assert calculate_monthly_cost(0.0, 730) == 0.0
    assert calculate_monthly_cost(0.50, 200) == 100.0
    print("  [OK] Monthly cost calculation")


def test_savings_calculation():
    """Verify absolute and percentage savings."""
    abs_sav, pct_sav = calculate_savings(100.0, 60.0)
    assert abs_sav == 40.0
    assert abs(pct_sav - 40.0) < 0.01
    print("  [OK] Savings calculation")


def test_percentage_savings_zero_current():
    """Verify no division-by-zero when current cost is 0."""
    abs_sav, pct_sav = calculate_savings(0.0, 0.0)
    assert abs_sav == 0.0
    assert pct_sav == 0.0
    print("  [OK] Percentage savings with zero current cost")


def test_required_resources():
    """Verify CPU/memory sizing with safety margin."""
    resource = {
        "avg_cpu_percent": 10.0,  # 10% of 4 vCPU = 0.4 actual
        "avg_memory_percent": 20.0,  # 20% of 16 GB = 3.2 actual
        "vcpu": 4,
        "memory_gb": 16,
    }
    req_cpu, req_mem = calculate_required_resources(resource, safety_margin=1.5)
    # Expected: 0.4 × 1.5 = 0.6 vCPU,  3.2 × 1.5 = 4.8 GB
    assert abs(req_cpu - 0.6) < 0.001, f"Expected 0.6, got {req_cpu}"
    assert abs(req_mem - 4.8) < 0.001, f"Expected 4.8, got {req_mem}"
    print("  [OK] Required resources calculation")


def test_candidate_selection_finds_cheaper():
    """Verify that a valid cheaper candidate is selected."""
    resource = {
        "resource_name": "test-vm",
        "resource_type": "vm_instance",
        "monthly_cost": 145.50,
        "avg_cpu_percent": 10.0,
        "avg_memory_percent": 15.0,
        "monthly_hours": 730,
        "vcpu": 4,
        "memory_gb": 16,
    }
    catalog = [
        {"config_name": "big",   "resource_type": "vm_instance",
         "vcpu": 4,  "memory_gb": 16, "hourly_cost": 0.20},
        {"config_name": "small", "resource_type": "vm_instance",
         "vcpu": 1,  "memory_gb": 4,  "hourly_cost": 0.04},
    ]
    best = find_best_candidate(resource, catalog, safety_margin=1.5)
    assert best is not None, "Expected a valid candidate"
    assert best["config_name"] == "small"
    print("  [OK] Candidate selection (cheaper found)")


def test_candidate_selection_no_cheaper():
    """Verify that None is returned when no cheaper candidate exists."""
    resource = {
        "resource_name": "cheap-vm",
        "resource_type": "vm_instance",
        "monthly_cost": 5.00,  # already very cheap
        "avg_cpu_percent": 10.0,
        "avg_memory_percent": 15.0,
        "monthly_hours": 730,
        "vcpu": 1,
        "memory_gb": 2,
    }
    catalog = [
        {"config_name": "only-option", "resource_type": "vm_instance",
         "vcpu": 1, "memory_gb": 2, "hourly_cost": 0.05},
    ]
    # 0.05 × 730 = 36.50 > 5.00 → no saving
    best = find_best_candidate(resource, catalog, safety_margin=1.5)
    assert best is None, "Expected None when no cheaper candidate exists"
    print("  [OK] Candidate selection (no cheaper candidate)")


def test_candidate_selection_wrong_type():
    """Verify that candidates of a different resource_type are ignored."""
    resource = {
        "resource_name": "my-db",
        "resource_type": "cloud_sql",
        "monthly_cost": 300.00,
        "avg_cpu_percent": 10.0,
        "avg_memory_percent": 10.0,
        "monthly_hours": 730,
        "vcpu": 4,
        "memory_gb": 15,
    }
    catalog = [
        {"config_name": "vm-tiny", "resource_type": "vm_instance",
         "vcpu": 1, "memory_gb": 4, "hourly_cost": 0.01},
    ]
    best = find_best_candidate(resource, catalog, safety_margin=1.5)
    assert best is None, "Should not match a vm_instance to a cloud_sql resource"
    print("  [OK] Candidate selection (type mismatch ignored)")


# ---------------------------------------------------------------------------
# Regression tests for issues found in technical review
# ---------------------------------------------------------------------------
def test_no_identical_spec_recommendation():
    """Regression: a candidate with identical vCPU AND memory must be rejected.

    This catches the load-balancer-01 issue where the same specs at a lower
    price were incorrectly recommended as a "downsize."
    """
    resource = {
        "resource_name": "test-lb",
        "resource_type": "load_balancer",
        "monthly_cost": 50.00,
        "avg_cpu_percent": 15.0,
        "avg_memory_percent": 10.0,
        "monthly_hours": 730,
        "vcpu": 1,
        "memory_gb": 2,
    }
    catalog = [
        # Same specs, cheaper price — must NOT be recommended
        {"config_name": "lb-cheap", "resource_type": "load_balancer",
         "vcpu": 1, "memory_gb": 2, "hourly_cost": 0.01},
    ]
    best = find_best_candidate(resource, catalog, safety_margin=1.5)
    assert best is None, "Must not recommend identical specs with only a lower price"
    print("  [OK] No identical-spec recommendation")


def test_consistent_pricing_model():
    """Regression: savings must be correct when both costs use the same catalog.

    Simulates the fixed pricing model where current_cost = hourly × hours.
    """
    hourly_current = 0.1344
    hourly_smaller = 0.0672
    monthly_hours = 730
    current_cost = hourly_current * monthly_hours  # Derived from catalog

    resource = {
        "resource_name": "test-vm",
        "resource_type": "vm_instance",
        "monthly_cost": current_cost,
        "avg_cpu_percent": 10.0,
        "avg_memory_percent": 15.0,
        "monthly_hours": monthly_hours,
        "vcpu": 4,
        "memory_gb": 16,
    }
    catalog = [
        {"config_name": "smaller", "resource_type": "vm_instance",
         "vcpu": 2, "memory_gb": 8, "hourly_cost": hourly_smaller},
        # Same-size entry must be excluded by the identical-spec guard
        {"config_name": "same-size", "resource_type": "vm_instance",
         "vcpu": 4, "memory_gb": 16, "hourly_cost": hourly_current},
    ]
    best = find_best_candidate(resource, catalog, safety_margin=1.5)
    assert best is not None, "Expected a valid smaller candidate"
    assert best["config_name"] == "smaller"

    # Both costs derived from same model → savings should be exactly 50%
    rec_cost = calculate_monthly_cost(best["hourly_cost"], monthly_hours)
    abs_sav, pct_sav = calculate_savings(current_cost, rec_cost)
    assert abs_sav > 0, "Expected positive savings"
    assert abs(pct_sav - 50.0) < 0.01, f"Expected ~50%, got {pct_sav}"
    print("  [OK] Consistent pricing model")


def test_live_dataset_no_identical_spec():
    """Regression: verify the actual dataset produces no identical-spec recs.

    Loads the real project data files and confirms every recommendation has
    at least one spec (vCPU or memory) that differs from the current resource.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_path = os.path.join(project_root, "data", "cloud_resources.csv")
    catalog_path   = os.path.join(project_root, "data", "resource_catalog.csv")

    resources = load_resources(resources_path)
    catalog   = load_catalog(catalog_path)
    _, recommendations = generate_recommendations(resources, catalog)

    for rec in recommendations:
        same_vcpu = rec["recommended_vcpu"] == rec["current_vcpu"]
        same_mem  = rec["recommended_memory_gb"] == rec["current_memory_gb"]
        assert not (same_vcpu and same_mem), (
            f"Identical-spec recommendation found for {rec['current_resource']}: "
            f"{rec['recommended_config']} has same vCPU and memory"
        )
    print("  [OK] Live dataset has no identical-spec recommendations")


def test_catalog_no_duplicate_specifications():
    """Regression: synthetic catalog must not contain duplicate-equivalent configurations."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog_path = os.path.join(project_root, "data", "resource_catalog.csv")
    catalog = load_catalog(catalog_path)

    seen_specs = set()
    for entry in catalog:
        spec_key = (entry["resource_type"], entry["vcpu"], entry["memory_gb"])
        assert spec_key not in seen_specs, (
            f"Duplicate configuration found in catalog for specs {spec_key}: {entry['config_name']}"
        )
        seen_specs.add(spec_key)
    print("  [OK] Synthetic catalog has no duplicate-equivalent configurations")


def test_cloud_resources_pricing_matches_catalog():
    """Regression: cloud_resources.csv costs and specs must align with catalog rates."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_path = os.path.join(project_root, "data", "cloud_resources.csv")
    catalog_path = os.path.join(project_root, "data", "resource_catalog.csv")

    resources = load_resources(resources_path)
    catalog = load_catalog(catalog_path)
    catalog_by_name = {c["config_name"]: c for c in catalog}

    for r in resources:
        config_name = r.get("current_config")
        assert config_name in catalog_by_name, (
            f"Resource {r['resource_name']} has unknown current_config '{config_name}'"
        )
        cat_entry = catalog_by_name[config_name]
        assert r["vcpu"] == cat_entry["vcpu"], (
            f"vCPU mismatch for {r['resource_name']}: {r['vcpu']} vs {cat_entry['vcpu']}"
        )
        assert r["memory_gb"] == cat_entry["memory_gb"], (
            f"Memory mismatch for {r['resource_name']}: {r['memory_gb']} vs {cat_entry['memory_gb']}"
        )
        expected_monthly = calculate_monthly_cost(cat_entry["hourly_cost"], r["monthly_hours"])
        assert r["monthly_cost"] == expected_monthly, (
            f"Monthly cost mismatch for {r['resource_name']}: {r['monthly_cost']} vs expected {expected_monthly}"
        )
    print("  [OK] Cloud resources CSV specs and pricing match catalog exactly")


def test_optimizer_derives_current_and_recommended_from_same_catalog():
    """Regression: optimizer derives both current and recommended costs from the catalog."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_path = os.path.join(project_root, "data", "cloud_resources.csv")
    catalog_path = os.path.join(project_root, "data", "resource_catalog.csv")

    resources = load_resources(resources_path)
    catalog = load_catalog(catalog_path)
    catalog_by_name = {c["config_name"]: c for c in catalog}

    _, recommendations = generate_recommendations(resources, catalog)
    resources_by_name = {r["resource_name"]: r for r in resources}

    for rec in recommendations:
        res = resources_by_name[rec["current_resource"]]
        current_cat = catalog_by_name[res["current_config"]]
        rec_cat = catalog_by_name[rec["recommended_config"]]

        expected_current_cost = calculate_monthly_cost(current_cat["hourly_cost"], res["monthly_hours"])
        expected_rec_cost = calculate_monthly_cost(rec_cat["hourly_cost"], res["monthly_hours"])
        expected_savings = round(expected_current_cost - expected_rec_cost, 2)

        assert rec["current_monthly_cost"] == expected_current_cost, (
            f"Current cost mismatch for {rec['current_resource']}"
        )
        assert rec["recommended_monthly_cost"] == expected_rec_cost, (
            f"Recommended cost mismatch for {rec['current_resource']}"
        )
        assert rec["estimated_monthly_savings"] == expected_savings, (
            f"Savings mismatch for {rec['current_resource']}"
        )
        assert rec["current_monthly_cost"] > rec["recommended_monthly_cost"], (
            f"Recommended configuration must be cheaper for {rec['current_resource']}"
        )
    print("  [OK] Optimizer derives current and recommended costs from same catalog")


def test_documentation_example_matches_optimizer():
    """Regression: documented recommendation in docs/stage-3-optimization.md matches optimizer output."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    resources_path = os.path.join(project_root, "data", "cloud_resources.csv")
    catalog_path = os.path.join(project_root, "data", "resource_catalog.csv")
    doc_path = os.path.join(project_root, "docs", "stage-3-optimization.md")

    resources = load_resources(resources_path)
    catalog = load_catalog(catalog_path)
    _, recommendations = generate_recommendations(resources, catalog)

    api_backend_rec = next((r for r in recommendations if r["current_resource"] == "api-backend-02"), None)
    assert api_backend_rec is not None, "Expected recommendation for api-backend-02"

    with open(doc_path, "r", encoding="utf-8") as f:
        doc_content = f.read()

    # Check key documented values in markdown
    assert "Resource          : api-backend-02" in doc_content
    assert f"Current cost      : $  {api_backend_rec['current_monthly_cost']:>6.2f} /month" in doc_content
    assert f"Recommended config: {api_backend_rec['recommended_config']}" in doc_content
    assert f"Recommended cost  : $   {api_backend_rec['recommended_monthly_cost']:>5.2f} /month" in doc_content
    assert f"Estimated savings : $  {api_backend_rec['estimated_monthly_savings']:>6.2f} /month  ({api_backend_rec['estimated_savings_percent']:.1f}%)" in doc_content
    assert api_backend_rec["reason"] in doc_content
    print("  [OK] Stage 3 documentation example matches optimizer output exactly")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------
def main():
    print()
    print("=" * 50)
    print("  Stage 3 — Optimiser Validation Tests")
    print("=" * 50)

    test_monthly_cost_calculation()
    test_savings_calculation()
    test_percentage_savings_zero_current()
    test_required_resources()
    test_candidate_selection_finds_cheaper()
    test_candidate_selection_no_cheaper()
    test_candidate_selection_wrong_type()
    test_no_identical_spec_recommendation()
    test_consistent_pricing_model()
    test_live_dataset_no_identical_spec()
    test_catalog_no_duplicate_specifications()
    test_cloud_resources_pricing_matches_catalog()
    test_optimizer_derives_current_and_recommended_from_same_catalog()
    test_documentation_example_matches_optimizer()

    print()
    print("  All tests passed.")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()
