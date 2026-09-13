# src/optimizer.py
# AI Cloud Cost Optimizer — Stage 3: Rule-Based Optimization Engine
#
# Given the underutilized resources identified in Stage 2, this module finds
# cheaper resource configurations from a local catalog and produces
# right-sizing recommendations with estimated savings.
#
# IMPORTANT DISCLAIMERS:
#   - All data and pricing are SYNTHETIC / DEMONSTRATION values.
#   - The sizing heuristic is a simple, transparent rule — not a production
#     algorithm and not claimed to be novel or patentable.
#   - No real cloud resource is modified.  This stage produces
#     RECOMMENDATIONS ONLY.

import csv
import os

from src.cost_analyzer import load_resources, find_underutilized


# ---------------------------------------------------------------------------
# Configuration — Sizing & Safety Parameters
# ---------------------------------------------------------------------------
# SAFETY_MARGIN is a multiplier applied to observed average usage so that the
# recommended configuration has headroom for traffic spikes.
#
#   required_vcpu      = (avg_cpu% / 100) × current_vcpu × SAFETY_MARGIN
#   required_memory_gb = (avg_mem% / 100) × current_memory_gb × SAFETY_MARGIN
#
# Example: a 4-vCPU VM at 12% CPU → actual usage ≈ 0.48 vCPU
#          with 1.5× margin → need at least 0.72 vCPU
#
# A value of 1.5 means "50 % headroom above the observed average."
# This is a deliberately simple heuristic — real systems would analyse
# percentile distributions, burst patterns, and SLA requirements.
# ---------------------------------------------------------------------------
SAFETY_MARGIN = 1.5


# ---------------------------------------------------------------------------
# Catalog loader
# ---------------------------------------------------------------------------
def load_catalog(csv_path):
    """Load the resource configuration catalog from a CSV file.

    Returns a list of dicts, each with:
      - config_name   (str)   e.g. "e2-small"
      - resource_type (str)   e.g. "vm_instance"
      - vcpu          (float)
      - memory_gb     (float)
      - hourly_cost   (float)

    PRICING DISCLAIMER: All hourly_cost values are synthetic demonstration
    values and do NOT represent real GCP pricing.
    """
    catalog = []

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            catalog.append({
                "config_name":   row["config_name"].strip(),
                "resource_type": row["resource_type"].strip(),
                "vcpu":          float(row["vcpu"]),
                "memory_gb":     float(row["memory_gb"]),
                "hourly_cost":   float(row["hourly_cost"]),
            })

    return catalog


# ---------------------------------------------------------------------------
# Sizing calculations
# ---------------------------------------------------------------------------
def calculate_required_resources(resource, safety_margin=SAFETY_MARGIN):
    """Translate observed utilisation into minimum required specs.

    Assumptions (documented, not production-grade):
      1. avg_cpu_percent / 100 × current_vcpu  = average vCPU demand.
      2. avg_memory_percent / 100 × memory_gb   = average memory demand.
      3. Both are multiplied by safety_margin to provide spike headroom.
      4. This does NOT account for P99 peaks, burst, or time-of-day patterns.

    Returns (required_vcpu, required_memory_gb).
    """
    required_vcpu = (resource["avg_cpu_percent"] / 100.0) \
                    * resource["vcpu"] \
                    * safety_margin

    required_memory = (resource["avg_memory_percent"] / 100.0) \
                      * resource["memory_gb"] \
                      * safety_margin

    return required_vcpu, required_memory


def calculate_monthly_cost(hourly_cost, monthly_hours):
    """Monthly cost = hourly rate × hours running that month."""
    return round(hourly_cost * monthly_hours, 2)


def calculate_savings(current_cost, recommended_cost):
    """Return (absolute_savings, percentage_savings)."""
    absolute = round(current_cost - recommended_cost, 2)
    percentage = (absolute / current_cost * 100.0) if current_cost > 0 else 0.0
    return absolute, percentage


