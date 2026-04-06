"""
Feature engineering pipeline for the churn model.

Design decisions
----------------
- build_features_base()  → deterministic transformations (safe BEFORE train/test split)
- apply_scaling()        → MinMaxScaler step (must be fit ONLY on training data)
- build_features()       → convenience wrapper that combines both steps

Why the split?
--------------
Fitting MinMaxScaler on the entire dataset before splitting would cause data leakage:
the scaler would learn statistics from the test set and contaminate the training step.
By separating base FE from scaling, train.py can:
  1. Call build_features_base() on the full dataset
  2. Split into train / test
  3. Fit scaler on X_train only
  4. Transform both X_train and X_test
"""
from __future__ import annotations

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from src.config import (
    DROP_COLS,
    ORDINAL_CONTRACT,
    ORDINAL_INTERNET,
    BINARY_YES_NO,
    THREE_VALUE_COLS,
    SERVICE_COLS,
    AUTO_PAYMENT_METHODS,
    SCALE_COLS,
)


# ---------------------------------------------------------------------------
# Step 1 — Deterministic transformations (no fitting required)
# ---------------------------------------------------------------------------

def build_features_base(df: pd.DataFrame, include_target: bool = True) -> pd.DataFrame:
    """Apply all feature engineering steps that do NOT require fitting.

    Safe to run on the full dataset before the train/test split.

    Parameters
    ----------
    df             : Raw input DataFrame. A copy is made internally.
    include_target : Encode Churn (Yes/No → 1/0). Set False for unlabelled data.

    Returns
    -------
    pd.DataFrame with engineered features. Still contains raw `tenure` and
    `MonthlyCharges` columns — call apply_scaling() to add the scaled versions.
    """
    df = df.copy()

    # --- Derived features that need columns which will be dropped -------------
    # IsAutoPayment must be created BEFORE PaymentMethod is dropped
    df["IsAutoPayment"] = df["PaymentMethod"].isin(AUTO_PAYMENT_METHODS).astype(int)
    df = df.drop(columns=["PaymentMethod"])

    # --- Drop irrelevant / high-VIF columns ----------------------------------
    df = df.drop(columns=[c for c in DROP_COLS if c in df.columns])

    # --- Target encoding (optional) ------------------------------------------
    if include_target and "Churn" in df.columns:
        df["Churn"] = (df["Churn"] == "Yes").astype(int)

    # --- Ordinal encodings ---------------------------------------------------
    df["Contract"]        = df["Contract"].map(ORDINAL_CONTRACT)
    df["InternetService"] = df["InternetService"].map(ORDINAL_INTERNET)

    # --- Binary encodings ----------------------------------------------------
    for col in BINARY_YES_NO:
        if col in df.columns:
            df[col] = (df[col] == "Yes").astype(int)

    for col in THREE_VALUE_COLS:
        if col in df.columns:
            df[col] = (df[col] == "Yes").astype(int)

    # --- Aggregate feature: number of additional services contracted ----------
    # Higher bundle = more lock-in = lower churn (confirmed in EDA)
    df["ServicesBundle"] = df[SERVICE_COLS].sum(axis=1)

    # --- Flag: client has any internet service --------------------------------
    # No-internet group has ~1.4% churn — a very clean separating signal
    df["HasInternetService"] = (df["InternetService"] > 0).astype(int)

    # --- Tenure segmentation (non-linear risk curve from EDA) ----------------
    # 0-12m: high risk | 13-24m: medium-high | 25-48m: moderate | 49-72m: loyal
    df["TenureGroup"] = pd.cut(
        df["tenure"],
        bins=[-1, 12, 24, 48, 72],
        labels=[0, 1, 2, 3],
    ).astype(int)

    return df


# ---------------------------------------------------------------------------
# Step 2 — Scaling (requires fitting on training data only)
# ---------------------------------------------------------------------------

def apply_scaling(
    df: pd.DataFrame,
    scaler: MinMaxScaler,
    fit: bool = False,
) -> pd.DataFrame:
    """Scale SCALE_COLS and add `<col>_scaled` companion columns.

    Parameters
    ----------
    df     : DataFrame that already has raw `tenure` and `MonthlyCharges`.
    scaler : MinMaxScaler instance.
    fit    : True  → fit_transform (training data only).
             False → transform only (test / inference data).

    Returns
    -------
    DataFrame with added `tenure_scaled` and `MonthlyCharges_scaled` columns.
    The original raw columns are preserved so callers can inspect or drop them.
    """
    df = df.copy()
    scaled_names = [f"{c}_scaled" for c in SCALE_COLS]

    if fit:
        df[scaled_names] = scaler.fit_transform(df[SCALE_COLS])
    else:
        df[scaled_names] = scaler.transform(df[SCALE_COLS])

    return df


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

def build_features(
    df: pd.DataFrame,
    scaler: MinMaxScaler | None = None,
    fit_scaler: bool = False,
    include_target: bool = True,
) -> tuple[pd.DataFrame, MinMaxScaler]:
    """Full FE pipeline: base transformations + scaling.

    Prefer using build_features_base() + apply_scaling() separately when
    you need a train/test split between the two steps.

    Parameters
    ----------
    df             : Raw input DataFrame.
    scaler         : Pre-fitted MinMaxScaler; create new one if None.
    fit_scaler     : True → fit on this data (training). False → transform only.
    include_target : Encode the Churn column.

    Returns
    -------
    (df_transformed, scaler)
    """
    df = build_features_base(df, include_target=include_target)
    if scaler is None:
        scaler = MinMaxScaler()
    df = apply_scaling(df, scaler=scaler, fit=fit_scaler)
    return df, scaler
