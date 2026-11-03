"""Run a local registry experiment; remove the temporary DB/artifacts on exit."""
import os
os.environ.setdefault("MLFLOW_ENABLE_TELEMETRY", "false")
os.environ.setdefault("MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR", "false")

from pathlib import Path
from tempfile import TemporaryDirectory

import mlflow
import mlflow.sklearn
import numpy as np
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.linear_model import LinearRegression


def main():
    with TemporaryDirectory(prefix="registry-lab-") as directory:
        root = Path(directory)
        mlflow.set_tracking_uri(f"sqlite:///{root / 'registry.db'}")
        mlflow.set_registry_uri(mlflow.get_tracking_uri())
        experiment = mlflow.create_experiment(
            "alias-and-reload", artifact_location=(root / "artifacts").as_uri()
        )
        client = MlflowClient()
        name = "toy-linear"
        train_x = np.array([[0.0], [1.0], [2.0], [3.0]])
        test_x = np.array([[4.0]])
        versions = []
        for slope in (1.0, 2.0):
            model = LinearRegression().fit(train_x, slope * train_x[:, 0])
            with mlflow.start_run(experiment_id=experiment):
                mlflow.log_param("slope", slope)
                mlflow.set_tag("dataset", f"toy-y-{slope:g}x")
                info = mlflow.sklearn.log_model(
                    model, name="linear-model",
                    signature=infer_signature(train_x, model.predict(train_x)),
                    input_example=train_x[:1],
                    pip_requirements=["scikit-learn==1.7.2", "numpy==2.5.4",
                                      "cloudpickle==3.1.2"],
                )
                version = str(mlflow.register_model(info.model_uri, name).version)
                versions.append(version)
                client.set_model_version_tag(name, version, "purpose", "alias-reload-demo")
        first, second = versions
        assert (first, second) == ("1", "2")
        client.set_registered_model_alias(name, "champion", first)
        resident = mlflow.pyfunc.load_model(f"models:/{name}@champion")

        def report(label, model, expected_version, expected_prediction):
            version = str(client.get_model_version_by_alias(name, "champion").version)
            prediction = float(model.predict(test_x)[0])
            assert version == expected_version
            assert np.isclose(prediction, expected_prediction)
            print(f"{label}: alias=v{version}, prediction={prediction:.1f}")

        report("initial load", resident, first, 4.0)
        client.set_registered_model_alias(name, "champion", second)
        report("alias changed only", resident, second, 4.0)
        resident = mlflow.pyfunc.load_model(f"models:/{name}@champion")
        report("after reload", resident, second, 8.0)
        client.set_registered_model_alias(name, "champion", first)
        report("rollback alias only", resident, first, 8.0)
        resident = mlflow.pyfunc.load_model(f"models:/{name}@champion")
        report("after rollback reload", resident, first, 4.0)
        mlflow.end_run()


if __name__ == "__main__":
    main()
