import pytest
import pandas as pd

@pytest.fixture
def sample_raw_data() -> pd.DataFrame:
    return pd.DataFrame({
        "id":             [1, 2],
        "gender":         ["Male", "Female"],
        "SeniorCitizen":  [0, 1],
        "Partner":        ["Yes", "No"],
        "Dependents":     ["No", "Yes"],
        "tenure":         [12, 48],
        "PhoneService":   ["Yes", "Yes"],
        "MultipleLines":  ["No", "Yes"],
        "InternetService":["Fiber optic", "DSL"],
        "OnlineSecurity": ["No", "Yes"],
        "OnlineBackup":   ["No", "No"],
        "DeviceProtection":["No", "Yes"],
        "TechSupport":    ["No", "No"],
        "StreamingTV":    ["Yes", "No"],
        "StreamingMovies":["Yes", "No"],
        "Contract":       ["Month-to-month", "Two year"],
        "PaperlessBilling":["Yes", "No"],
        "PaymentMethod":  ["Electronic check", "Bank transfer (automatic)"],
        "MonthlyCharges": [70.35, 20.15],
        "TotalCharges":   [844.2, 967.2],
        "Churn":          ["Yes", "No"],
    })