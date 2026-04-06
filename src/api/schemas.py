from pydantic import BaseModel, Field
from typing import Literal

_YES_NO = Literal["Yes", "No"]
_YES_NO_NO_SERVICE = Literal["Yes", "No", "No internet service"]
_YES_NO_NO_PHONE = Literal["Yes", "No", "No phone service"]

class CustomerInput(BaseModel):
    SeniorCitizen: int = Field(..., ge=0, le=1)
    Partner: _YES_NO
    Dependents: _YES_NO
    tenure: int = Field(..., ge=0)
    PhoneService: _YES_NO
    MultipleLines: _YES_NO_NO_PHONE
    InternetService: Literal["No", "DSL", "Fiber optic"]
    OnlineSecurity: _YES_NO_NO_SERVICE
    OnlineBackup: _YES_NO_NO_SERVICE
    DeviceProtection: _YES_NO_NO_SERVICE
    TechSupport: _YES_NO_NO_SERVICE
    StreamingTV: _YES_NO_NO_SERVICE
    StreamingMovies: _YES_NO_NO_SERVICE
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: _YES_NO
    PaymentMethod: Literal["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
    MonthlyCharges: float = Field(..., gt=0)

class PredictionOutput(BaseModel):
    churn_probability: float
    churn_label: int
    model_version: str

class JobResponse(BaseModel):
    job_id: str
    status: str