def get_current_resource_cost(resource, catalog=None):
    """Derive current resource monthly cost from the catalog if current_config is present.

    Falls back to resource['monthly_cost'] if no catalog or current_config is provided.
    """
    if catalog and "current_config" in resource:
        for entry in catalog:
            if entry["config_name"] == resource["current_config"]:
                return calculate_monthly_cost(entry["hourly_cost"], resource["monthly_hours"])
    return resource.get("monthly_cost", 0.0)


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------
def find_best_candidate(resource, catalog, safety_margin=SAFETY_MARGIN):
    """Find the cheapest catalog config that satisfies the resource's needs.

    Selection rules:
      1. Must be the same resource_type.
      2. Must have enough vCPU  (>= required after safety margin).
      3. Must have enough memory (>= required after safety margin).
      4. Must NOT have identical vCPU and memory to the current resource
         (identical specs with only a price difference is not a genuine
         downsize recommendation).
      5. Must NOT be the identical current configuration.
      6. Its monthly cost must be LOWER than the current monthly cost
         derived from the same catalog pricing model.
      7. Among all valid candidates, pick the one with the lowest hourly cost.

    Returns the matching catalog entry dict, or None if no cheaper candidate.
    """
    required_vcpu, required_memory = calculate_required_resources(
        resource, safety_margin
    )

    current_cost = get_current_resource_cost(resource, catalog)

    # Filter candidates by type, minimum specs, and exclude identical configs.
    # A candidate with the same vCPU and memory as the current resource is not
    # a genuine downsize — it would only reflect a pricing discrepancy.
    candidates = [
        c for c in catalog
        if c["resource_type"] == resource["resource_type"]
        and c["vcpu"] >= required_vcpu
        and c["memory_gb"] >= required_memory
        and not (c["vcpu"] == resource["vcpu"]
                 and c["memory_gb"] == resource["memory_gb"])
        and c["config_name"] != resource.get("current_config")
    ]

    if not candidates:
        return None

    # Sort ascending by hourly cost and pick the cheapest
    candidates.sort(key=lambda c: c["hourly_cost"])
    best = candidates[0]

    # Only recommend if it actually saves money
    recommended_monthly = calculate_monthly_cost(
        best["hourly_cost"], resource["monthly_hours"]
    )
    if recommended_monthly >= current_cost:
        return None

    return best


# ---------------------------------------------------------------------------
# Recommendation builder
# ---------------------------------------------------------------------------
def build_recommendation(resource, candidate, catalog=None):
    """Create a structured recommendation dict for one resource.

    Contains everything needed to understand the suggestion:
      - what the resource currently is and costs (derived from catalog)
      - what the recommended configuration is and would cost
      - the estimated savings (absolute and percentage)
      - a human-readable reason
    """
    current_cost = get_current_resource_cost(resource, catalog)
    recommended_monthly = calculate_monthly_cost(
        candidate["hourly_cost"], resource["monthly_hours"]
    )
    savings, savings_pct = calculate_savings(
        current_cost, recommended_monthly
    )

    return {
        "current_resource":          resource["resource_name"],
        "current_type":              resource["resource_type"],
        "current_vcpu":              resource["vcpu"],
        "current_memory_gb":         resource["memory_gb"],
        "current_monthly_cost":      current_cost,

        "recommended_config":        candidate["config_name"],
        "recommended_vcpu":          candidate["vcpu"],
        "recommended_memory_gb":     candidate["memory_gb"],
        "recommended_monthly_cost":  recommended_monthly,

        "estimated_monthly_savings": savings,
        "estimated_savings_percent": savings_pct,

        "reason": (
            f"Average CPU ({resource['avg_cpu_percent']}%) and memory "
            f"({resource['avg_memory_percent']}%) usage are both low.  "
            f"A {candidate['config_name']} ({candidate['vcpu']} vCPU, "
            f"{candidate['memory_gb']} GB) can handle the observed workload "
            f"with a {SAFETY_MARGIN}x safety margin."
        ),
    }


