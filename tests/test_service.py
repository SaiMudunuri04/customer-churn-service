import csv
from datetime import date, timedelta

import joblib
import pytest
from fastapi.testclient import TestClient

from service import app, train


def dataset(path):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["customer_id", "observed_at", "churned", *train.FEATURES])
        for i in range(120):
            label = int(i % 4 == 0)
            writer.writerow([f"customer-{i}", (date(2025, 1, 1) + timedelta(days=i)).isoformat(),
                             label, i % 30, 50 + i % 20, label * 4, 25 - label * 10])


def test_train_and_serve(tmp_path, monkeypatch):
    path = tmp_path / "churn.csv"
    dataset(path)
    report = train.train(path, tmp_path / "model")
    assert report["test_roc_auc"] > .8
    assert report["test_rows"] == 18
    monkeypatch.setenv("MODEL_PATH", str(tmp_path / "model" / "model.joblib"))
    app.artifact.cache_clear()
    client = TestClient(app.app)
    assert client.get("/health/ready").status_code == 200
    result = client.post("/predict", json={"tenure_months": 12, "monthly_spend": 60,
                                            "support_tickets": 4, "usage_hours": 15})
    assert result.status_code == 200
    assert 0 <= result.json()["churn_probability"] <= 1
    bundle = joblib.load(tmp_path / "model" / "model.joblib")
    assert tuple(bundle["features"]) == train.FEATURES


def test_duplicate_customer_rejected(tmp_path):
    path = tmp_path / "churn.csv"
    dataset(path)
    text = path.read_text().replace("customer-1,", "customer-0,")
    path.write_text(text)
    with pytest.raises(ValueError, match="Duplicate customer"):
        train.load(path)


@pytest.mark.parametrize("before,after,error", [
    ("customer-1,", ",", "customer_id must be nonempty"),
    (",51,", ",-1,", "Invalid target or feature"),
])
def test_invalid_observations_rejected(tmp_path, before, after, error):
    path = tmp_path / "churn.csv"
    dataset(path)
    path.write_text(path.read_text().replace(before, after, 1))
    with pytest.raises(ValueError, match=error):
        train.load(path)
