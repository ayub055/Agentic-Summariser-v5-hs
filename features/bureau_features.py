"""Bureau feature vector definition.

Each BureauLoanFeatureVector represents the computed features for one
canonical loan type across all tradelines of that type for a customer.
These are primitive data points — internal, not UI-facing.
"""

from dataclasses import dataclass, field
from typing import Optional, List

from schemas.loan_type import LoanType


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

    forced_event_flags: List[str] = field(default_factory=list)
    on_us_count: int = 0
    off_us_count: int = 0