def generate_recommendations(resources, catalog, safety_margin=SAFETY_MARGIN):
    """Produce optimisation recommendations for all underutilized resources.

    Steps:
      1. Identify underutilized resources (Stage 2 logic).
      2. For each, find the best cheaper candidate from the catalog.
      3. Build a recommendation if a valid candidate exists.

    Returns (underutilized_list, recommendations_list).
    """
    underutilized = find_underutilized(resources)
    recommendations = []

    for resource in underutilized:
        # Skip resources that lack spec columns (shouldn't happen, but safe)
        if "vcpu" not in resource or "memory_gb" not in resource:
            continue

        candidate = find_best_candidate(resource, catalog, safety_margin)
        if candidate is not None:
            recommendations.append(build_recommendation(resource, candidate, catalog))

    return underutilized, recommendations


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------
def print_optimization_report(resources, underutilized, recommendations):
    """Print a readable optimisation report to the console."""

    total_cost = sum(r["monthly_cost"] for r in resources)

    print()
    print("=" * 70)
    print("  Stage 3: Resource Optimisation Report  (Synthetic Data)")
    print("=" * 70)

    # --- Overview ---
    print(f"  Total resources in dataset        : {len(resources)}")
    print(f"  Total current monthly cost        : ${total_cost:,.2f}")
    print(f"  Resources flagged as underutilized : {len(underutilized)}")
    print(f"  Resources with valid recommendations : {len(recommendations)}")
    print("-" * 70)

    if not recommendations:
        print("  No cheaper configurations found for the underutilized resources.")
        print("=" * 70)
        print()
        return

    # --- Recommendation details ---
    total_savings = sum(r["estimated_monthly_savings"] for r in recommendations)
    overall_savings_pct = (total_savings / total_cost * 100) if total_cost > 0 else 0

    print()
    print("  Recommendations:")
    print()

    for i, rec in enumerate(recommendations, start=1):
        print(f"  --- Recommendation {i} ---")
        print(f"  Resource          : {rec['current_resource']}")
        print(f"  Current config    : {rec['current_type']}  "
              f"({rec['current_vcpu']} vCPU, {rec['current_memory_gb']} GB)")
        print(f"  Current cost      : ${rec['current_monthly_cost']:>8.2f} /month")
        print(f"  Recommended config: {rec['recommended_config']}  "
              f"({rec['recommended_vcpu']} vCPU, {rec['recommended_memory_gb']} GB)")
        print(f"  Recommended cost  : ${rec['recommended_monthly_cost']:>8.2f} /month")
        print(f"  Estimated savings : ${rec['estimated_monthly_savings']:>8.2f} /month  "
              f"({rec['estimated_savings_percent']:.1f}%)")
        print(f"  Reason            : {rec['reason']}")
        print()

    # --- Totals ---
    print("-" * 70)
    print(f"  Total estimated monthly savings : ${total_savings:,.2f}")
    print(f"  Overall savings (% of spend)    : {overall_savings_pct:.1f}%")
    print()
    print("=" * 70)
    print("  DISCLAIMER: Recommendations are based on synthetic data and")
    print("  simple heuristics.  This is NOT a production optimisation system.")
    print("  No real cloud resources are modified by this analysis.")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    """Run the complete Stage 3 optimisation pipeline."""
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    resources_path = os.path.join(project_root, "data", "cloud_resources.csv")
    catalog_path   = os.path.join(project_root, "data", "resource_catalog.csv")

    # Validate input files
    for label, path in [("Resource dataset", resources_path),
                        ("Resource catalog", catalog_path)]:
        if not os.path.isfile(path):
            print(f"ERROR: {label} not found at {path}")
            return

    # Load data
    resources = load_resources(resources_path)
    catalog   = load_catalog(catalog_path)

    # Generate recommendations and print report
    underutilized, recommendations = generate_recommendations(resources, catalog)
    print_optimization_report(resources, underutilized, recommendations)


if __name__ == "__main__":
    main()
