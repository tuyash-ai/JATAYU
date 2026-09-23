"""Pydantic schemas for API input validation."""

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    """Current-month values used with an imported UCI customer profile."""

    customer_id: int = Field(..., gt=0, description="The UCI customer ID.")
    BILL_AMT1: float = Field(..., ge=0, description="Bill amount must be 0 or greater.")
    PAY_AMT1: float = Field(..., ge=0, description="Payment amount must be 0 or greater.")
