"""Churn scoring HTTP API. Only trusted model artifacts may be loaded."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .train import FEATURES

app = FastAPI(title="Churn scoring", version="0.1.0")


class Customer(BaseModel):
    tenure_months: float = Field(ge=0, allow_inf_nan=False)
    monthly_spend: float = Field(ge=0, allow_inf_nan=False)
    support_tickets: float = Field(ge=0, allow_inf_nan=False)
    usage_hours: float = Field(ge=0, allow_inf_nan=False)


@lru_cache(maxsize=1)
def artifact() -> dict:
    path = Path(os.getenv("MODEL_PATH", "artifacts/model.joblib"))
    if not path.is_file():
        raise FileNotFoundError(path)
    result = joblib.load(path)
    if tuple(result["features"]) != FEATURES:
        raise ValueError("Model feature schema does not match service")
    return result


@app.get("/health/live")
def live() -> dict:
    return {"status": "alive"}


@app.get("/health/ready")
def ready() -> dict:
    try:
        artifact()
    except (FileNotFoundError, ValueError, KeyError):
        raise HTTPException(503, "Model artifact unavailable")
    return {"status": "ready"}


@app.post("/predict")
def predict(customer: Customer) -> dict:
    try:
        bundle = artifact()
    except (FileNotFoundError, ValueError, KeyError):
        raise HTTPException(503, "Model artifact unavailable")
    vector = [[getattr(customer, name) for name in FEATURES]]
    probability = float(bundle["model"].predict_proba(vector)[0, 1])
    return {"churn_probability": probability, "churn_predicted": probability >= bundle["threshold"],
            "threshold": bundle["threshold"]}
