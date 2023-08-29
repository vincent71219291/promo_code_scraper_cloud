import datetime
from typing import Iterable

import pandas as pd
from google.cloud import bigquery, exceptions

COL_NAMES = {
    "discount": "Réduction (%)",
    "description": "Description",
    "code": "Code",
    "expiration_date": "Date d'expiration",
    "days_before_exp": "Jours avant expiration",
}


def select_new_codes(
    current_codes: pd.DataFrame,
    previous_codes: pd.DataFrame,
    discount_col: str = "discount",
    threshold: int = 0,
) -> pd.DataFrame:
    df = pd.merge(
        left=current_codes, right=previous_codes, how="left", indicator=True
    )
    df = df.loc[
        (df["_merge"] == "left_only") & (df[discount_col] >= threshold)
    ].drop(columns="_merge")

    return df


def days_from_today(date: datetime.date):
    return (date - datetime.date.today()).days


def add_days_before_exp(
    data: pd.DataFrame,
    exp_date_col: str = "expiration_date",
) -> pd.DataFrame:
    data = data.copy()
    data["days_before_exp"] = data[exp_date_col].map(days_from_today)
    return data


def format_codes(data: pd.DataFrame) -> pd.DataFrame:
    return add_days_before_exp(data).rename(columns=COL_NAMES)
