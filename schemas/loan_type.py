"""Canonical loan type taxonomy for bureau tradeline classification.

Single source of truth for loan types used across all bureau logic.
Derived from dpd_data.csv loan_type values.
"""

from enum import Enum
from typing import Dict, Set


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


# Maps raw dpd_data.csv `loan_type` values to canonical LoanType
LOAN_TYPE_NORMALIZATION_MAP: Dict[str, LoanType] = {
    "Personal Loan": LoanType.PL,
    "Short Term Personal Loan": LoanType.PL,
    "Credit Card": LoanType.CC,
    "Home Loan": LoanType.HL,
    "Auto Loan": LoanType.AL,
    "Used Car Loan": LoanType.AL,
    "Business Loan - General": LoanType.BL,
    "Business Loan - Priority Sector - Agriculture": LoanType.BL,
    "GECL Loan Secured": LoanType.BL,
    "GECL Loan Unsecured": LoanType.BL,
    "Loan_against_securities": LoanType.LAP,
    "Property Loan": LoanType.LAP,
    "Gold Loan": LoanType.GL,
    "Priority Sector - Gold Loan": LoanType.GL,
    "Two-wheeler Loan": LoanType.TWL,
    "Consumer Loan": LoanType.CD,
    "Other": LoanType.OTHER,
}

# Loan types backed by collateral
SECURED_LOAN_TYPES: Set[LoanType] = {
    LoanType.HL,
    LoanType.AL,
    LoanType.LAP,
    LoanType.GL,
    LoanType.TWL,
}

# Kotak sectors that count as "on-us" tradelines
ON_US_SECTORS: Set[str] = {"KOTAK BANK", "KOTAK PRIME"}


def normalize_loan_type(raw_loan_type: str) -> LoanType:
    """Normalize a raw loan_type string from dpd_data.csv to canonical LoanType."""
    return LOAN_TYPE_NORMALIZATION_MAP.get(raw_loan_type, LoanType.OTHER)


def is_secured(loan_type: LoanType) -> bool:
    """Check if a loan type is secured (collateral-backed)."""
    return loan_type in SECURED_LOAN_TYPES
