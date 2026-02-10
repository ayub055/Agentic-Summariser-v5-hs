"""
Data loading and management module.
Handles all data access in one place.
"""

import pandas as pd
from typing import Optional
import os

# Module-level cache for the dataframe
_transactions_df: Optional[pd.DataFrame] = None


def get_data_path() -> str:
    """Get the path to the transactions CSV file."""
    # Get the directory where this file is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate to the data folder (../../data from archive_refactored/data/)
    data_path = os.path.join(current_dir,  "ayub_txns.csv")
    return os.path.normpath(data_path)


def load_transactions(force_reload: bool = False) -> pd.DataFrame:
    """
    Load transaction data from CSV.

    Args:
        force_reload: If True, reload from disk even if cached

    Returns:
        DataFrame with transaction data
    """
    global _transactions_df

    if _transactions_df is None or force_reload:
        data_path = get_data_path()
        _transactions_df = pd.read_csv(data_path)
        print(f"Loaded {len(_transactions_df)} transactions from {data_path}")

    return _transactions_df


def get_transactions_df() -> pd.DataFrame:
    """
    Get the transactions DataFrame (loads if not already loaded).

    This is the main function tools should use to access data.
    """
    return load_transactions()


def get_data_summary() -> str:
    """
    Generate a summary of the transaction data.

    Returns:
        String with data statistics
    """
    df = get_transactions_df()

    total_credits = df[df['dr_cr_indctor'] == 'C']['tran_amt_in_ac'].sum()
    total_debits = df[df['dr_cr_indctor'] == 'D']['tran_amt_in_ac'].sum()

    summary = f"""
Transaction Data Summary
========================
Total Records: {len(df)}
Unique Customers: {df['cust_id'].nunique()}
Date Range: {df['tran_date'].min()} to {df['tran_date'].max()}

Transaction Types: {df['tran_type'].unique().tolist()}
Categories: {df['category_of_txn'].unique().tolist()}

Total Credits (Income): ${total_credits:,.2f}
Total Debits (Expenses): ${total_debits:,.2f}
"""
    return summary
