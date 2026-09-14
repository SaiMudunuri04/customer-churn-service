"""Train a leakage-aware scikit-learn churn model locally or in SageMaker."""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ("tenure_months", "monthly_spend", "support_tickets", "usage_hours")


def load(path: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"customer_id", "observed_at", "churned", *FEATURES}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing columns: {sorted(required - set(reader.fieldnames or []))}")
        rows = list(reader)
    if len(rows) < 40:
        raise ValueError("At least 40 rows are required for train, validation and test splits")
    ids = [row["customer_id"].strip() for row in rows]
    if any(not customer_id for customer_id in ids):
        raise ValueError("customer_id must be nonempty")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate customer_id; resolve entity leakage before training")
    try:
        rows.sort(key=lambda row: datetime.fromisoformat(row["observed_at"]))
        x = np.asarray([[float(row[column]) if row[column] else np.nan for column in FEATURES]
                        for row in rows], dtype=np.float64)
        y = np.asarray([int(row["churned"]) for row in rows], dtype=np.int64)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid timestamp or numeric value") from exc
    observed = x[~np.isnan(x)]
    if not set(y).issubset({0, 1}) or not np.isfinite(observed).all() or (observed < 0).any():
        raise ValueError("Invalid target or feature")
    return x, y, [row["observed_at"] for row in rows]


def train(path: Path, output: Path) -> dict:
    x, y, dates = load(path)
    first, second = int(len(y) * .7), int(len(y) * .85)
    train_x, val_x, test_x = x[:first], x[first:second], x[second:]
    train_y, val_y, test_y = y[:first], y[first:second], y[second:]
    if any(len(set(part)) < 2 for part in (train_y, val_y, test_y)):
        raise ValueError("Every chronological split must contain both target classes")
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                          StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
    model.fit(train_x, train_y)
    val_scores = model.predict_proba(val_x)[:, 1]
    thresholds = np.arange(.15, .86, .05)
    threshold = float(max(thresholds, key=lambda t: f1_score(val_y, val_scores >= t)))
    scores = model.predict_proba(test_x)[:, 1]
    predicted = scores >= threshold
    report = {
        "train_rows": len(train_y), "validation_rows": len(val_y), "test_rows": len(test_y),
        "test_started_at": dates[second], "threshold_selected_on": "validation",
        "threshold": threshold, "test_roc_auc": float(roc_auc_score(test_y, scores)),
        "test_f1": float(f1_score(test_y, predicted)),
        "test_precision": float(precision_score(test_y, predicted, zero_division=0)),
        "test_recall": float(recall_score(test_y, predicted, zero_division=0)),
        "test_brier": float(brier_score_loss(test_y, scores)),
    }
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "threshold": threshold}, output / "model.joblib")
    (output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-file", type=Path, default=Path(os.getenv("SM_CHANNEL_TRAIN", "data")) / "churn.csv")
    parser.add_argument("--output", type=Path, default=Path(os.getenv("SM_MODEL_DIR", "artifacts")))
    args = parser.parse_args()
    print(json.dumps(train(args.train_file, args.output), indent=2))


if __name__ == "__main__":
    main()
