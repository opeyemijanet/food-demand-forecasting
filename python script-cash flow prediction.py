"""
cashflow_predictor.py
---------------------
Tech4Dev Capstone - Food SME Management System
Data Science Track

Predicts cashflow risk for small food businesses and generates
actionable recommendations based on transaction history.

Author: Data Science Team
Version: 1.0.0
"""

import pandas as pd
from datetime import datetime


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

# Risk thresholds (days until broke)
CRITICAL_THRESHOLD = 30
WARNING_THRESHOLD  = 60

# Confidence score weights
MIN_DAYS_FOR_FULL_CONFIDENCE   = 90
MID_DAYS_FOR_MEDIUM_CONFIDENCE = 60
MIN_DAYS_FOR_LOW_CONFIDENCE    = 30

MIN_TRANSACTIONS_PER_DAY = 5  # Threshold for density score


# ─────────────────────────────────────────────
# CONFIDENCE SCORE
# ─────────────────────────────────────────────

def calculate_confidence(df: pd.DataFrame) -> float:
    """
    Estimates how reliable the prediction is based on
    how much data is available.

    Parameters:
        df (pd.DataFrame): Transaction history with a 'date' column.

    Returns:
        float: Confidence score between 0.0 and 1.0
    """

    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])

    days_of_data = (df['date'].max() - df['date'].min()).days + 1

    # Score based on how many days of history we have
    if days_of_data >= MIN_DAYS_FOR_FULL_CONFIDENCE:
        days_score = 1.0
    elif days_of_data >= MID_DAYS_FOR_MEDIUM_CONFIDENCE:
        days_score = 0.85
    elif days_of_data >= MIN_DAYS_FOR_LOW_CONFIDENCE:
        days_score = 0.70
    else:
        days_score = 0.50

    # Score based on how frequently transactions are recorded
    transactions_per_day = len(df) / days_of_data
    density_score = 1.0 if transactions_per_day >= MIN_TRANSACTIONS_PER_DAY else 0.70

    return round(days_score * density_score, 2)


# ─────────────────────────────────────────────
# RECOMMENDATION ENGINE
# ─────────────────────────────────────────────

def generate_recommendations(risk_level: str) -> list:
    """
    Returns prioritised action recommendations based on risk level.

    Parameters:
        risk_level (str): One of 'critical', 'warning', 'ok', 'stable'

    Returns:
        list: Ordered list of recommendation dicts with priority and action
    """

    recommendations_map = {
        "critical": [
            {"priority": 1, "action": "Reduce non-essential expenses immediately"},
            {"priority": 2, "action": "Follow up on all pending payments"},
            {"priority": 3, "action": "Consider short-term financing options"},
        ],
        "warning": [
            {"priority": 1, "action": "Review and cut discretionary spending"},
            {"priority": 2, "action": "Speed up collection of receivables"},
            {"priority": 3, "action": "Identify and plan new revenue sources"},
        ],
        "ok": [
            {"priority": 1, "action": "Monitor cashflow on a weekly basis"},
            {"priority": 2, "action": "Build an emergency cash reserve"},
        ],
        "stable": [
            {"priority": 1, "action": "Maintain current financial discipline"},
            {"priority": 2, "action": "Consider reinvesting surplus into inventory"},
        ],
    }

    # Fallback in case an unexpected risk level is passed
    return recommendations_map.get(risk_level, [
        {"priority": 1, "action": "Review your transaction data for accuracy"}
    ])


# ─────────────────────────────────────────────
# MAIN PREDICTION FUNCTION
# ─────────────────────────────────────────────

def predict_cashflow_risk(transactions: list, current_balance: float) -> dict:
    """
    Main prediction function. Analyses a business's transaction history
    to determine cashflow risk and generate recommendations.

    Parameters:
        transactions (list): List of transaction dicts, each containing:
            - date    (str):   Transaction date in 'YYYY-MM-DD' format
            - type    (str):   'income' or 'expense'
            - amount  (float): Transaction amount (always positive)

        current_balance (float): Business's current cash balance in NGN

    Returns:
        dict: Prediction result containing:
            - risk_level        (str):        'stable', 'ok', 'warning', or 'critical'
            - days_until_broke  (int | None): Days until balance reaches zero (None if stable)
            - avg_daily_income  (float):      Average income per transaction
            - avg_daily_expense (float):      Average expense per transaction
            - burn_rate         (float):      Daily net cash burn (expense - income)
            - confidence_score  (float):      Reliability of prediction (0.0 to 1.0)
            - recommendations   (list):       Prioritised action items
            - created_at        (str):        ISO timestamp of when prediction was run

    Raises:
        ValueError: If transactions list is empty or missing required fields
        TypeError:  If current_balance is not a number
    """

    # ── Input Validation ─────────────────────
    if not transactions:
        raise ValueError("Transactions list cannot be empty.")

    if not isinstance(current_balance, (int, float)):
        raise TypeError(f"current_balance must be a number, got {type(current_balance).__name__}.")

    required_fields = {"date", "type", "amount"}
    for i, t in enumerate(transactions):
        missing = required_fields - set(t.keys())
        if missing:
            raise ValueError(f"Transaction at index {i} is missing fields: {missing}")

    # ── Build DataFrame ───────────────────────
    df = pd.DataFrame(transactions)

    valid_types = {"income", "expense"}
    invalid = df[~df["type"].isin(valid_types)]
    if not invalid.empty:
        raise ValueError(
            f"Invalid transaction type(s) found: {invalid['type'].unique().tolist()}. "
            f"Must be one of: {valid_types}"
        )

    # ── Core Calculations ─────────────────────
    confidence_score = calculate_confidence(df)

    income_df  = df[df["type"] == "income"]
    expense_df = df[df["type"] == "expense"]

    avg_income  = income_df["amount"].mean()  if not income_df.empty  else 0.0
    avg_expense = expense_df["amount"].mean() if not expense_df.empty else 0.0

    burn_rate = avg_expense - avg_income

    # ── Risk Classification ───────────────────
    if burn_rate <= 0:
        # Business is making money or breaking even
        risk_level      = "stable"
        days_until_broke = None
    else:
        days_until_broke = int(current_balance / burn_rate)

        if days_until_broke <= CRITICAL_THRESHOLD:
            risk_level = "critical"
        elif days_until_broke <= WARNING_THRESHOLD:
            risk_level = "warning"
        else:
            risk_level = "ok"

    # ── Build Result ──────────────────────────
    return {
        "risk_level":        risk_level,
        "days_until_broke":  days_until_broke,
        "avg_daily_income":  round(avg_income, 2),
        "avg_daily_expense": round(avg_expense, 2),
        "burn_rate":         round(burn_rate, 2),
        "confidence_score":  confidence_score,
        "recommendations":   generate_recommendations(risk_level),
        "created_at":        datetime.now().isoformat(),
    }
