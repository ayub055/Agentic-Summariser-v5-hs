"""Report summary chain - LLM-based customer review and persona generation.

This module generates:
1. Executive summary (3-4 lines) - financial metrics focus
2. Customer persona (4-5 lines) - lifestyle/behavior focus

Uses LangChain Expression Language (LCEL) with Ollama models.
"""

from dataclasses import asdict
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama

from schemas.customer_report import CustomerReport
from data.loader import get_transactions_df
from utils.helpers import mask_customer_id
from config.settings import EXPLAINER_MODEL


# Original summary prompt (customer-focused, kept for reference)
REVIEW_PROMPT_ORIGINAL = """Based on the following financial data for customer {customer_id}, write a 3-4 line professional financial review.

IMPORTANT RULES:
- Only mention data that is provided below
- Do NOT mention or reference missing sections
- Be factual and concise
- Highlight any red flags or positive signals for lending decision
- Focus on key financial patterns and observations

Financial Data:
{data_summary}

Write a concise, professional review:"""

# Summary prompt template - LENDER POV
# REVIEW_PROMPT = """You are a credit analyst assessing customer {customer_id} for lending purposes. Based on the financial data below, write a 3-4 line executive summary for loan underwriting.

# IMPORTANT RULES:
# - Only mention data that is provided below
# - Do NOT mention or reference missing sections
# - Focus on creditworthiness indicators: income stability, repayment capacity, existing obligations
# - Highlight any red flags or positive signals for lending decision

# Financial Data:
# {data_summary}

# Write a concise credit assessment summary:"""

# Default model for summary generation (from settings)
SUMMARY_MODEL = EXPLAINER_MODEL


def create_summary_chain(model_name: str = SUMMARY_MODEL):
    """
    Create an LCEL chain for generating customer reviews.

    Args:
        model_name: Ollama model to use (default: llama3.1:8b)

    Returns:
        LCEL chain that takes {customer_id, data_summary} and returns str
    """
    prompt = ChatPromptTemplate.from_template(REVIEW_PROMPT_ORIGINAL)
    llm = ChatOllama(model=model_name, temperature=0)

    return prompt | llm | StrOutputParser()


def generate_customer_review(
    report: CustomerReport,
    model_name: str = SUMMARY_MODEL
) -> Optional[str]:
    """
    Generate an LLM-based customer review from populated report sections.

    This function:
    1. Extracts only populated sections from the report
    2. Builds a data summary string
    3. Invokes the LLM chain
    4. Returns the generated review (or None on failure)

    Args:
        report: CustomerReport with populated sections
        model_name: Ollama model to use

    Returns:
        Generated review string, or None if generation fails
    """
    # Build data summary from populated sections only
    sections = _build_data_summary(report)

    if not sections:
        return None

    data_summary = "\n".join(sections)

    try:
        chain = create_summary_chain(model_name)
        review = chain.invoke({
            "customer_id": mask_customer_id(report.meta.customer_id),
            "data_summary": data_summary
        })
        return review.strip() if review else None
    except Exception:
        # Fail-soft: PDF will still be generated without summary
        return None


