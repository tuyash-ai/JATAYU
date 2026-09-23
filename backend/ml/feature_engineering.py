"""Feature engineering used by the uploaded credit-risk model bundle."""

import numpy as np
import pandas as pd


PAYMENT_COLUMNS = ["PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6"]
BILL_COLUMNS = [f"BILL_AMT{i}" for i in range(1, 7)]
PAYMENT_AMOUNT_COLUMNS = [f"PAY_AMT{i}" for i in range(1, 7)]


def transform_raw_input(data: pd.DataFrame) -> pd.DataFrame:
    """Create the features expected by the pipelines stored in the pickle."""
    data = data.copy()

    if "EDUCATION" in data:
        data["EDUCATION"] = data["EDUCATION"].replace({0: 5, 4: 5, 6: 5})
    if "MARRIAGE" in data:
        data["MARRIAGE"] = data["MARRIAGE"].replace({0: 3})

    for column in PAYMENT_COLUMNS:
        data[column] = data[column].replace({-2: 0, -1: 0})
    for column in BILL_COLUMNS:
        data[column] = data[column].abs()

    payment_status = data[PAYMENT_COLUMNS]
    recent_status = data[["PAY_0", "PAY_2", "PAY_3"]]
    older_status = data[["PAY_4", "PAY_5", "PAY_6"]]
    data["max_payment_delay"] = payment_status.max(axis=1)
    data["min_payment_status"] = payment_status.min(axis=1)
    data["avg_payment_delay"] = payment_status.mean(axis=1)
    data["payment_status_std"] = payment_status.std(axis=1).fillna(0)
    data["delay_count"] = (payment_status > 0).sum(axis=1)
    data["severe_delay_count"] = (payment_status >= 2).sum(axis=1)
    data["ever_delinquent"] = (payment_status > 0).any(axis=1).astype(int)
    data["ever_severe_delinquency"] = (payment_status >= 2).any(axis=1).astype(int)
    data["recent_delay_avg"] = recent_status.mean(axis=1)
    data["older_delay_avg"] = older_status.mean(axis=1)
    data["payment_trend"] = data["recent_delay_avg"] - data["older_delay_avg"]
    data["recent_delay_max"] = recent_status.max(axis=1)
    data["recent_delay_count"] = (recent_status > 0).sum(axis=1)

    bills = data[BILL_COLUMNS]
    data["avg_bill_amount"] = bills.mean(axis=1)
    data["max_bill_amount"] = bills.max(axis=1)
    data["bill_std"] = bills.std(axis=1).fillna(0)
    data["recent_bill_avg"] = data[["BILL_AMT1", "BILL_AMT2", "BILL_AMT3"]].mean(axis=1)
    data["older_bill_avg"] = data[["BILL_AMT4", "BILL_AMT5", "BILL_AMT6"]].mean(axis=1)
    data["bill_trend"] = data["recent_bill_avg"] - data["older_bill_avg"]

    safe_limit = data["LIMIT_BAL"].replace(0, np.nan)
    utilization_columns = []
    for index, bill_column in enumerate(BILL_COLUMNS, start=1):
        column = f"utilization_{index}"
        data[column] = (data[bill_column] / safe_limit).replace([np.inf, -np.inf], np.nan).fillna(0)
        utilization_columns.append(column)
    utilization = data[utilization_columns]
    data["avg_utilization"] = utilization.mean(axis=1)
    data["max_utilization"] = utilization.max(axis=1)
    data["utilization_std"] = utilization.std(axis=1).fillna(0)
    data["high_utilization_months"] = (utilization > 0.8).sum(axis=1)
    data["recent_utilization"] = utilization.iloc[:, :3].mean(axis=1)
    data["older_utilization"] = utilization.iloc[:, 3:].mean(axis=1)
    data["utilization_trend"] = data["recent_utilization"] - data["older_utilization"]

    payments = data[PAYMENT_AMOUNT_COLUMNS]
    data["avg_payment_amount"] = payments.mean(axis=1)
    data["max_payment_amount"] = payments.max(axis=1)
    data["payment_amount_std"] = payments.std(axis=1).fillna(0)
    data["zero_payment_months"] = (payments == 0).sum(axis=1)
    ratio_columns = []
    gap_columns = []
    for index, (bill_column, payment_column) in enumerate(
        zip(BILL_COLUMNS, PAYMENT_AMOUNT_COLUMNS), start=1
    ):
        ratio_column = f"payment_ratio_{index}"
        gap_column = f"unpaid_gap_{index}"
        data[ratio_column] = (
            data[payment_column] / data[bill_column].replace(0, np.nan)
        ).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 10)
        data[gap_column] = (data[bill_column] - data[payment_column]).clip(lower=0)
        ratio_columns.append(ratio_column)
        gap_columns.append(gap_column)
    ratios = data[ratio_columns]
    gaps = data[gap_columns]
    data["avg_payment_ratio"] = ratios.mean(axis=1)
    data["recent_payment_ratio"] = ratios.iloc[:, :3].mean(axis=1)
    data["older_payment_ratio"] = ratios.iloc[:, 3:].mean(axis=1)
    data["payment_ratio_trend"] = data["recent_payment_ratio"] - data["older_payment_ratio"]
    data["avg_unpaid_gap"] = gaps.mean(axis=1)
    data["recent_unpaid_gap"] = gaps.iloc[:, :3].mean(axis=1)
    data["older_unpaid_gap"] = gaps.iloc[:, 3:].mean(axis=1)
    data["unpaid_gap_trend"] = data["recent_unpaid_gap"] - data["older_unpaid_gap"]
    data["overall_payment_coverage"] = (
        data[PAYMENT_AMOUNT_COLUMNS].sum(axis=1)
        / data[BILL_COLUMNS].sum(axis=1).replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan).fillna(0).clip(0, 1)

    data["utilization_x_delay"] = data["avg_utilization"] * data["avg_payment_delay"]
    data["delay_x_zero_payment"] = data["delay_count"] * data["zero_payment_months"]
    data["risk_pressure"] = data["max_utilization"] * (1 + data["max_payment_delay"])
    data["age_group"] = pd.cut(
        data["AGE"],
        bins=[0, 25, 35, 45, 55, 120],
        labels=["18-25", "26-35", "36-45", "46-55", "56+"],
        include_lowest=True,
    ).astype(object).fillna("56+")
    return data