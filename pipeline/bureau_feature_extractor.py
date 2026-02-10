"""Bureau feature extraction from raw tradeline data.

Loads dpd_data.csv, normalizes loan types, groups by canonical LoanType,
and computes one BureauLoanFeatureVector per loan type.

All logic is deterministic — no LLM, no formatting.
"""

import csv
import os
import re
from collections import defaultdict
from datetime import datetime, date
from typing import Dict, List, Optional

from schemas.loan_type import (
    LoanType,
    normalize_loan_type,
    is_secured,
    ON_US_SECTORS,
)
from features.bureau_features import BureauLoanFeatureVector

# Module-level cache for bureau CSV
_bureau_df: Optional[List[dict]] = None

# DPD flag columns in dpd_data.csv
_DPD_COLUMNS = [f"dpdf{i}" for i in range(1, 37)]

# Forced event codes in dpd_string (3-char patterns indicating non-standard events)
_KNOWN_FORCED_EVENTS = {"WRF", "SET", "SMA", "SUB", "DBT", "LSS", "WOF"}

# Pattern: 3 consecutive alpha chars in dpd_string
_ALPHA_PATTERN = re.compile(r"[A-Z]{3}")


def _get_dpd_data_path() -> str:
    """Get the path to dpd_data.csv relative to the project root."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "dpd_data.csv")


def _load_bureau_data(force_reload: bool = False) -> List[dict]:
    """Load and cache dpd_data.csv (tab-separated)."""
    global _bureau_df
    if _bureau_df is None or force_reload:
        data_path = _get_dpd_data_path()
        with open(data_path, "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            _bureau_df = list(reader)
    return _bureau_df


def _safe_float(value: str, default: float = 0.0) -> float:
    """Parse a string to float, returning default for NULL/empty/invalid."""
    if not value or value.strip().upper() in ("NULL", ""):
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _safe_int(value: str, default: int = 0) -> int:
    """Parse a string to int, returning default for NULL/empty/invalid."""
    if not value or value.strip().upper() in ("NULL", ""):
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def _parse_date(value: str) -> Optional[date]:
    """Parse a date string (YYYY-MM-DD) safely."""
    if not value or value.strip().upper() in ("NULL", ""):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _compute_months_since_last_payment(tradelines: List[dict]) -> Optional[int]:
    """Compute months since the most recent last_payment_date across tradelines."""
    today = date.today()
    latest_payment: Optional[date] = None

    for tl in tradelines:
        payment_date = _parse_date(tl.get("last_payment_date", ""))
        if payment_date is not None:
            if latest_payment is None or payment_date > latest_payment:
                latest_payment = payment_date

    if latest_payment is None:
        return None

    delta = (today.year - latest_payment.year) * 12 + (today.month - latest_payment.month)
    return max(0, delta)


def _compute_max_dpd(tradelines: List[dict]) -> Optional[int]:
    """Compute maximum DPD across all tradelines and all 36 monthly flags."""
    max_val = 0
    found_any = False

    for tl in tradelines:
        for col in _DPD_COLUMNS:
            val = _safe_int(tl.get(col, ""), default=0)
            if val > 0:
                found_any = True
                max_val = max(max_val, val)

    return max_val if found_any else None


def _extract_forced_event_flags(tradelines: List[dict]) -> List[str]:
    """Extract forced event flags from dpd_string across tradelines.

    Forced events are 3-character alpha codes in the dpd_string that are
    not standard markers (STD, XXX).
    """
    flags: set = set()

    for tl in tradelines:
        dpd_str = tl.get("dpd_string", "")
        matches = _ALPHA_PATTERN.findall(dpd_str)
        for m in matches:
            if m not in ("STD", "XXX"):
                flags.add(m)

    return sorted(flags)


def _compute_utilization_ratio(tradelines: List[dict], loan_type: LoanType) -> Optional[float]:
    """Compute utilization ratio for credit cards only.

    Utilization = total outstanding / total credit limit (for live tradelines).
    """
    if loan_type != LoanType.CC:
        return None

    total_outstanding = 0.0
    total_limit = 0.0

    for tl in tradelines:
        if tl.get("loan_status", "").strip() != "Live":
            continue
        limit = _safe_float(tl.get("creditlimit", ""))
        outstanding = _safe_float(tl.get("out_standing_balance", ""))
        if limit > 0:
            total_limit += limit
            total_outstanding += outstanding

    if total_limit <= 0:
        return None

    return round(total_outstanding / total_limit, 4)


def _build_feature_vector(
    loan_type: LoanType, tradelines: List[dict]
) -> BureauLoanFeatureVector:
    """Build a single feature vector for a group of tradelines of the same loan type."""
    loan_count = len(tradelines)
    secured = is_secured(loan_type)

    total_sanctioned = sum(_safe_float(tl.get("sanction_amount", "")) for tl in tradelines)
    total_outstanding = sum(_safe_float(tl.get("out_standing_balance", "")) for tl in tradelines)

    # Vintage from tl_vin_1 (months)
    vintages = [_safe_float(tl.get("tl_vin_1", "")) for tl in tradelines]
    valid_vintages = [v for v in vintages if v > 0]
    avg_vintage = round(sum(valid_vintages) / len(valid_vintages), 1) if valid_vintages else 0.0

    # Live / Closed counts
    live_count = sum(1 for tl in tradelines if tl.get("loan_status", "").strip() == "Live")
    closed_count = sum(1 for tl in tradelines if tl.get("loan_status", "").strip() == "Closed")

    # DPD and delinquency
    max_dpd = _compute_max_dpd(tradelines)
    delinquency_flag = max_dpd is not None and max_dpd > 0

    # Overdue
    overdue_amount = sum(_safe_float(tl.get("over_due_amount", "")) for tl in tradelines)

    # Utilization (CC only)
    utilization_ratio = _compute_utilization_ratio(tradelines, loan_type)

    # Forced events
    forced_event_flags = _extract_forced_event_flags(tradelines)

    # On-us / Off-us
    on_us_count = sum(1 for tl in tradelines if tl.get("sector", "").strip() in ON_US_SECTORS)
    off_us_count = loan_count - on_us_count

    # Months since last payment
    months_since_last_payment = _compute_months_since_last_payment(tradelines)

    return BureauLoanFeatureVector(
        loan_type=loan_type,
        secured=secured,
        loan_count=loan_count,
        total_sanctioned_amount=total_sanctioned,
        total_outstanding_amount=total_outstanding,
        avg_vintage_months=avg_vintage,
        months_since_last_payment=months_since_last_payment,
        live_count=live_count,
        closed_count=closed_count,
        delinquency_flag=delinquency_flag,
        max_dpd=max_dpd,
        overdue_amount=overdue_amount,
        utilization_ratio=utilization_ratio,
        forced_event_flags=forced_event_flags,
        on_us_count=on_us_count,
        off_us_count=off_us_count,
    )


def extract_bureau_features(customer_id: int) -> Dict[LoanType, BureauLoanFeatureVector]:
    """Extract bureau feature vectors for a customer.

    Loads raw tradelines from dpd_data.csv, groups by canonical LoanType,
    and computes one BureauLoanFeatureVector per loan type.

    Args:
        customer_id: The CRN (customer reference number) from bureau data.

    Returns:
        Dict mapping each LoanType to its computed feature vector.
        Only loan types present in the customer's data are included.
    """
    all_rows = _load_bureau_data()

    # Filter by customer
    customer_rows = [
        row for row in all_rows if _safe_int(row.get("crn", "")) == customer_id
    ]

    if not customer_rows:
        return {}

    # Group by canonical loan type
    grouped: Dict[LoanType, List[dict]] = defaultdict(list)
    for row in customer_rows:
        raw_type = row.get("loan_type", "").strip()
        canonical = normalize_loan_type(raw_type)
        grouped[canonical].append(row)

    # Build one feature vector per loan type
    vectors: Dict[LoanType, BureauLoanFeatureVector] = {}
    for loan_type, tradelines in grouped.items():
        vectors[loan_type] = _build_feature_vector(loan_type, tradelines)

    return vectors
