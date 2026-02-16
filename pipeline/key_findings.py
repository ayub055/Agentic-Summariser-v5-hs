"""Key findings extractor - deterministic bullet-point generation.

Scans all bureau features (executive inputs, per-loan-type vectors,
tradeline features) and produces structured key findings with inferences.
Each finding is severity-tagged for rendering.

NO LLM calls - purely threshold-based deterministic logic.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from schemas.loan_type import LoanType, get_loan_type_display_name
from features.bureau_features import BureauLoanFeatureVector
from features.tradeline_features import TradelineFeatures
from pipeline.bureau_feature_aggregator import BureauExecutiveSummaryInputs
from utils.helpers import format_inr


@dataclass
class KeyFinding:
    """A single key finding with inference."""
    category: str       # Feature group (e.g., "Portfolio", "DPD & Delinquency")
    finding: str        # Factual observation
    inference: str      # Risk/positive interpretation
    severity: str       # "high_risk", "moderate_risk", "concern", "positive", "neutral"


def extract_key_findings(
    executive_inputs: BureauExecutiveSummaryInputs,
    feature_vectors: Dict[LoanType, BureauLoanFeatureVector],
    tradeline_features: Optional[TradelineFeatures] = None,
) -> List[KeyFinding]:
    """Extract key findings from all available bureau data.

    Deterministic: each finding is produced by threshold checks on
    pre-computed features. Returns findings ordered by severity
    (high_risk first, positive last).

    Args:
        executive_inputs: Portfolio-level aggregated data.
        feature_vectors: Per-loan-type feature vectors.
        tradeline_features: Optional customer-level behavioral features.

    Returns:
        List of KeyFinding objects, severity-ordered.
    """
    findings: List[KeyFinding] = []

    # --- Portfolio-level findings ---
    findings.extend(_portfolio_findings(executive_inputs, feature_vectors))

    # --- Per-loan-type findings ---
    findings.extend(_loan_type_findings(feature_vectors))

    # --- Tradeline behavioral findings ---
    if tradeline_features is not None:
        findings.extend(_tradeline_findings(tradeline_features))

    # --- Composite / interaction findings ---
    if tradeline_features is not None:
        findings.extend(_composite_findings(executive_inputs, tradeline_features))

    # Sort: high_risk > moderate_risk > concern > neutral > positive
    severity_order = {"high_risk": 0, "moderate_risk": 1, "concern": 2, "neutral": 3, "positive": 4}
    findings.sort(key=lambda f: severity_order.get(f.severity, 3))

    return findings


def _portfolio_findings(
    ei: BureauExecutiveSummaryInputs,
    vectors: Dict[LoanType, BureauLoanFeatureVector],
) -> List[KeyFinding]:
    """Extract findings from portfolio-level data."""
    findings = []

    # Delinquency flag
    if ei.has_delinquency:
        dpd_str = f" (Max DPD: {ei.max_dpd})" if ei.max_dpd is not None else ""
        if ei.max_dpd is not None and ei.max_dpd > 90:
            findings.append(KeyFinding(
                category="Delinquency",
                finding=f"Active delinquency detected with Max DPD of {ei.max_dpd} days",
                inference="Severe delinquency indicates significant repayment stress; loan may be classified as NPA",
                severity="high_risk",
            ))
        elif ei.max_dpd is not None and ei.max_dpd > 30:
            findings.append(KeyFinding(
                category="Delinquency",
                finding=f"Active delinquency detected with Max DPD of {ei.max_dpd} days",
                inference="Significant past-due status suggests repayment difficulty; close monitoring required",
                severity="moderate_risk",
            ))
        elif ei.max_dpd is not None and ei.max_dpd > 0:
            findings.append(KeyFinding(
                category="Delinquency",
                finding=f"Minor delinquency detected with Max DPD of {ei.max_dpd} days",
                inference="Early-stage past-due status; may reflect temporary cash flow mismatch",
                severity="concern",
            ))
    else:
        findings.append(KeyFinding(
            category="Delinquency",
            finding="No delinquency detected across the portfolio",
            inference="Clean delinquency record is a positive indicator for repayment discipline",
            severity="positive",
        ))

    # Unsecured exposure proportion
    if ei.total_exposure > 0:
        unsecured_pct = (ei.unsecured_exposure / ei.total_exposure) * 100
        if unsecured_pct > 80:
            findings.append(KeyFinding(
                category="Portfolio",
                finding=f"Unsecured exposure is {unsecured_pct:.0f}% of total (INR {format_inr(ei.unsecured_exposure)} of INR {format_inr(ei.total_exposure)})",
                inference="Heavily skewed towards unsecured lending; higher risk in absence of collateral",
                severity="moderate_risk",
            ))
        elif unsecured_pct > 50:
            findings.append(KeyFinding(
                category="Portfolio",
                finding=f"Unsecured exposure is {unsecured_pct:.0f}% of total (INR {format_inr(ei.unsecured_exposure)} of INR {format_inr(ei.total_exposure)})",
                inference="Majority unsecured portfolio; monitor for over-leveraging on unsecured products",
                severity="concern",
            ))

    # Outstanding as % of sanctioned
    if ei.total_exposure > 0:
        outstanding_pct = (ei.total_outstanding / ei.total_exposure) * 100
        if outstanding_pct > 80:
            findings.append(KeyFinding(
                category="Portfolio",
                finding=f"Outstanding balance is {outstanding_pct:.0f}% of total sanctioned exposure",
                inference="Most sanctioned amount still outstanding; limited repayment progress on existing obligations",
                severity="concern",
            ))

    # Product diversity
    product_count = len(vectors)
    if product_count >= 4:
        product_names = ", ".join(get_loan_type_display_name(lt) for lt in vectors)
        findings.append(KeyFinding(
            category="Portfolio",
            finding=f"Portfolio spans {product_count} loan products ({product_names})",
            inference="Diversified credit portfolio indicates established borrowing history across products",
            severity="neutral",
        ))

    return findings


def _loan_type_findings(
    vectors: Dict[LoanType, BureauLoanFeatureVector],
) -> List[KeyFinding]:
    """Extract findings from per-loan-type feature vectors."""
    findings = []

    for loan_type, vec in vectors.items():
        lt_name = get_loan_type_display_name(loan_type)

        # CC utilization
        if loan_type == LoanType.CC and vec.utilization_ratio is not None:
            util = vec.utilization_ratio
            if util > 75:
                findings.append(KeyFinding(
                    category="Utilization",
                    finding=f"Credit card utilization at {util:.0f}%",
                    inference="Over-utilization of credit card limits signals high credit dependency and potential cash flow stress",
                    severity="high_risk",
                ))
            elif util > 50:
                findings.append(KeyFinding(
                    category="Utilization",
                    finding=f"Credit card utilization at {util:.0f}%",
                    inference="Elevated utilization; approaching high-risk threshold for revolving credit",
                    severity="moderate_risk",
                ))
            elif util <= 30:
                findings.append(KeyFinding(
                    category="Utilization",
                    finding=f"Credit card utilization at {util:.0f}%",
                    inference="Healthy utilization indicates disciplined credit card usage",
                    severity="positive",
                ))

        # Per-type delinquency
        if vec.delinquency_flag and vec.max_dpd is not None and vec.max_dpd > 0:
            if vec.max_dpd > 90:
                findings.append(KeyFinding(
                    category="Delinquency",
                    finding=f"{lt_name}: Delinquent with Max DPD of {vec.max_dpd} days",
                    inference=f"Severe delinquency on {lt_name} account; may indicate deep financial distress",
                    severity="high_risk",
                ))
            elif vec.max_dpd > 30:
                findings.append(KeyFinding(
                    category="Delinquency",
                    finding=f"{lt_name}: Delinquent with Max DPD of {vec.max_dpd} days",
                    inference=f"Significant past-due on {lt_name}; repayment discipline is compromised",
                    severity="moderate_risk",
                ))

        # Overdue amount
        if vec.overdue_amount > 0:
            findings.append(KeyFinding(
                category="Outstanding",
                finding=f"{lt_name}: Overdue amount of INR {format_inr(vec.overdue_amount)}",
                inference=f"Active overdue balance on {lt_name} indicates unresolved payment obligation",
                severity="concern",
            ))

        # Forced events (write-off, settlement, etc.)
        if vec.forced_event_flags:
            events = ", ".join(vec.forced_event_flags)
            findings.append(KeyFinding(
                category="Adverse Events",
                finding=f"{lt_name}: Forced events detected — {events}",
                inference=f"Adverse credit events on {lt_name} are strong negative signals for creditworthiness",
                severity="high_risk",
            ))

    return findings


def _tradeline_findings(tf: TradelineFeatures) -> List[KeyFinding]:
    """Extract findings from pre-computed tradeline features."""
    findings = []

    # --- Loan Activity ---
    if tf.new_trades_6m_pl is not None:
        if tf.new_trades_6m_pl >= 3:
            findings.append(KeyFinding(
                category="Loan Activity",
                finding=f"{tf.new_trades_6m_pl} new personal loan trades opened in last 6 months",
                inference="Rapid PL acquisition suggests urgent credit need or loan stacking behavior",
                severity="high_risk",
            ))
        elif tf.new_trades_6m_pl >= 2:
            findings.append(KeyFinding(
                category="Loan Activity",
                finding=f"{tf.new_trades_6m_pl} new personal loan trades opened in last 6 months",
                inference="Multiple recent PL acquisitions; monitor for emerging over-leverage",
                severity="moderate_risk",
            ))

    if tf.months_since_last_trade_pl is not None and tf.months_since_last_trade_pl < 2:
        findings.append(KeyFinding(
            category="Loan Activity",
            finding=f"Last PL trade opened {tf.months_since_last_trade_pl:.1f} months ago",
            inference="Very recent PL activity indicates active credit seeking",
            severity="concern",
        ))

    # --- DPD & Delinquency ---
    for field_name, label in [
        ("max_dpd_6m_cc", "Credit Card (6M)"),
        ("max_dpd_6m_pl", "Personal Loan (6M)"),
        ("max_dpd_9m_cc", "Credit Card (9M)"),
    ]:
        val = getattr(tf, field_name, None)
        if val is not None and val > 0:
            if val > 90:
                findings.append(KeyFinding(
                    category="DPD & Delinquency",
                    finding=f"Max DPD for {label}: {val} days",
                    inference=f"Severe delinquency on {label} — strong negative indicator",
                    severity="high_risk",
                ))
            elif val > 30:
                findings.append(KeyFinding(
                    category="DPD & Delinquency",
                    finding=f"Max DPD for {label}: {val} days",
                    inference=f"Significant past-due on {label}; repayment under stress",
                    severity="moderate_risk",
                ))
            else:
                findings.append(KeyFinding(
                    category="DPD & Delinquency",
                    finding=f"Max DPD for {label}: {val} days",
                    inference=f"Minor past-due on {label}; may be a temporary delay",
                    severity="concern",
                ))

    # Clean DPD check (all zero)
    dpd_fields = [tf.max_dpd_6m_cc, tf.max_dpd_6m_pl, tf.max_dpd_9m_cc]
    if all(v is not None and v == 0 for v in dpd_fields):
        findings.append(KeyFinding(
            category="DPD & Delinquency",
            finding="Zero DPD across all products in recent 6-9 month windows",
            inference="Clean recent payment record demonstrates consistent repayment discipline",
            severity="positive",
        ))

    # --- Payment Behavior ---
    if tf.pct_missed_payments_18m is not None:
        if tf.pct_missed_payments_18m > 10:
            findings.append(KeyFinding(
                category="Payment Behavior",
                finding=f"{tf.pct_missed_payments_18m:.1f}% missed payments in last 18 months",
                inference="Frequent missed payments indicate chronic repayment stress",
                severity="high_risk",
            ))
        elif tf.pct_missed_payments_18m > 0:
            findings.append(KeyFinding(
                category="Payment Behavior",
                finding=f"{tf.pct_missed_payments_18m:.1f}% missed payments in last 18 months",
                inference="Some missed payments detected; not habitual but warrants attention",
                severity="concern",
            ))
        else:
            findings.append(KeyFinding(
                category="Payment Behavior",
                finding="No missed payments in last 18 months",
                inference="Perfect payment track record over 18 months is a strong positive",
                severity="positive",
            ))

    if tf.ratio_good_closed_pl is not None:
        if tf.ratio_good_closed_pl >= 0.8:
            findings.append(KeyFinding(
                category="Payment Behavior",
                finding=f"Good closure ratio for PL loans: {tf.ratio_good_closed_pl:.0%}",
                inference="Strong track record of closing personal loans in good standing",
                severity="positive",
            ))
        elif tf.ratio_good_closed_pl < 0.5:
            findings.append(KeyFinding(
                category="Payment Behavior",
                finding=f"Good closure ratio for PL loans: {tf.ratio_good_closed_pl:.0%}",
                inference="Poor PL closure history — majority of closed PLs had issues",
                severity="high_risk",
            ))
        elif tf.ratio_good_closed_pl < 0.7:
            findings.append(KeyFinding(
                category="Payment Behavior",
                finding=f"Good closure ratio for PL loans: {tf.ratio_good_closed_pl:.0%}",
                inference="Below-average PL closure quality; some loans closed with problems",
                severity="concern",
            ))

    # --- Utilization ---
    if tf.cc_balance_utilization_pct is not None:
        if tf.cc_balance_utilization_pct > 75:
            findings.append(KeyFinding(
                category="Utilization",
                finding=f"CC balance utilization: {tf.cc_balance_utilization_pct:.1f}%",
                inference="Over-utilized credit card limits indicate high revolving credit dependency",
                severity="high_risk",
            ))
        elif tf.cc_balance_utilization_pct > 50:
            findings.append(KeyFinding(
                category="Utilization",
                finding=f"CC balance utilization: {tf.cc_balance_utilization_pct:.1f}%",
                inference="Elevated CC utilization; approaching over-utilization threshold",
                severity="moderate_risk",
            ))
        elif tf.cc_balance_utilization_pct <= 30:
            findings.append(KeyFinding(
                category="Utilization",
                finding=f"CC balance utilization: {tf.cc_balance_utilization_pct:.1f}%",
                inference="Healthy CC utilization reflects controlled credit card usage",
                severity="positive",
            ))

    if tf.pl_balance_remaining_pct is not None:
        if tf.pl_balance_remaining_pct > 80:
            findings.append(KeyFinding(
                category="Utilization",
                finding=f"PL balance remaining: {tf.pl_balance_remaining_pct:.1f}%",
                inference="Most PL sanctioned amount still outstanding; limited principal repayment progress",
                severity="high_risk",
            ))
        elif tf.pl_balance_remaining_pct <= 30:
            findings.append(KeyFinding(
                category="Utilization",
                finding=f"PL balance remaining: {tf.pl_balance_remaining_pct:.1f}%",
                inference="Significant PL principal already repaid; good repayment progress",
                severity="positive",
            ))

    # --- Enquiry Behavior ---
    if tf.unsecured_enquiries_12m is not None:
        if tf.unsecured_enquiries_12m > 15:
            findings.append(KeyFinding(
                category="Enquiry Behavior",
                finding=f"{tf.unsecured_enquiries_12m} unsecured enquiries in last 12 months",
                inference="Very high enquiry pressure suggests desperate credit seeking or multiple rejections",
                severity="high_risk",
            ))
        elif tf.unsecured_enquiries_12m > 10:
            findings.append(KeyFinding(
                category="Enquiry Behavior",
                finding=f"{tf.unsecured_enquiries_12m} unsecured enquiries in last 12 months",
                inference="Elevated enquiry activity; may indicate difficulty securing credit",
                severity="moderate_risk",
            ))
        elif tf.unsecured_enquiries_12m <= 3:
            findings.append(KeyFinding(
                category="Enquiry Behavior",
                finding=f"{tf.unsecured_enquiries_12m} unsecured enquiries in last 12 months",
                inference="Minimal enquiry activity indicates stable credit position",
                severity="positive",
            ))

    if tf.trade_to_enquiry_ratio_uns_24m is not None:
        if tf.trade_to_enquiry_ratio_uns_24m < 20:
            findings.append(KeyFinding(
                category="Enquiry Behavior",
                finding=f"Trade-to-enquiry ratio (unsecured, 24M): {tf.trade_to_enquiry_ratio_uns_24m:.1f}%",
                inference="Low conversion from enquiries to actual loans suggests possible rejections by lenders",
                severity="concern",
            ))
        elif tf.trade_to_enquiry_ratio_uns_24m > 50:
            findings.append(KeyFinding(
                category="Enquiry Behavior",
                finding=f"Trade-to-enquiry ratio (unsecured, 24M): {tf.trade_to_enquiry_ratio_uns_24m:.1f}%",
                inference="High conversion rate indicates strong acceptance by lenders",
                severity="positive",
            ))

    # --- Loan Acquisition Velocity ---
    if tf.interpurchase_time_12m_plbl is not None:
        if tf.interpurchase_time_12m_plbl < 1:
            findings.append(KeyFinding(
                category="Loan Velocity",
                finding=f"Avg time between PL/BL acquisitions (12M): {tf.interpurchase_time_12m_plbl:.1f} months",
                inference="Rapid loan stacking — acquiring unsecured loans faster than monthly; high risk of over-leverage",
                severity="high_risk",
            ))
        elif tf.interpurchase_time_12m_plbl < 2:
            findings.append(KeyFinding(
                category="Loan Velocity",
                finding=f"Avg time between PL/BL acquisitions (12M): {tf.interpurchase_time_12m_plbl:.1f} months",
                inference="Frequent loan acquisitions; borrower is actively accumulating unsecured debt",
                severity="concern",
            ))
        elif tf.interpurchase_time_12m_plbl >= 6:
            findings.append(KeyFinding(
                category="Loan Velocity",
                finding=f"Avg time between PL/BL acquisitions (12M): {tf.interpurchase_time_12m_plbl:.1f} months",
                inference="Measured pace of loan acquisitions indicates no urgency or stacking behavior",
                severity="positive",
            ))

    return findings


def _composite_findings(
    ei: BureauExecutiveSummaryInputs,
    tf: TradelineFeatures,
) -> List[KeyFinding]:
    """Extract findings from feature interactions (multi-feature signals)."""
    findings = []

    enquiries = tf.unsecured_enquiries_12m
    new_pl_6m = tf.new_trades_6m_pl
    ipt_plbl = tf.interpurchase_time_12m_plbl

    # Credit hungry + loan stacking
    if enquiries is not None and enquiries > 10 and new_pl_6m is not None and new_pl_6m >= 2:
        findings.append(KeyFinding(
            category="Composite Signal",
            finding=f"High enquiry volume ({enquiries} in 12M) combined with {new_pl_6m} new PL trades in 6M",
            inference="Credit hungry behavior with active loan stacking — elevated risk of debt spiral",
            severity="high_risk",
        ))

    # Rapid stacking with low interpurchase time
    if ipt_plbl is not None and ipt_plbl < 2 and new_pl_6m is not None and new_pl_6m >= 2:
        findings.append(KeyFinding(
            category="Composite Signal",
            finding=f"Avg {ipt_plbl:.1f} months between PL/BL with {new_pl_6m} new trades in 6M",
            inference="Rapid PL stacking pattern — borrower is accumulating unsecured debt at an accelerating pace",
            severity="high_risk",
        ))

    # High utilization + high outstanding
    cc_util = tf.cc_balance_utilization_pct
    pl_bal = tf.pl_balance_remaining_pct
    if cc_util is not None and cc_util > 50 and pl_bal is not None and pl_bal > 50:
        findings.append(KeyFinding(
            category="Composite Signal",
            finding=f"CC utilization at {cc_util:.1f}% and PL balance remaining at {pl_bal:.1f}%",
            inference="Elevated leverage across both revolving and term products; limited debt servicing headroom",
            severity="moderate_risk",
        ))

    # High enquiries + low conversion
    trade_ratio = tf.trade_to_enquiry_ratio_uns_24m
    if enquiries is not None and enquiries > 10 and trade_ratio is not None and trade_ratio < 30:
        findings.append(KeyFinding(
            category="Composite Signal",
            finding=f"High enquiries ({enquiries}) but only {trade_ratio:.1f}% trade-to-enquiry conversion",
            inference="Low conversion rate despite high enquiry volume suggests multiple lender rejections",
            severity="moderate_risk",
        ))

    # Clean profile composite
    dpd_clean = all(
        getattr(tf, f, None) is not None and getattr(tf, f) == 0
        for f in ["max_dpd_6m_cc", "max_dpd_6m_pl", "max_dpd_9m_cc"]
    )
    missed_clean = tf.pct_missed_payments_18m is not None and tf.pct_missed_payments_18m == 0
    good_ratio = tf.ratio_good_closed_pl
    if dpd_clean and missed_clean and good_ratio is not None and good_ratio >= 0.8:
        findings.append(KeyFinding(
            category="Composite Signal",
            finding=f"Zero DPD, no missed payments, and {good_ratio:.0%} good PL closure ratio",
            inference="Exemplary repayment profile — strong candidate from a credit discipline standpoint",
            severity="positive",
        ))

    return findings


def findings_to_dicts(findings: List[KeyFinding]) -> List[Dict]:
    """Convert KeyFinding list to list of dicts for serialization."""
    return [asdict(f) for f in findings]