def _build_data_summary(report: CustomerReport) -> list:
    """
    Build data summary lines from populated report sections.

    Only includes sections that have data - never mentions
    missing sections.

    Args:
        report: CustomerReport to summarize

    Returns:
        List of summary strings for each populated section
    """
    sections = []

    # Category spending
    if report.category_overview:
        top_cats = sorted(
            report.category_overview.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        cats_str = ", ".join(f"{k}: {v:,.0f}" for k, v in top_cats)
        sections.append(f"Top spending categories: {cats_str}")

    # Monthly cashflow
    if report.monthly_cashflow:
        total_inflow = sum(m.get('inflow', 0) for m in report.monthly_cashflow)
        total_outflow = sum(m.get('outflow', 0) for m in report.monthly_cashflow)
        avg_net = (total_inflow - total_outflow) / max(1, len(report.monthly_cashflow))
        sections.append(
            f"Monthly cashflow: Avg net {avg_net:,.0f} INR "
            f"(Total in: {total_inflow:,.0f}, out: {total_outflow:,.0f})"
        )

    # Salary
    if report.salary:
        sections.append(
            f"Salary income: {report.salary.avg_amount:,.0f} INR average "
            f"({report.salary.frequency} transactions)"
        )

    # EMIs
    if report.emis:
        total_emi = sum(e.amount for e in report.emis)
        emi_count = sum(e.frequency for e in report.emis)
        sections.append(f"EMI commitments: {total_emi:,.0f} INR ({emi_count} payments)")

    # Rent
    if report.rent:
        sections.append(
            f"Rent payments: {report.rent.amount:,.0f} INR "
            f"({report.rent.frequency} transactions)"
        )

    # Bills
    if report.bills:
        total_bills = sum(b.avg_amount * b.frequency for b in report.bills)
        sections.append(f"Utility bills: {total_bills:,.0f} INR total")

    # Top merchants
    if report.top_merchants:
        top_merchant = report.top_merchants[0]
        sections.append(
            f"Most frequent merchant: {top_merchant.get('name', 'Unknown')} "
            f"({top_merchant.get('count', 0)} transactions, "
            f"{top_merchant.get('total', 0):,.0f} INR)"
        )

    return sections


# Original persona prompt (general, kept for reference)
PERSONA_PROMPT_ORIGINAL = """Based on the complete financial profile for customer {customer_id}, describe who this customer is in 4-5 lines.

COMPLETE FINANCIAL DATA:
{comprehensive_data}

SAMPLE TRANSACTIONS:
{transaction_sample}

Describe the customer persona focusing on:
- Who they likely are (profession, lifestyle)
- Their financial behavior and discipline
- Spending patterns and priorities
- Overall financial health assessment

Write a 4-5 line customer persona description:"""

# Persona prompt template - LENDER POV (focuses on creditworthiness assessment)
# PERSONA_PROMPT = """You are a credit analyst building a borrower profile for customer {customer_id}. Based on the complete financial data below, write a 4-5 line borrower assessment.

# COMPLETE FINANCIAL DATA:
# {comprehensive_data}

# SAMPLE TRANSACTIONS:
# {transaction_sample}

# Describe the borrower profile focusing on:
# - Income source and stability (salaried/self-employed, regularity)
# - Financial discipline (savings behavior, spending control)
# - Existing debt burden and repayment track record
# - Risk indicators (irregular income, high discretionary spending, overleveraging)
# - Overall creditworthiness assessment (low/medium/high risk)

# Write a 4-5 line borrower profile for lending decision:"""


def create_persona_chain(model_name: str = SUMMARY_MODEL):
    """Create an LCEL chain for generating customer persona."""
    prompt = ChatPromptTemplate.from_template(PERSONA_PROMPT_ORIGINAL)
    llm = ChatOllama(model=model_name, temperature=0.1)
    return prompt | llm | StrOutputParser()


def generate_customer_persona(
    report: CustomerReport,
    model_name: str = SUMMARY_MODEL
) -> Optional[str]:
    """
    Generate an LLM-based customer persona from all available data.

    Uses comprehensive report data plus transaction samples to create
    a 4-5 line persona description of the customer.

    Args:
        report: CustomerReport with populated sections
        model_name: Ollama model to use

    Returns:
        Generated persona string, or None if generation fails
    """
    # Build comprehensive data from report
    comprehensive_data = _build_comprehensive_data(report)

    # Get transaction sample
    transaction_sample = _get_transaction_sample(report.meta.customer_id)

    if not comprehensive_data:
        return None

    try:
        chain = create_persona_chain(model_name)
        persona = chain.invoke({
            "customer_id": mask_customer_id(report.meta.customer_id),
            "comprehensive_data": comprehensive_data,
            "transaction_sample": transaction_sample
        })
        return persona.strip() if persona else None
    except Exception:
        # Fail-soft: report will still be generated without persona
        return None


def _build_comprehensive_data(report: CustomerReport) -> str:
    """
    Build comprehensive data string from all report sections.

    Includes all available data for persona generation.
    """
    lines = []

    # Customer info
    if report.meta.prty_name:
        lines.append(f"Customer Name: {report.meta.prty_name}")
    lines.append(f"Total Transactions: {report.meta.transaction_count}")
    lines.append(f"Analysis Period: {report.meta.analysis_period}")

    # Compute overall financial metrics
    if report.monthly_cashflow:
        total_inflow = sum(m.get('inflow', 0) for m in report.monthly_cashflow)
        total_outflow = sum(m.get('outflow', 0) for m in report.monthly_cashflow)
        savings_rate = (total_inflow - total_outflow) / total_inflow if total_inflow > 0 else 0
        lines.append(f"\nFINANCIAL OVERVIEW:")
        lines.append(f"Total Income: {total_inflow:,.0f} INR")
        lines.append(f"Total Expenses: {total_outflow:,.0f} INR")
        lines.append(f"Net Position: {total_inflow - total_outflow:,.0f} INR")
        lines.append(f"Savings Rate: {savings_rate:.1%}")

    # Salary info
    if report.salary:
        lines.append(f"\nINCOME:")
        lines.append(f"Salary: {report.salary.avg_amount:,.0f} INR average ({report.salary.frequency} payments)")
        if report.salary.narration:
            lines.append(f"Source: {report.salary.narration[:60]}")

    # All spending categories
    if report.category_overview:
        lines.append(f"\nSPENDING BY CATEGORY:")
        sorted_cats = sorted(report.category_overview.items(), key=lambda x: x[1], reverse=True)
        for cat, amount in sorted_cats:
            lines.append(f"  - {cat}: {amount:,.0f} INR")

    # Monthly cashflow trend
    if report.monthly_cashflow:
        lines.append(f"\nMONTHLY CASHFLOW:")
        positive_months = sum(1 for m in report.monthly_cashflow if m.get('net', 0) > 0)
        negative_months = len(report.monthly_cashflow) - positive_months
        lines.append(f"Positive months: {positive_months}, Negative months: {negative_months}")

    # EMI commitments
    if report.emis:
        total_emi = sum(e.amount for e in report.emis)
        lines.append(f"\nEMI COMMITMENTS: {total_emi:,.0f} INR total")

    # Rent
    if report.rent:
        lines.append(f"\nRENT: {report.rent.amount:,.0f} INR ({report.rent.frequency} payments)")

    # Bills
    if report.bills:
        total_bills = sum(b.avg_amount * b.frequency for b in report.bills)
        lines.append(f"\nUTILITY BILLS: {total_bills:,.0f} INR total")

    # Top merchants
    if report.top_merchants:
        lines.append(f"\nTOP MERCHANTS:")
        for m in report.top_merchants[:5]:
            lines.append(f"  - {m.get('name', 'Unknown')[:40]}: {m.get('count', 0)} txns, {m.get('total', 0):,.0f} INR")

    return "\n".join(lines)


def _get_transaction_sample(customer_id: int, limit: int = 20) -> str:
    """
    Get sample of recent transactions for persona context.

    Args:
        customer_id: Customer to get transactions for
        limit: Maximum transactions to include

    Returns:
        Formatted string of transaction samples
    """
    try:
        df = get_transactions_df()
        cust_df = df[df['cust_id'] == customer_id].copy()

        if len(cust_df) == 0:
            return "No transactions available"

        # Sort by date descending to get recent transactions
        cust_df = cust_df.sort_values('tran_date', ascending=False).head(limit)

        lines = []
        for _, row in cust_df.iterrows():
            date = str(row.get('tran_date', 'N/A'))[:10]
            direction = row.get('dr_cr_indctor', 'D')
            amount = row.get('tran_amt_in_ac', 0)
            category = row.get('category_of_txn', 'Unknown')
            narration = str(row.get('tran_partclr', ''))[:50]

            dir_symbol = '+' if direction == 'C' else '-'
            lines.append(f"{date} | {dir_symbol}{amount:,.0f} | {category} | {narration}")

        return "\n".join(lines)
    except Exception:
        return "Transaction sample unavailable"


# =============================================================================
# Bureau Report — LLM Narration
# =============================================================================

BUREAU_REVIEW_PROMPT = """You are a credit analyst writing a brief executive summary of a customer's bureau tradeline portfolio.

IMPORTANT RULES:
- Only reference numbers provided below — do NOT invent or compute any figures
- No arithmetic — just narrate the pre-computed values
- Keep the tone professional and concise (4-6 lines)
- Highlight key risk signals: delinquency, high unsecured exposure, DPD
- Note positive signals: diversified portfolio, mostly closed accounts, low outstanding

Bureau Portfolio Summary:
{data_summary}

Write a concise bureau portfolio review:"""


def _build_bureau_data_summary(executive_inputs) -> str:
    """Format BureauExecutiveSummaryInputs into a text block for the LLM prompt.

    Args:
        executive_inputs: BureauExecutiveSummaryInputs dataclass instance.

    Returns:
        Formatted text summary string.
    """
    data = asdict(executive_inputs) if not isinstance(executive_inputs, dict) else executive_inputs
    product_breakdown = data.pop("product_breakdown", {})

    lines = [
        f"Total Tradelines: {data.get('total_tradelines', 0)}",
        f"Live Tradelines: {data.get('live_tradelines', 0)}",
        f"Closed Tradelines: {data.get('closed_tradelines', 0)}",
        f"Total Exposure (Sanctioned): {data.get('total_exposure', 0):,.0f}",
        f"Total Outstanding: {data.get('total_outstanding', 0):,.0f}",
        f"Unsecured Exposure: {data.get('unsecured_exposure', 0):,.0f}",
        f"Delinquency Flag: {'Yes' if data.get('has_delinquency') else 'No'}",
        f"Max DPD (Days Past Due): {data.get('max_dpd', 'N/A')}",
    ]

    # Product breakdown
    if product_breakdown:
        lines.append("\nProduct-wise Breakdown:")
        for loan_type_key, vec in product_breakdown.items():
            vec_data = asdict(vec) if not isinstance(vec, dict) else vec
            lt_name = loan_type_key if isinstance(loan_type_key, str) else loan_type_key.value
            lines.append(
                f"  - {lt_name}: {vec_data.get('loan_count', 0)} accounts "
                f"(Live: {vec_data.get('live_count', 0)}, Closed: {vec_data.get('closed_count', 0)}), "
                f"Sanctioned: {vec_data.get('total_sanctioned_amount', 0):,.0f}, "
                f"Outstanding: {vec_data.get('total_outstanding_amount', 0):,.0f}"
            )

    return "\n".join(lines)


def generate_bureau_review(
    executive_inputs,
    model_name: str = SUMMARY_MODEL,
) -> Optional[str]:
    """Generate an LLM-based bureau portfolio review from executive summary inputs.

    The LLM receives ONLY pre-computed numbers — no raw tradeline data.

    Args:
        executive_inputs: BureauExecutiveSummaryInputs (dataclass or dict).
        model_name: Ollama model to use.

    Returns:
        Generated narrative string, or None if generation fails.
    """
    data_summary = _build_bureau_data_summary(executive_inputs)

    if not data_summary:
        return None

    try:
        prompt = ChatPromptTemplate.from_template(BUREAU_REVIEW_PROMPT)
        llm = ChatOllama(model=model_name, temperature=0)
        chain = prompt | llm | StrOutputParser()

        review = chain.invoke({"data_summary": data_summary})
        return review.strip() if review else None
    except Exception:
        return None
