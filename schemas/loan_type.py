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
    # Personal loans
    "Personal Loan": LoanType.PL,
    "Short Term Personal Loan": LoanType.PL,
    "Microfinance - Personal Loan": LoanType.PL,
    "P2P Personal Loan": LoanType.PL,
    "Loan to Professional": LoanType.PL,

    # Credit cards
    "Credit Card": LoanType.CC,
    "Secured Credit Card": LoanType.CC,
    "Corporate Credit Card": LoanType.CC,
    "Loan on Credit Card": LoanType.CC,
    "Fleet Card": LoanType.CC,
    "Kisan Credit Card": LoanType.CC,

    # Home / housing loans
    "Housing Loan": LoanType.HL,
    "Microfinance - Housing Loan": LoanType.HL,
    "Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS": LoanType.HL,

    # Auto / vehicle loans
    "Auto Loan (Personal)": LoanType.AL,
    "Used Car Loan": LoanType.AL,
    "Commercial Vehicle Loan": LoanType.AL,
    "Construction Equipment Loan": LoanType.AL,
    "Tractor Loan": LoanType.AL,
    "P2P Auto Loan": LoanType.AL,

    # Business loans
    "Business Loan - General": LoanType.BL,
    "Business Loan - Secured": LoanType.BL,
    "Business Loan - Unsecured": LoanType.BL,
    "Business Loan - Priority Sector - Agriculture": LoanType.BL,
    "Business Loan - Priority Sector - Others": LoanType.BL,
    "Business Loan - Priority Sector - Small Business": LoanType.BL,
    "Business Loan Against Bank Deposits": LoanType.BL,
    "Business Non-Funded Credit Facility - General": LoanType.BL,
    "Business Non-Funded Credit Facility - Priority Sector-Others": LoanType.BL,
    "Business Non-Funded Credit Facility - Priority Sector - Agriculture": LoanType.BL,
    "Business Non-Funded Credit Facility - Priority Sector - Small Business": LoanType.BL,
    "Business Loan - General": LoanType.BL,
    "Business Loan - Unsecured": LoanType.BL,
    "Non-Funded Credit Facility": LoanType.BL,
    "Microfinance - Business Loan": LoanType.BL,
    "Mudra Loans - Shishu / Kishor / Tarun": LoanType.BL,
    "GECL Loan Secured": LoanType.BL,
    "GECL Loan Unsecured": LoanType.BL,

    # Loan against property / securities / deposits
    "Loan_against_securities": LoanType.LAP,
    "Loan Against Shares/Securities": LoanType.LAP,
    "Loan Against Bank Deposits": LoanType.LAP,
    "Property Loan": LoanType.LAP,

    # Gold loans
    "Gold Loan": LoanType.GL,
    "Priority Sector - Gold Loan": LoanType.GL,

    # Two-wheeler
    "Two-wheeler Loan": LoanType.TWL,

    # Consumer durables
    "Consumer Loan": LoanType.CD,

    # Education
    "Education Loan": LoanType.OTHER,
    "P2P Education Loan": LoanType.OTHER,

    # Other
    "Seller Financing": LoanType.OTHER,
    "Temporary Overdraft": LoanType.OTHER,
    "Overdraft": LoanType.OTHER,
    "Prime Minister Jaan Dhan Yojana - Overdraft": LoanType.OTHER,
    "Leasing": LoanType.OTHER,
    "Microfinance - Other": LoanType.OTHER,
    "Other": LoanType.OTHER,
}

# Raw loan type names that are secured (sec_flag=1).
# Checked at raw level because some canonical types (BL, CC)
# have both secured and unsecured variants.
SECURED_LOAN_TYPES: Set[str] = {
    "Gold Loan",
    "Priority Sector - Gold Loan",
    "Two-wheeler Loan",
    "Tractor Loan",
    "Loan Against Bank Deposits",
    "Loan_against_securities",
    "Loan Against Shares/Securities",
    "Secured Credit Card",
    "Pradhan Mantri Awas Yojana - Credit Link Subsidy Scheme MAY CLSS",
    "GECL Loan Secured",
    "Microfinance - Housing Loan",
    "Leasing",
    "P2P Auto Loan",
    "Housing Loan",
    "Property Loan",
    "Auto Loan (Personal)",
    "Used Car Loan",
    "Commercial Vehicle Loan",
    "Construction Equipment Loan",
    "Business Loan - Secured",
    "Business Loan Against Bank Deposits",
}

# Kotak sectors that count as "on-us" tradelines
ON_US_SECTORS: Set[str] = {"KOTAK BANK", "KOTAK PRIME"}


def normalize_loan_type(raw_loan_type: str) -> LoanType:
    """Normalize a raw loan_type string from dpd_data.csv to canonical LoanType."""
    return LOAN_TYPE_NORMALIZATION_MAP.get(raw_loan_type, LoanType.OTHER)


def is_secured(raw_loan_type: str) -> bool:
    """Check if a raw loan type is secured (collateral-backed)."""
    return raw_loan_type in SECURED_LOAN_TYPES
