# Bureau Report & Executive Summary – Implementation Instructions

This document is written for **Cursor** to implement bureau tradeline–based reporting **within the existing architecture**.

The goal is to:

* Reuse the current agentic pipeline
* Add a new **bureau report vertical**
* Introduce a **feature-extraction layer** for bureau tradelines
* Generate a deterministic **executive summary** (later narrated by LLM)

---

## 1. Guiding Principles (DO NOT VIOLATE)

1. **This work MUST reuse the existing pipeline end-to-end**
2. **No new agent, planner, executor, or UI is to be created**
3. **Bureau reporting is a parallel report vertical, not a new system**
4. **No LLM touches raw bureau tradelines**
5. **All bureau features are computed deterministically**
6. **LLM is used only for narration / phrasing**
7. **Reuse intent → planner → executor → PDF → UI exactly as-is**
8. **Features ≠ report sections** (features are inputs)

If any logic ends up inside the LLM prompt → architecture is wrong.

---

## 2. High-Level Architecture Extension

⚠️ IMPORTANT: This is **NOT a new pipeline**.

The existing pipeline remains unchanged. We are **adding a parallel report build path** that plugs into the same flow.

Existing (unchanged):

```
Intent
 → Tool
   → Builder (deterministic)
     → Schema
       → LLM Summary
         → PDF
```

Extended (parallel build path only):

```
Intent (BUREAU_REPORT)
 → Tool (generate_bureau_report)
   → Bureau Report Builder   ← parallel to customer_report_builder
       → Feature Extraction Layer
       → Feature Aggregation Layer
       → Executive Summary Inputs
   → LLM Narration (existing summary chain)
   → PDF Renderer (existing engine, new template)
```

Nothing above the **Builder layer** changes.

---

## 3. New Intent Addition

### File: `schemas/intent.py`

Add a new intent:

```python
class IntentType(str, Enum):
    ...
    BUREAU_REPORT = "bureau_report"
```

---

## 4. Intent Mapping

### File: `config/intents.py`

```python
INTENT_TOOL_MAP[IntentType.BUREAU_REPORT] = ["generate_bureau_report"]

REQUIRED_FIELDS[IntentType.BUREAU_REPORT] = ["customer_id"]
```

---

## 5. Loan Taxonomy (Canonical)

### File: `schemas/loan_type.py`

Create a **single source of truth** for loan types:
Refer to dpd_data.csv for names of loan types and create accorfingly

```python
class LoanType(str, Enum):
    PL = "personal_loan"
    CC = "credit_card"
    HL = "home_loan"
    AL = "auto_loan"
    BL = "business_loan"
    LAP = "lap_las_lad"
    GL = "gold_loan"
    TWL = "two_wheeler_loan"
    CD = "consumer_durable"
    OTHER = "other"
```

All bureau logic MUST reference this enum.

---

## 6. Bureau Feature Definition Layer (CORE)

### Purpose

This layer implements the **feature matrix** you provided.

Each feature is a **primitive data point** used to compute the executive summary.

### File: `features/bureau_features.py`

Define a **FeatureVector** (internal, not UI-facing):

```python
@dataclass
class BureauLoanFeatureVector:
    loan_type: LoanType
    secured: bool

    loan_count: int
    total_sanctioned_amount: float
    total_outstanding_amount: float

    avg_vintage_months: float
    months_since_last_payment: Optional[int]

    live_count: int
    closed_count: int

    delinquency_flag: bool
    max_dpd: Optional[int]
    overdue_amount: float

    utilization_ratio: Optional[float]  # CC only

    forced_event_flags: List[str]
    on_us_count: int
    off_us_count: int
```

Applicability rules (e.g. utilization only for CC) are enforced during computation.

---

## 7. Feature Extraction Logic

### File: `pipeline/bureau_feature_extractor.py`

Responsibilities:

1. Load raw bureau tradelines
2. Normalize loan types → `LoanType`
3. Group tradelines by loan type
4. Compute **one FeatureVector per loan type**

This layer MUST:

* Contain all numeric logic
* Handle missing / partial data safely
* Never format text

---

## 8. Feature Aggregation Layer

### File: `pipeline/bureau_feature_aggregator.py`

Compute **executive summary inputs** from feature vectors.

Examples:

* Total tradelines
* Live vs closed counts
* Product-wise exposure
* Total unsecured exposure
* Max delinquency across portfolio
* Weighted utilization

Output:

```python
@dataclass
class BureauExecutiveSummaryInputs:
    total_tradelines: int
    live_tradelines: int
    closed_tradelines: int

    product_breakdown: Dict[LoanType, BureauLoanFeatureVector]

    total_exposure: float
    total_outstanding: float
    unsecured_exposure: float

    has_delinquency: bool
    max_dpd: Optional[int]
```

This object is what the LLM will see.

---

## 9. Bureau Report Schema

### File: `schemas/bureau_report.py`

```python
@dataclass
class BureauReport:
    meta: ReportMeta
    feature_vectors: Dict[LoanType, BureauLoanFeatureVector]
    executive_inputs: BureauExecutiveSummaryInputs
    narrative: Optional[str] = None
```

Feature vectors are retained for auditability.

---

## 10. Bureau Report Builder

### File: `pipeline/bureau_report_builder.py`

Responsibilities:

1. Call feature extractor
2. Call feature aggregator
3. Assemble `BureauReport`

NO LLM CALLS HERE.

---

## 11. Tool Orchestration

### File: `pipeline/executor.py`

Register tool:

```python
"generate_bureau_report": generate_bureau_report_pdf
```

### File: `tools/bureau.py`

```python
def generate_bureau_report_pdf(customer_id: int):
    report = build_bureau_report(customer_id)
    report.narrative = generate_bureau_review(report.executive_inputs)
    pdf_path = render_bureau_report_pdf(report)
    return report, pdf_path
```

---

## 12. LLM Summary Chain

### File: `pipeline/report_summary_chain.py`

Add a new function:

```python
def generate_bureau_review(executive_inputs, style="hinglish"):
    # LLM sees ONLY executive_inputs
```

Rules:

* No numbers invented
* No arithmetic
* Pure narration

---

## 13. PDF Rendering

### File: `templates/bureau_report.html`

Two pages:

**Page 1 – Executive Summary**

* Total tradelines
* Live vs closed
* Key exposures
* Delinquency flags

**Page 2 – Product-wise Table**

* One row per loan type
* Columns from feature matrix

---

## 14. UI Integration (No New UI)

The **existing ChatGPT-like UI is reused without modification**.

There is:

* No new frontend
* No new endpoints
* No new routing layer

The UI simply sends user text into the same pipeline.

Example:

```
User: Generate bureau report for <customer_id>
```

The intent parser routes to `BUREAU_REPORT`, which triggers a **parallel report build** using the same executor and renderer.

Return to UI:

* Executive narrative
* PDF download button

---

## 15. Validation & Safety

Add checks:

* Sum of live + closed == total tradelines
* Utilization only present for CC
* No negative balances

Failures → log + partial report (fail-soft).

---

## 16. Future Extensions (DO NOT BUILD NOW)

* Combined bank + bureau report
* Risk score derivation
* Policy-based decisioning

---

## 17. Final Note to Cursor

This is a **financial risk system**.

Determinism > intelligence.

If logic feels like it belongs in the LLM, move it DOWN into features.

End of instructions.
