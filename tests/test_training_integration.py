import hashlib
import os
import subprocess
import sys
from pathlib import Path

import joblib
import pytest
from mlflow.tracking import MlflowClient
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split


def test_training_cli_registers_and_downloads_models(tmp_path):
    script = Path(__file__).resolve().parents[1] / "apps/training/train_register.py"
    tracking_uri = "sqlite:///" + (tmp_path / "mlflow.db").as_posix()
    # Isolate both stores from any configured live MLflow/MinIO environment.
    env = {key: value for key, value in os.environ.items() if not key.startswith("MLFLOW_")}
    env.update(
        MLFLOW_TRACKING_URI=tracking_uri,
        MLFLOW_REGISTRY_URI=tracking_uri,
        MLFLOW_ENABLE_ARTIFACTS_PROGRESS_BAR="false",
    )
    client = MlflowClient(tracking_uri=tracking_uri, registry_uri=tracking_uri)
    client.create_experiment(
        "final-iris-training", artifact_location=(tmp_path / "artifacts").as_uri()
    )
    data = load_iris()
    _, x_test, _, y_test = train_test_split(
        data.data, data.target, test_size=0.25, random_state=42, stratify=data.target
    )
    run_ids = []
    for number in (1, 2):
        git_sha = f"integration-commit-{number}"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--model-name",
                "integration-iris",
                "--git-sha",
                git_sha,
                "--dataset-version",
                "iris-test-v1",
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        output = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        run = client.get_run(output["run_id"])
        run_ids.append(run.info.run_id)
        assert run.info.status == "FINISHED"
        assert run.data.params["git_sha"] == git_sha
        assert run.data.params["dataset_version"] == "iris-test-v1"
        assert run.data.metrics["accuracy"] > 0.9
        assert 0 < run.data.metrics["loss"] < 0.5
        assert output["version"] == str(number)
        assert output["stage"] == "Staging"

        version = client.get_model_version("integration-iris", str(number))
        assert version.run_id == run.info.run_id
        assert version.current_stage == "Staging"
        assert version.tags["git_sha"] == git_sha
        assert version.tags["dataset_version"] == "iris-test-v1"
        download_dir = tmp_path / f"download-{number}"
        download_dir.mkdir()
        artifact = Path(
            client.download_artifacts(run.info.run_id, "model/model.joblib", str(download_dir))
        )
        checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
        assert checksum == run.data.params["model_checksum_sha256"]
        assert checksum == version.tags["checksum_sha256"] == output["checksum_sha256"]
        # Only deserialize the artifact produced by this isolated test process.
        model = joblib.load(artifact)
        assert accuracy_score(y_test, model.predict(x_test)) == pytest.approx(
            run.data.metrics["accuracy"]
        )
        assert log_loss(y_test, model.predict_proba(x_test)) == pytest.approx(
            run.data.metrics["loss"]
        )

    assert len(set(run_ids)) == 2
    assert (
        client.get_model_version("integration-iris", "1").tags["git_sha"] == "integration-commit-1"
    )
