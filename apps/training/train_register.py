from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", default="iris-classifier")
    parser.add_argument("--git-sha", default=os.getenv("GITHUB_SHA", "local"))
    parser.add_argument("--dataset-version", default="iris-v1")
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment("final-iris-training")

    data = load_iris()
    x_train, x_test, y_train, y_test = train_test_split(
        data.data, data.target, test_size=0.25, random_state=42, stratify=data.target
    )

    with tempfile.TemporaryDirectory() as tmp:
        model_path = Path(tmp) / "model.joblib"
        model = LogisticRegression(C=2.0, max_iter=500, solver="lbfgs")
        model.fit(x_train, y_train)
        joblib.dump(model, model_path)
        checksum = sha256_file(model_path)

        with mlflow.start_run() as run:
            predictions = model.predict(x_test)
            probabilities = model.predict_proba(x_test)
            accuracy = accuracy_score(y_test, predictions)
            loss = log_loss(y_test, probabilities)

            mlflow.log_param("git_sha", args.git_sha)
            mlflow.log_param("dataset_version", args.dataset_version)
            mlflow.log_param("model_checksum_sha256", checksum)
            mlflow.log_metric("accuracy", accuracy)
            mlflow.log_metric("loss", loss)
            mlflow.log_artifact(str(model_path), artifact_path="model")

            model_info = mlflow.sklearn.log_model(
                model,
                name="model",
                registered_model_name=args.model_name,
            )

            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(args.model_name)[-1]
            client.set_model_version_tag(args.model_name, latest.version, "git_sha", args.git_sha)
            client.set_model_version_tag(args.model_name, latest.version, "dataset_version", args.dataset_version)
            client.set_model_version_tag(args.model_name, latest.version, "checksum_sha256", checksum)
            client.transition_model_version_stage(
                name=args.model_name,
                version=latest.version,
                stage="Staging",
                archive_existing_versions=False,
            )

            print(f"run_id={run.info.run_id}")
            print(f"model_uri={model_info.model_uri}")
            print(f"registered_model_name={args.model_name}")
            print(f"version={latest.version}")
            print(f"stage=Staging")
            print(f"accuracy={accuracy:.4f}")
            print(f"loss={loss:.4f}")
            print(f"checksum_sha256={checksum}")


if __name__ == "__main__":
    main()
