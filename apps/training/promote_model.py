from __future__ import annotations

import argparse
import json
import logging
import os

import mlflow

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("model_registry_audit")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--stage", choices=["Staging", "Production", "Archived"], required=True)
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    client = mlflow.tracking.MlflowClient()
    client.transition_model_version_stage(
        name=args.model_name,
        version=args.version,
        stage=args.stage,
        archive_existing_versions=args.stage == "Production",
    )

    logger.info(json.dumps({
        "event": "model_stage_transition",
        "model_name": args.model_name,
        "version": args.version,
        "stage": args.stage,
        "actor": os.getenv("USER", "unknown"),
    }))


if __name__ == "__main__":
    main()
