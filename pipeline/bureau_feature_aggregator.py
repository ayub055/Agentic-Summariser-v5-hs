"""Bureau feature aggregation layer.

Computes executive summary inputs from per-loan-type feature vectors.
All logic is deterministic — this produces the structured inputs that
the LLM narration layer will see.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional

from schemas.loan_type import LoanType
from features.bureau_features import BureauLoanFeatureVector


@dataclass
class BureauExecutiveSummaryInputs:
    total_tradelines: int
    live_tradelines: int
    closed_tradelines: int

    product_breakdown: Dict[LoanType, BureauLoanFeatureVector] = field(default_factory=dict)

    total_exposure: float = 0.0
    total_outstanding: float = 0.0
    unsecured_exposure: float = 0.0

    has_delinquency: bool = False
    max_dpd: Optional[int] = None


def aggregate_bureau_features(
    vectors: Dict[LoanType, BureauLoanFeatureVector],
) -> BureauExecutiveSummaryInputs:
    """Aggregate per-loan-type feature vectors into executive summary inputs.

    Args:
        vectors: Dict mapping LoanType to its computed feature vector.

    Returns:
        BureauExecutiveSummaryInputs with portfolio-level aggregations.
    """
    total_tradelines = 0
    live_tradelines = 0
    closed_tradelines = 0
    total_exposure = 0.0
    total_outstanding = 0.0
    unsecured_exposure = 0.0
    has_delinquency = False
    portfolio_max_dpd: Optional[int] = None

    for loan_type, vec in vectors.items():
        total_tradelines += vec.loan_count
        live_tradelines += vec.live_count
        closed_tradelines += vec.closed_count

        total_exposure += vec.total_sanctioned_amount
        total_outstanding += vec.total_outstanding_amount

        # Unsecured exposure = sanctioned amount for non-secured loan types
        if not vec.secured:
            unsecured_exposure += vec.total_sanctioned_amount

        # Delinquency across portfolio
        if vec.delinquency_flag:
            has_delinquency = True

        # Max DPD across portfolio
        if vec.max_dpd is not None:
            if portfolio_max_dpd is None or vec.max_dpd > portfolio_max_dpd:
                portfolio_max_dpd = vec.max_dpd

    return BureauExecutiveSummaryInputs(
        total_tradelines=total_tradelines,
        live_tradelines=live_tradelines,
        closed_tradelines=closed_tradelines,
        product_breakdown=dict(vectors),
        total_exposure=total_exposure,
        total_outstanding=total_outstanding,
        unsecured_exposure=unsecured_exposure,
        has_delinquency=has_delinquency,
        max_dpd=portfolio_max_dpd,
    )
