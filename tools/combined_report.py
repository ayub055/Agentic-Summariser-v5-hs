"""Combined report tool - merges banking + bureau into one report.

Generates both individual reports (reusing caches), then renders
a unified combined PDF + HTML document.
"""

import logging
from typing import Tuple

from schemas.customer_report import CustomerReport
from schemas.bureau_report import BureauReport
from pipeline.report_orchestrator import generate_customer_report_pdf
from tools.bureau import generate_bureau_report_pdf

logger = logging.getLogger(__name__)


def generate_combined_report_pdf(
    customer_id: int,
) -> Tuple[CustomerReport, BureauReport, str]:
    """Generate a combined banking + bureau report as one PDF.

    Steps:
        1. Generate customer report (reuses cache if available)
        2. Generate bureau report (reuses cache if available)
        3. Render combined PDF + HTML

    Args:
        customer_id: The customer identifier (CRN).

    Returns:
        Tuple of (CustomerReport, BureauReport, combined_pdf_path).
    """
    # 1. Customer report (cached by report_orchestrator)
    customer_report, _ = generate_customer_report_pdf(customer_id)

    # 2. Bureau report
    bureau_report, _ = generate_bureau_report_pdf(customer_id)

    # 3. Combined rendering
    from pipeline.combined_report_renderer import render_combined_report
    pdf_path = render_combined_report(customer_report, bureau_report)

    return customer_report, bureau_report, pdf_path
