"""Register a toy churn model in a temporary local registry, then call
serve.py (FastAPI) and batch_predict.py (PySpark) against it."""

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("MLFLOW_ENABLE_TELEMETRY", "false")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")
os.environ["PYSPARK_PYTHON"] = sys.executable

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.linear_model import LogisticRegression

FEATURES = ["tenure_months", "monthly_charges", "support_calls"]


def make_customers(n, rng):
    X = pd.DataFrame({
        "tenure_months": rng.integers(1, 72, n).astype(float),
        "monthly_charges": rng.uniform(20, 120, n).round(1),
        "support_calls": rng.poisson(1.5, n).astype(float),
    })
    logit = -0.05 * X.tenure_months + 0.02 * X.monthly_charges + 0.6 * X.support_calls - 1.0
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return X, y


def main():
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    with TemporaryDirectory(prefix="serving-lab-") as d:
        root = Path(d)
        mlflow.set_tracking_uri(f"sqlite:///{root / 'mlflow.db'}")
        os.environ["MLFLOW_TRACKING_URI"] = mlflow.get_tracking_uri()
        mlflow.set_experiment("churn")
        rng = np.random.default_rng(0)
        X, y = make_customers(2000, rng)
        clf = LogisticRegression(max_iter=1000).fit(X, y)
        with mlflow.start_run():
            info = mlflow.sklearn.log_model(
                clf, name="model", pyfunc_predict_fn="predict_proba",
                signature=infer_signature(X, clf.predict_proba(X)),
                input_example=X.head(2), registered_model_name="churn-classifier",
            )
        client = MlflowClient()
        client.set_registered_model_alias(
            "churn-classifier", "champion", info.registered_model_version)

        from fastapi.testclient import TestClient
        import serve
        api = TestClient(serve.app)
        print("GET /healthz ->", api.get("/healthz").json())
        for body in [
            {"tenure_months": 60, "monthly_charges": 30.0, "support_calls": 0},
            {"tenure_months": 3, "monthly_charges": 110.0, "support_calls": 5},
        ]:
            print("POST /predict", body, "->", api.post("/predict", json=body).json())

        import batch_predict
        features, _ = make_customers(5, np.random.default_rng(1))
        features.to_parquet(root / "features.parquet")
        batch_predict.main(str(root / "features.parquet"), str(root / "predictions"))
        out = pd.read_parquet(root / "predictions").sort_values("tenure_months")
        print(out.round(3).to_string(index=False, float_format=lambda v: f"{v:g}"))
        direct = clf.predict_proba(out[FEATURES])[:, 1]
        print("max |spark - sklearn| =", float(np.abs(out.churn_probability - direct).max()))
        from pyspark.sql import SparkSession
        SparkSession.builder.getOrCreate().stop()


if __name__ == "__main__":
    main()
