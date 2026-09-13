# src/cost_analyzer.py
# AI Cloud Cost Optimizer — Stage 2: Local Cost Analysis
#
# This script loads a synthetic CSV dataset of cloud resources and performs
# basic cost and utilization analysis.  It uses only Python's standard
# library (no external packages required).
#
# DATA DISCLAIMER:
#   The dataset used here is SYNTHETIC / DEMONSTRATION DATA.
#   It does not represent real GCP billing values or actual cloud usage.

import csv
import os


# ---------------------------------------------------------------------------
# Configuration — Analysis Thresholds
# ---------------------------------------------------------------------------
# A resource is flagged as "potentially underutilized" when BOTH of the
# following conditions are true:
#   • Average CPU utilization  < CPU_THRESHOLD  (default 20%)
#   • Average Memory utilization < MEM_THRESHOLD (default 30%)
#
# These thresholds are simple starting heuristics and are NOT a substitute
# for a real cloud-optimization assessment.
# ---------------------------------------------------------------------------
CPU_THRESHOLD = 20.0   # percent
MEM_THRESHOLD = 30.0   # percent


def load_resources(csv_path):
    """Load cloud resource records from a CSV file.

    Each row is returned as a dictionary with properly typed values:
      - resource_name     (str)
      - resource_type     (str)
      - monthly_cost      (float)
      - avg_cpu_percent   (float)
      - avg_memory_percent(float)
      - monthly_hours     (float)
      - vcpu              (float, optional — present when resource specs are available)
      - memory_gb         (float, optional — present when resource specs are available)
      - current_config    (str, optional — catalog config name for pricing traceability)
    """
    resources = []

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            resource = {
                "resource_name":      row["resource_name"].strip(),
                "resource_type":      row["resource_type"].strip(),
                "monthly_cost":       float(row["monthly_cost"]),
                "avg_cpu_percent":    float(row["avg_cpu_percent"]),
                "avg_memory_percent": float(row["avg_memory_percent"]),
                "monthly_hours":      float(row["monthly_hours"]),
            }

            # Stage 3 fields (optional — present when resource specs exist)
            if "vcpu" in row and row["vcpu"].strip():
                resource["vcpu"] = float(row["vcpu"])
            if "memory_gb" in row and row["memory_gb"].strip():
                resource["memory_gb"] = float(row["memory_gb"])
            if "current_config" in row and row["current_config"].strip():
                resource["current_config"] = row["current_config"].strip()

            resources.append(resource)

    return resources


def find_underutilized(resources, cpu_thresh=CPU_THRESHOLD, mem_thresh=MEM_THRESHOLD):
    """Return resources where BOTH CPU and memory are below their thresholds."""
    return [
        r for r in resources
        if r["avg_cpu_percent"] < cpu_thresh
        and r["avg_memory_percent"] < mem_thresh
    ]


def print_report(resources, underutilized):
    """Print a human-readable analysis report to the console."""

    # --- Summary statistics ---
    total_cost = sum(r["monthly_cost"] for r in resources)
    avg_cpu    = sum(r["avg_cpu_percent"] for r in resources) / len(resources)
    avg_mem    = sum(r["avg_memory_percent"] for r in resources) / len(resources)

    print()
    print("=" * 65)
    print("  Cloud Cost Analysis Report  (Synthetic Data)")
    print("=" * 65)
    print(f"  Total resources analysed   : {len(resources)}")
    print(f"  Total monthly cost         : ${total_cost:,.2f}")
    print(f"  Average CPU utilization    : {avg_cpu:.1f}%")
    print(f"  Average Memory utilization : {avg_mem:.1f}%")
    print("-" * 65)

    # --- Full resource table ---
    print()
    print("  All Resources:")
    print(f"  {'Name':<20} {'Type':<16} {'Cost':>8}  {'CPU%':>5}  {'Mem%':>5}  {'Hrs':>5}")
    print("  " + "-" * 63)

    for r in resources:
        print(
            f"  {r['resource_name']:<20} "
            f"{r['resource_type']:<16} "
            f"${r['monthly_cost']:>7.2f}  "
            f"{r['avg_cpu_percent']:>5.1f}  "
            f"{r['avg_memory_percent']:>5.1f}  "
            f"{r['monthly_hours']:>5.0f}"
        )

    # --- Underutilized resources ---
    print()
    print("-" * 65)
    print(f"  Underutilization Thresholds: CPU < {CPU_THRESHOLD}%  AND  Memory < {MEM_THRESHOLD}%")
    print("-" * 65)

    if underutilized:
        underutil_cost = sum(r["monthly_cost"] for r in underutilized)

        print(f"  Potentially underutilized resources: {len(underutilized)}")
        print(f"  Combined monthly cost of flagged resources: ${underutil_cost:,.2f}")
        print()

        for r in underutilized:
            print(f"    [!] {r['resource_name']:<20}  "
                  f"CPU {r['avg_cpu_percent']:>5.1f}%  "
                  f"Mem {r['avg_memory_percent']:>5.1f}%  "
                  f"Cost ${r['monthly_cost']:>7.2f}")

        # --- Potential savings as a percentage ---
        savings_pct = (underutil_cost / total_cost) * 100 if total_cost > 0 else 0
        print()
        print(f"  >> Flagged resources account for {savings_pct:.1f}% of total spend.")
        print("  >> Consider reviewing these for downsizing or decommissioning.")
    else:
        print("  No underutilized resources detected with current thresholds.")

    print()
    print("=" * 65)
    print("  NOTE: This analysis uses synthetic data and simple heuristics.")
    print("  It is NOT a production cloud-optimization assessment.")
    print("=" * 65)
    print()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main():
    # Build the path to the CSV relative to the project root
    # (assumes this script is run from the project root directory)
    script_dir   = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)  # go up from src/
    csv_path     = os.path.join(project_root, "data", "cloud_resources.csv")

    # Validate that the file exists
    if not os.path.isfile(csv_path):
        print(f"ERROR: Dataset not found at {csv_path}")
        print("Make sure data/cloud_resources.csv exists.")
        return

    # Load, analyse, report
    resources     = load_resources(csv_path)
    underutilized = find_underutilized(resources)
    print_report(resources, underutilized)

    # --- Quick validation check ---
    # Verify basic expectations about the loaded data.
    assert len(resources) > 0, "No resources loaded — CSV may be empty."
    assert all(r["monthly_cost"] >= 0 for r in resources), "Negative cost detected."
    assert all(0 <= r["avg_cpu_percent"] <= 100 for r in resources), "CPU% out of range."
    assert all(0 <= r["avg_memory_percent"] <= 100 for r in resources), "Memory% out of range."
    print("  [OK] Basic data-validation checks passed.\n")


if __name__ == "__main__":
    main()
