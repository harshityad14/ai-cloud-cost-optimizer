# Stage 3 — Rule-Based Resource Optimisation

## Problem

Stage 2 identifies cloud resources that appear underutilized (low CPU **and**
low memory).  However, it does not answer the question:

> *"What should I replace this resource with, and how much would I save?"*

Stage 3 answers this by matching each underutilized resource against a catalog
of cheaper configurations and producing concrete right-sizing recommendations.

---

## Synthetic Pricing Model

All pricing in this project is **SYNTHETIC / DEMONSTRATION** data and does
**NOT** represent real GCP pricing.

### Single Pricing Source

Both current and recommended resource costs are derived from the **same**
catalog (`data/resource_catalog.csv`).  Each resource in
`data/cloud_resources.csv` has a `current_config` field that references its
catalog entry, making the pricing relationship traceable and internally
consistent.

### Pricing Structure & Assumptions

The synthetic catalog uses transparent, predictable pricing models:
- **VM Instances (`vm_instance`)**: Linear scaling based on standard tiers at **$0.0336 per vCPU per hour** (with 4 GB RAM per vCPU):
  - `e2-micro` (0.25 vCPU, 1 GB): $0.0084/hr
  - `e2-small` (0.5 vCPU, 2 GB): $0.0168/hr
  - `e2-medium` (1 vCPU, 4 GB): $0.0336/hr
  - `e2-standard-2` (2 vCPU, 8 GB): $0.0672/hr
  - `e2-standard-4` (4 vCPU, 16 GB): $0.1344/hr
  - `e2-standard-8` (8 vCPU, 32 GB): $0.2688/hr
- **Cloud SQL (`cloud_sql`)**: Standard instances scale linearly at **$0.0965 per vCPU per hour** (with 3.75 GB RAM per vCPU):
  - `db-n1-standard-1` (1 vCPU, 3.75 GB): $0.0965/hr
  - `db-n1-standard-2` (2 vCPU, 7.5 GB): $0.1930/hr
  - `db-n1-standard-4` (4 vCPU, 15 GB): $0.3860/hr
  - `db-n1-standard-8` (8 vCPU, 30 GB): $0.7720/hr
  - Shared-core tiers: `db-f1-micro` ($0.0150/hr), `db-g1-small` ($0.0500/hr)
- **Memorystore (`memorystore`)**: Tiered pricing from `basic-m1` ($0.0490/hr) to `basic-m5` ($0.4900/hr).
- **Load Balancers (`load_balancer`)**: Linear scaling at **$0.0250 per vCPU / 2 GB RAM per hour**:
  - `lb-small` (1 vCPU, 2 GB): $0.0250/hr
  - `lb-medium` (2 vCPU, 4 GB): $0.0500/hr
  - `lb-large` (4 vCPU, 8 GB): $0.1000/hr

### Monthly Hours Assumption

- A standard full-time month is assumed to be **730 hours** (≈ 365.25 days ÷ 12 months × 24 hours/day).
- Non-production resources may run for fewer hours to reflect realistic schedules (e.g., `staging-server` at 200 hours/month, `dev-test-server` at 350 hours/month).

### Monthly Cost Formula

Both current resource costs and recommended resource costs are derived using the exact same formula:

```
monthly_cost = round(hourly_cost × monthly_hours, 2)
```

- `hourly_cost` — the synthetic rate looked up from `data/resource_catalog.csv`.
- `monthly_hours` — how many hours the resource ran that month.
- Rounding to 2 decimal places is applied consistently across all cost and savings calculations.

### Resource Specifications

Each resource's `vcpu` and `memory_gb` in `data/cloud_resources.csv` match the
exact specifications of its `current_config` entry in `data/resource_catalog.csv`.
No duplicate-equivalent configurations exist in the catalog.

---

## Optimisation Approach

The method is a **simple, deterministic, rule-based heuristic**:

1. **Identify underutilized resources** — reuse Stage 2 logic
   (CPU < 20% **and** Memory < 30%).

2. **Translate utilisation into absolute resource needs:**

   ```
   required_vcpu      = (avg_cpu_percent / 100) × current_vcpu × SAFETY_MARGIN
   required_memory_gb = (avg_memory_percent / 100) × current_memory_gb × SAFETY_MARGIN
   ```

3. **Search the resource catalog** for configurations that:
   - match the same `resource_type`
   - have `vcpu >= required_vcpu`
   - have `memory_gb >= required_memory_gb`
   - do **NOT** have identical vCPU and memory to the current resource
     (identical specs with only a price difference is not a genuine downsize)

4. **Pick the cheapest valid candidate** (sorted by `hourly_cost`).

5. **Only recommend if it saves money:**
   ```
   recommended_monthly_cost = candidate_hourly_cost × monthly_hours
   ```
   If `recommended_monthly_cost >= current_monthly_cost`, the candidate is
   rejected (no recommendation made).

