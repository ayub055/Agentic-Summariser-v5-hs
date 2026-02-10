"""
Utility functions used across the project.
"""


def format_currency(amount: float) -> str:
    """Format a number as currency."""
    return f"${amount:,.2f}"


def print_header(title: str, char: str = "=", width: int = 60):
    """Print a formatted header."""
    print(char * width)
    print(title.center(width))
    print(char * width)


def print_section(title: str, char: str = "-", width: int = 40):
    """Print a section divider."""
    print(f"\n{title}")
    print(char * width)


def mask_customer_id(customer_id: int | str) -> str:
    """
    Mask customer ID to show only last 4 digits.

    Args:
        customer_id: Customer identifier (int or str)

    Returns:
        Masked string showing only last 4 digits (e.g., "###4898")

    Examples:
        >>> mask_customer_id(9449274898)
        '###4898'
        >>> mask_customer_id("1234567890")
        '###7890'
        >>> mask_customer_id(123)
        '###123'
    """
    id_str = str(customer_id)
    if len(id_str) <= 4:
        return f"###{id_str}"
    return f"###{id_str[-4:]}"
