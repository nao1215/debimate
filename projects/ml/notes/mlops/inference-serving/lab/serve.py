from fastapi import FastAPI
from mlflow import MlflowClient
import mlflow.pyfunc
import pandas as pd
from pydantic import BaseModel

NAME = "churn-classifier"

# 起動時に 1 回だけ、別名 champion が指すバージョンを決めて読み込む
version = MlflowClient().get_model_version_by_alias(NAME, "champion").version
model = mlflow.pyfunc.load_model(f"models:/{NAME}/{version}")

app = FastAPI()


class Customer(BaseModel):
    tenure_months: float
    monthly_charges: float
    support_calls: float


@app.post("/predict")
def predict(customer: Customer):
    X = pd.DataFrame([customer.model_dump()])
    # 登録時に predict_proba を指定したので、[解約しない確率, 解約する確率] が返る
    churn_proba = model.predict(X)[0][1]
    return {"churn_probability": round(float(churn_proba), 3), "model_version": version}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
