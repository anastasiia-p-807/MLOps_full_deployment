"""Check target readiness and change GitOps routing, never live Services."""

import argparse
import json
import subprocess
from pathlib import Path

import yaml

ROUTING = Path(__file__).resolve().parents[2] / "gitops/manifests/inference/production/routing.yaml"


def select_color(documents, color):
    if color not in {"blue", "green"}:
        raise ValueError("Expected blue or green")
    names = {"inference", "inference-public"}
    if len(documents) != 2 or {d["metadata"]["name"] for d in documents} != names:
        raise ValueError("Expected exactly the two active Services")
    for doc in documents:
        if doc["kind"] != "Service" or doc["metadata"]["namespace"] != "production":
            raise ValueError("Unexpected routing resource")
        doc["spec"]["selector"] = {"app.kubernetes.io/name": "inference", "slot": color}
    return documents


def check_ready(deployment, color):
    desired = deployment["spec"].get("replicas", 1)
    status = deployment.get("status", {})
    if (
        desired < 1
        or status.get("observedGeneration", 0) < deployment["metadata"]["generation"]
        or status.get("updatedReplicas", 0) != desired
        or status.get("readyReplicas", 0) < desired
        or status.get("availableReplicas", 0) < desired
        or deployment["spec"]["template"]["metadata"]["labels"].get("slot") != color
    ):
        raise RuntimeError("Target Deployment is not fully ready")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--color", choices=["blue", "green"], required=True)
    args = parser.parse_args()
    name = "inference" if args.color == "blue" else "inference-green"
    subprocess.run(
        [
            "kubectl",
            "rollout",
            "status",
            f"deployment/{name}",
            "-n",
            "production",
            "--timeout=180s",
        ],
        check=True,
    )
    deployment = json.loads(
        subprocess.check_output(
            ["kubectl", "get", "deployment", name, "-n", "production", "-o", "json"]
        )
    )
    check_ready(deployment, args.color)
    documents = list(yaml.safe_load_all(ROUTING.read_text(encoding="utf-8")))
    updated = select_color(documents, args.color)
    ROUTING.write_text(yaml.safe_dump_all(updated, sort_keys=False), encoding="utf-8")
    print(f"GitOps routing prepared: {args.color}. Commit and push routing.yaml to apply.")


if __name__ == "__main__":
    main()