6. **Calculate savings:**
   ```
   estimated_savings     = current_monthly_cost − recommended_monthly_cost
   estimated_savings_pct = (estimated_savings / current_monthly_cost) × 100
   ```

---

## Assumptions

All of the following are simplifications used for this prototype:

| Assumption | Detail |
|---|---|
| **Average-based sizing** | We use average CPU/memory utilisation, not P95/P99. Real workloads may spike above the average. |
| **Safety margin = 1.5×** | A 50% headroom multiplier is applied to observed averages. This is arbitrary and would need tuning per workload. |
| **Same-type matching only** | A `vm_instance` can only be replaced by another `vm_instance`. Cross-type migrations (e.g., VM → serverless) are not considered. |
| **No identical-spec recommendations** | Candidates with the same vCPU and memory as the current resource are excluded. Only genuine downsizes are recommended. |
| **Consistent pricing model** | Both current and recommended costs are derived from the same catalog (`resource_catalog.csv`). |
| **Linear cost model** | Monthly cost = hourly rate × hours. Real cloud billing includes sustained-use discounts, committed-use agreements, egress charges, etc. |
| **No disk/network/GPU** | Only vCPU and memory are considered. Storage IOPS, network bandwidth, and GPU requirements are ignored. |

## Why This is a Heuristic

This approach uses a **fixed threshold + safety-margin rule**.  It does not:

- Learn from historical patterns
- Adapt thresholds per workload type
- Consider time-series usage patterns (e.g., nightly batch spikes)
- Account for auto-scaling or reserved-instance discounts
- Weigh business-criticality or SLA requirements

It is a transparent starting point that can be understood and verified by a
beginner.  Later stages may introduce machine learning or more advanced
analysis.

## Thresholds

| Parameter | Value | Purpose |
|---|---|---|
| CPU utilisation threshold | < 20% | Flag as underutilized |
| Memory utilisation threshold | < 30% | Flag as underutilized |
| Safety margin multiplier | 1.5× | Headroom for spikes |

---

## Example Recommendation

Actual output from the current optimizer for `api-backend-02`:

```
  --- Recommendation 2 ---
  Resource          : api-backend-02
  Current config    : vm_instance  (8.0 vCPU, 32.0 GB)
  Current cost      : $  196.22 /month
  Recommended config: e2-standard-2  (2.0 vCPU, 8.0 GB)
  Recommended cost  : $   49.06 /month
  Estimated savings : $  147.16 /month  (75.0%)
  Reason            : Average CPU (8.5%) and memory (11.2%) usage are both low.  A e2-standard-2 (2.0 vCPU, 8.0 GB) can handle the observed workload with a 1.5x safety margin.
```

### How this example's costs are derived

| Metric | Source / Specification | Formula / Derivation | Result |
|---|---|---|---|
| **Resource Specs** | `api-backend-02` (`e2-standard-8`) | 8.0 vCPU, 32.0 GB RAM, 730 hours/month | Baseline |
| **Observed Usage** | CPU: 8.5%, Memory: 11.2% | Both below thresholds (< 20% CPU, < 30% Mem) | Underutilized |
| **Required Specs** | Headroom with 1.5× safety margin | vCPU: `(8.5 / 100) × 8 × 1.5 = 1.02`<br>Memory: `(11.2 / 100) × 32 × 1.5 = 5.38 GB` | Minimum sizing |
| **Candidate Specs** | `e2-standard-2` | 2.0 vCPU, 8.0 GB RAM (meets minimum sizing) | Valid downsize |
| **Current Cost** | Config `e2-standard-8` rate: $0.2688/hr | `round(0.2688 × 730, 2)` | **$196.22 /month** |
| **Recommended Cost** | Config `e2-standard-2` rate: $0.0672/hr | `round(0.0672 × 730, 2)` | **$49.06 /month** |
| **Estimated Savings** | Absolute dollar difference | `round(196.22 − 49.06, 2)` | **$147.16 /month** |
| **Savings Percent** | Percentage reduction of spend | `(147.16 / 196.22) × 100` | **75.0%** |

Both current and recommended costs are derived consistently from the same catalog (`data/resource_catalog.csv`) using the identical hourly-to-monthly pricing model.

---

## Limitations

- This is **NOT** a production cloud optimisation system.
- Recommendations are based entirely on synthetic data and simple rules.
- The approach does not account for burst workloads, compliance constraints,
  multi-region failover, or reserved/committed pricing.
- No machine learning, generative AI, or real GCP integration is used.
- **No claim of novelty or patentability is made.** The method is a
  straightforward threshold-plus-catalog lookup that is common in cloud
  management tooling.

## Files

| File | Purpose |
|---|---|
| `data/cloud_resources.csv` | Current resources with specs, utilisation, and catalog-derived monthly cost |
| `data/resource_catalog.csv` | Available resource configurations (synthetic pricing) |
| `src/optimizer.py` | Optimisation engine (candidate search, recommendation builder) |
| `tests/test_optimizer.py` | Validation tests and regression checks |
| `docs/stage-3-optimization.md` | This document |
