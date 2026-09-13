# AI-Driven Cloud Cost Optimization & Resource Recommendation System

> A transparent, rule-based analytics engine for identifying underutilized cloud infrastructure and generating right-sizing recommendations with verifiable cost savings.

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/status-active--development-green.svg)](#project-status)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

---

## Project Overview

Modern cloud architectures frequently suffer from over-provisioning and idle resource allocation. Engineering teams often size cloud instances for peak traffic loads that rarely materialize, resulting in significant recurring infrastructure expenditure. Without automated visibility into workload patterns, organizations incur unnecessary costs across compute instances, managed databases, in-memory caches, and load balancers.

This repository provides an automated, reproducible cost-analysis and optimization engine. Starting with structured resource usage metrics and a standardized configuration catalog, the system:
1. Detects underutilized resources based on concurrent CPU and memory consumption thresholds.
2. Translates observed utilization metrics into baseline demand with provisioned safety headroom.
3. Matches workloads against a configuration catalog to identify the lowest-cost alternative satisfying all resource requirements.
4. Produces actionable right-sizing recommendations complete with detailed financial projections.

Currently, the project operates entirely via a local Python-based analytics pipeline using synthetic demonstration datasets.

---

## Key Objectives

- **Identify Underutilized Cloud Resources**: Detect idle or over-provisioned infrastructure using multi-metric threshold evaluation.
- **Analyze Utilization and Cost**: Aggregate expenditure and compute utilization statistics across heterogeneous resource families (`vm_instance`, `cloud_sql`, `memorystore`, `load_balancer`).
- **Recommend Cost-Efficient Configurations**: Search available resource tiers to identify viable, lower-cost configurations meeting capacity demands.
- **Estimate Potential Savings**: Calculate dollar-denominated and percentage-based monthly savings using a consistent, unified pricing model.
- **Preserve Performance Headroom**: Ensure recommended configurations maintain a safety margin (default 1.5× multiplier above average utilization) to accommodate workload fluctuations.

---

## Current Capabilities

The repository currently implements **Stage 2 (Local Cost Analysis)** and **Stage 3 (Rule-Based Resource Optimization Engine)**:

- **Local CSV Ingestion**: Type-safe loading of cloud resource metrics and configuration catalogs without third-party dependencies.
- **Multi-Metric Underutilization Filtering**: Flags resources where *both* average CPU utilization (< 20%) and average memory utilization (< 30%) indicate chronic over-provisioning.
- **Safety-Margin Capacity Sizing**: Converts percentage utilization into required vCPU and memory dimensions with configurable headroom multipliers.
- **Catalog-Driven Downsizing Search**: Deterministically filters catalog entries by resource type, minimum required specifications, cost savings, and specification divergence.
- **Identical-Specification Rejection**: Enforces validation guards preventing recommendations of identical vCPU/memory configurations that merely reflect catalog discrepancies.
- **Unified Pricing Model**: Derives current resource spend and candidate costs from the identical catalog pricing source using standardized monthly hours.
- **Comprehensive Test Suite**: Automated regression and validation tests enforcing data integrity, pricing model alignment, sizing math, and documentation accuracy.

---

## Current Architecture

The current system is structured as a modular, local data processing pipeline using only the Python standard library:

```mermaid
flowchart TD
    subgraph Data Layer
        A[cloud_resources.csv<br/>Observed Usage & Specs]
        B[resource_catalog.csv<br/>Pricing & Specs Tiers]
    end

    subgraph Cost Analyzer (Stage 2)
        C[load_resources] --> D[Utilization Aggregator]
        D --> E{find_underutilized<br/>CPU < 20% & Mem < 30%}
    end

    subgraph Optimization Engine (Stage 3)
        F[calculate_required_resources<br/>Usage x Current Specs x 1.5x Headroom]
        G[find_best_candidate<br/>Type Match + Specs Gate + Cheaper Gate]
        H[get_current_resource_cost<br/>Derived from Catalog Rates]
        I[build_recommendation<br/>Savings Math & Explanation]
    end

    subgraph Reporting Layer
        J[Console Optimization Report<br/>Resource-by-Resource Breakdown]
    end

    A --> C
    B --> G
    B --> H
    E -->|Flagged Resources| F
    F --> G
    H --> G
    G --> I
    I --> J
```

---

## Optimization Methodology

The optimization engine implements a deterministic, 6-step heuristic:

1. **Underutilization Detection**:
   A resource is flagged as underutilized if and only if both average metrics fall below heuristic thresholds:
   $$\text{avg\_cpu\_percent} < 20.0\% \quad \land \quad \text{avg\_memory\_percent} < 30.0\%$$

2. **Workload Sizing with Safety Headroom**:
   Translates observed percentages into minimum required hardware specifications while provisioning 50% headroom ($\text{SAFETY\_MARGIN} = 1.5$):
   $$\text{required\_vcpu} = \left(\frac{\text{avg\_cpu\_percent}}{100}\right) \times \text{current\_vcpu} \times 1.5$$
   $$\text{required\_memory\_gb} = \left(\frac{\text{avg\_memory\_percent}}{100}\right) \times \text{current\_memory\_gb} \times 1.5$$

3. **Candidate Filtering & Validation**:
   Filters candidate configurations from `data/resource_catalog.csv` satisfying all constraints:
   - **Type Equality**: `candidate.resource_type == resource.resource_type`
   - **Capacity Sufficiency**: `candidate.vcpu >= required_vcpu` and `candidate.memory_gb >= required_memory_gb`
   - **Specification Divergence**: Candidates with identical vCPU *and* memory to current specs are explicitly excluded to prevent false downsizes.
   - **Identity Exclusion**: `candidate.config_name != resource.current_config`

4. **Selection of Cheapest Viable Configuration**:
   Sorts eligible candidates by hourly rate and selects the candidate with the lowest hourly cost.

5. **Strict Cost Reduction Gate**:
   Both current and candidate monthly costs are derived from catalog rates:
   $$\text{monthly\_cost} = \text{round}(\text{hourly\_cost} \times \text{monthly\_hours}, 2)$$
   A candidate is accepted only if:
   $$\text{recommended\_monthly\_cost} < \text{current\_monthly\_cost}$$

6. **Financial Estimation**:
   $$\text{estimated\_monthly\_savings} = \text{round}(\text{current\_monthly\_cost} - \text{recommended\_monthly\_cost}, 2)$$
   $$\text{estimated\_savings\_percent} = \left(\frac{\text{estimated\_monthly\_savings}}{\text{current\_monthly\_cost}}\right) \times 100$$

---

## Project Structure

```text
ai-cloud-cost-optimizer/
├── data/
│   ├── cloud_resources.csv       # Synthetic resource inventory with metrics & run hours
│   └── resource_catalog.csv      # Synthetic configuration pricing catalog
├── docs/
│   ├── project-notes.md          # Multi-stage engineering notes and design decisions
│   └── stage-3-optimization.md   # Stage 3 methodology, derivations, and specifications
├── src/
│   ├── __init__.py
│   ├── cost_analyzer.py          # Stage 2: Inventory loading & underutilization filtering
│   └── optimizer.py              # Stage 3: Sizing calculations & recommendation engine
├── tests/
│   ├── __init__.py
│   ├── test_cost_analyzer.py     # Stage 2 validation test suite
│   └── test_optimizer.py         # Stage 3 validation and regression test suite
├── .gitignore
└── README.md
```

---

## Example Results

When executed against the project's verified synthetic baseline dataset (`data/cloud_resources.csv`), the optimizer outputs the following results:

| Metric | Value |
|---|---|
| **Total Resources Evaluated** | 12 |
| **Total Baseline Monthly Cost** | $1,823.85 |
| **Resources Flagged as Underutilized** | 7 (58.3% of inventory) |
| **Actionable Downsizing Recommendations** | 5 |
| **Total Estimated Monthly Savings** | **$448.70** |
| **Overall Spend Reduction** | **24.6%** |

> [!NOTE]
> **Data Disclaimer**: All resource metrics, instance names, and pricing figures are synthetic demonstration values designed for algorithmic validation. They do not represent live production environments or actual Google Cloud billing rates.

### Sample Recommendation Output

```text
  --- Recommendation 2 ---
  Resource          : api-backend-02
  Current config    : vm_instance  (8.0 vCPU, 32.0 GB)
  Current cost      : $  196.22 /month
  Recommended config: e2-standard-2  (2.0 vCPU, 8.0 GB)
  Recommended cost  : $   49.06 /month
  Estimated savings : $  147.16 /month  (75.0%)
  Reason            : Average CPU (8.5%) and memory (11.2%) usage are both low.  A e2-standard-2 (2.0 vCPU, 8.0 GB) can handle the observed workload with a 1.5x safety margin.
```

---

## Technology Stack

- **Language**: Python 3.10+
- **Standard Library Modules**:
  - `csv` — Tabular data parsing and serialization
  - `os` / `sys` — Path resolution and environment orchestration
- **External Dependencies**: None (zero third-party dependencies required for core execution)

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher installed on your system.
- Git installed.

### 1. Clone the Repository
```bash
git clone https://github.com/harshityad14/ai-cloud-cost-optimizer.git
cd ai-cloud-cost-optimizer
```

### 2. Optional: Set Up Virtual Environment
```bash
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Run the Applications
Execute the cost analysis module (Stage 2):
```bash
python -m src.cost_analyzer
```

Execute the resource optimization engine (Stage 3):
```bash
python -m src.optimizer
```

---

## Testing

The project uses Python's built-in assertion framework to ensure zero external test dependencies while maintaining strict verification standards.

### Running Test Suites

Run Stage 2 cost analyzer tests:
```bash
python -m tests.test_cost_analyzer
```

Run Stage 3 optimizer and regression tests:
```bash
python -m tests.test_optimizer
```

### What the Tests Verify
- **Data Ingestion Integrity**: Type verification, valid range bounds (CPU/Mem between 0–100%), non-negative costs.
- **Threshold Sizing**: Accurate vCPU and memory headroom computations with safety multiplier.
- **Edge Boundary Conditions**: Strict `<` inequality evaluations at exact threshold boundaries.
- **Candidate Filtering**: Filtering by resource type, sufficiency of specs, rejection of identical specifications.
- **Pricing Model Parity**: Cross-verification that `data/cloud_resources.csv` costs exactly equal `catalog_hourly_rate * monthly_hours`.
- **Catalog Uniqueness**: Automated check ensuring no duplicate `(resource_type, vcpu, memory_gb)` tuples exist in the catalog.
- **Documentation Parity**: Automated regression check verifying that documentation examples match optimizer runtime output verbatim.

---

## Design Goals

- **Correctness**: Zero tolerance for false-positive downsizes, identical-spec cost differences, or rounding errors.
- **Reproducibility**: Deterministic heuristics and standalone scripts that run consistently across all environments.
- **Explainability**: Every recommendation includes human-readable rationale articulating the workload demand and safety headroom.
- **Cost-Awareness**: Both current spend and potential alternatives are evaluated against a single, traceable pricing catalog.
- **Testability**: Self-contained test suites covering edge cases, math accuracy, and catalog constraints.
- **Modular Architecture**: Clean separation between data ingestion, underutilization detection, optimization heuristics, and reporting layers.

---

## Limitations

- **Synthetic Datasets**: The current system runs on synthetic CSV data and does not connect to live cloud environments.
- **Heuristic Sizing**: Sizing is derived from average CPU/memory utilization rather than full percentile distributions (e.g., P95, P99) or burst profiles.
- **Simplified Billing Model**: Assumes linear hourly rates without factoring in committed-use discounts (CUDs), sustained-use discounts (SUDs), or network egress costs.
- **Same-Family Matching**: The optimizer only downsizes within the same resource family (e.g., VM to VM); cross-architecture conversions (e.g., VM to Serverless/Cloud Run) are not modeled.
- **No Cloud API Integration**: Real-time metric querying and automated resizing actions are not implemented in the current stage.

---

## Development Roadmap

The project is being developed in iterative milestones:

### Completed Stages
- [x] **Stage 1: Project Foundation**: Setup repository structure, coding standards, and project scaffolding.
- [x] **Stage 2: Local Cost Analysis**: Built CSV data loader, threshold-based underutilization detection, and utilization summary reporting.
- [x] **Stage 3: Rule-Based Optimization Engine**: Implemented resource sizing with safety margin, catalog search, unified pricing derivation, and comprehensive regression test suites.

### Planned Stages *(Not Yet Implemented)*
- [ ] **Stage 4: Google Cloud Platform (GCP) Integration**: Connect to live GCP Cloud Monitoring (CloudWatch / Monitoring API) and Cloud Billing BigQuery export. *(Planned)*
- [ ] **Stage 5: Time-Series Workload Forecasting & Anomaly Detection**: Incorporate machine learning models (e.g., ARIMA, Prophet, LSTM) to forecast traffic spikes and identify usage anomalies before downsizing. *(Planned)*
- [ ] **Stage 6: Advanced Multi-Factor Optimization**: Factor in disk IOPS, network egress bandwidth, GPU requirements, and regional pricing differences. *(Planned)*
- [ ] **Stage 7: GenAI-Powered Recommendations & Explanations**: Integrate LLM APIs (e.g., Google Gemini) to generate natural-language executive summaries, architectural advice, and contextual risk assessments. *(Planned)*
- [ ] **Stage 8: Interactive Dashboard & UI**: Develop a Streamlit or React-based management interface for real-time visualization and one-click right-sizing actions. *(Planned)*
- [ ] **Stage 9: Automated Infrastructure Remediation**: Terraform / Google Cloud SDK integration for approval-gated automated right-sizing execution. *(Planned)*
- [ ] **Stage 10: Empirical Evaluation & Benchmarking**: Formal evaluation on production workloads measuring cost reduction versus SLA impact. *(Planned)*

---

## Future Research & Innovation Direction

Beyond static threshold matching, intelligent cloud cost optimization requires understanding workload dynamics over time. Future development aims to transition this prototype from a rule-based calculator to an adaptive optimization system by exploring:
- **Distributional Risk Analysis**: Evaluating workload volatility via probability distributions rather than static scalar averages to prevent SLA degradation.
- **Context-Aware LLM Synthesis**: Synthesizing monitoring logs, deployment schedules, and architectural context to explain *why* a workload behaves as it does before recommending resizing.
- **Multi-Cloud Policy Mapping**: Standardizing cross-provider abstraction layers to enable workload-placement recommendations across multiple cloud vendors.

---

## Project Status

- **Status**: Active Development
- **Current Milestone**: Stage 3 Complete (Rule-Based Resource Optimization Engine verified and tested)

---

## Author

- **Harshit Yadav**
- GitHub: [@harshityad14](https://github.com/harshityad14)
- Repository: [ai-cloud-cost-optimizer](https://github.com/harshityad14/ai-cloud-cost-optimizer)

---

## License

This repository is currently under active development. All rights reserved. Formal open-source licensing will be added in a future release.
