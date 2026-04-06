"""
Centralized configuration for the churn prediction project.

All constants, paths, and hyperparameters live here.
Importing from this module is the single source of truth for the entire codebase.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR    = Path(__file__).resolve().parent.parent
DATA_DIR    = ROOT_DIR / "data"
MODELS_DIR  = ROOT_DIR / "models"
RESULTS_DIR = ROOT_DIR / "notebooks" / "results"

RAW_TRAIN_PATH = DATA_DIR / "train.csv"
RAW_TEST_PATH  = DATA_DIR / "test.csv"
MODEL_PATH     = MODELS_DIR / "gradient_boosting_ciclo0.pkl"

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
SEED      = 42
TEST_SIZE = 0.20

# ---------------------------------------------------------------------------
# Feature Engineering — column lists
# ---------------------------------------------------------------------------

# Columns dropped before modelling (no predictive value or high VIF)
DROP_COLS = ["id", "gender", "TotalCharges"]

# Ordinal mappings (risk order confirmed by EDA)
ORDINAL_CONTRACT = {"Month-to-month": 0, "One year": 1, "Two year": 2}
ORDINAL_INTERNET = {"No": 0, "DSL": 1, "Fiber optic": 2}

# Simple Yes/No binary columns
BINARY_YES_NO = ["Partner", "Dependents", "PhoneService", "PaperlessBilling"]

# Three-value columns (Yes / No / No internet service) → Yes=1, rest=0
THREE_VALUE_COLS = [
    "MultipleLines", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
]

# Columns aggregated into ServicesBundle
SERVICE_COLS = [
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies",
]

# Payment methods classified as automatic (lower churn)
AUTO_PAYMENT_METHODS = [
    "Bank transfer (automatic)",
    "Credit card (automatic)",
]

# Columns to scale with MinMaxScaler (raw names, before scaling)
SCALE_COLS = ["tenure", "MonthlyCharges"]

# ---------------------------------------------------------------------------
# Model input — final feature column order (must be stable across train/serve)
# ---------------------------------------------------------------------------
FEATURE_COLS = [
    "SeniorCitizen", "Partner", "Dependents",
    "tenure_scaled", "PhoneService", "MultipleLines",
    "InternetService", "HasInternetService", "ServicesBundle",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies",
    "Contract", "PaperlessBilling", "IsAutoPayment",
    "MonthlyCharges_scaled", "TenureGroup",
]

TARGET_COL = "Churn"
CICLO = "ciclo0"  # For experiment tracking and artifact versioning
QUEUE_NAME = "churn_requests"
JOBS_RESULTS_DIR = ROOT_DIR / "results"
