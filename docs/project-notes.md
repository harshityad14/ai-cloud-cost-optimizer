# AI Cloud Cost Optimizer — Project Notes

## Project Objective

Build an AI-powered system that analyzes cloud infrastructure costs and
recommends resource optimizations. The system will eventually use machine
learning and generative AI to identify waste, predict spending trends, and
suggest right-sizing actions.

## Current Development Stage

**Stage: Stage 2 — Local Cost Analysis**

- Setting up the Python project structure (completed in Stage 1).
- Loading a synthetic CSV dataset and performing basic cost analysis.
- Identifying potentially underutilized resources using simple thresholds.
- No external libraries, cloud SDKs, or ML frameworks are used at this stage.

## Technologies Planned for Later Stages

| Category             | Technology / Service              |
|----------------------|-----------------------------------|
| Language             | Python                            |
| Cloud Platform       | Google Cloud Platform (GCP)       |
| AI / ML              | Scikit-learn, TensorFlow (TBD)    |
| Generative AI        | Google Gemini API                 |
| Data & Visualization | Pandas, Matplotlib, Streamlit     |
| Version Control      | Git & GitHub                      |

> These technologies will be introduced incrementally as the project matures.

## Important Notices

- **Patentability has NOT been established.** No claim of novelty or
  patentability is made at this time. The project is for educational and
  research purposes.
- **Current code is a prototype / foundation only.** It does not represent
  a production-ready system and is intended solely to explore concepts and
  establish a starting point for further development.

---

## Stage 2 — Local Cost Analysis

### Why synthetic data?

At this stage we do not have access to a real GCP billing export or live
monitoring metrics. To build and test the analysis logic we use a small,
hand-crafted CSV file (`data/cloud_resources.csv`) containing **demonstration /
synthetic data**. The values are realistic-looking but entirely fabricated.
They do **not** represent real cloud billing or usage figures.

### Dataset fields

| Column               | Type   | Description                                             |
|----------------------|--------|---------------------------------------------------------|
| `resource_name`      | string | A human-readable label for the resource (e.g. `web-server-01`). |
| `resource_type`      | string | The kind of cloud service (`vm_instance`, `cloud_sql`, `memorystore`, `load_balancer`). |
| `monthly_cost`       | float  | Estimated monthly cost in USD (synthetic).              |
| `avg_cpu_percent`    | float  | Average CPU utilization over the billing period (0–100). |
| `avg_memory_percent` | float  | Average memory utilization over the billing period (0–100). |
| `monthly_hours`      | float  | Total hours the resource was running during the month.  |

### What is an "underutilized" resource?

In this prototype, a resource is flagged as **potentially underutilized** when
**both** of the following conditions are true:

- Average CPU utilization is **below 20%**
- Average memory utilization is **below 30%**

These thresholds are simple starting heuristics chosen for demonstration
purposes. In a real system, thresholds would vary by resource type, workload
pattern, and business requirements.

### Thresholds used

| Metric                  | Threshold |
|-------------------------|-----------|
| Average CPU utilization | < 20%     |
| Average Memory utilization | < 30%  |

### Limitations

- This is **NOT** a real cloud optimization system.
- The thresholds are arbitrary and not validated against production workloads.
- The analysis does not account for burst usage, time-of-day patterns,
  auto-scaling, reserved/committed-use discounts, or network utilisation.
- No machine learning, generative AI, or GCP integration is used yet.

---

## Stage 3 — Rule-Based Optimisation Engine

Stage 3 adds a **recommendation engine** that determines whether a cheaper
resource configuration can replace each underutilized resource identified in
Stage 2.

Key additions:

- **Resource catalog** (`data/resource_catalog.csv`) — a set of available
  configurations with synthetic pricing.
- **Sizing logic** — translates observed utilisation into minimum required
  vCPU and memory, with a 1.5× safety margin.
- **Candidate matching** — finds the cheapest catalog entry (same type) that
  meets the computed requirements.
- **Savings calculation** — reports estimated monthly savings per resource and
  overall.
- **Validation tests** (`tests/test_optimizer.py`) — assert-based checks for
  all key calculations.

> Full details, assumptions, and limitations are documented in
> `docs/stage-3-optimization.md`.
