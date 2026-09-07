"""Copy only the existing MinIO credentials without writing them to disk or logs."""

import json
import subprocess


def main():
    source = json.loads(
        subprocess.check_output(
            ["kubectl", "get", "secret", "minio-credentials", "-n", "mlops-system", "-o", "json"]
        )
    )
    manifest = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "training-artifacts", "namespace": "mlops-training"},
        "type": "Opaque",
        "data": {key: source["data"][key] for key in ("root-user", "root-password")},
    }
    subprocess.run(
        [
            "kubectl",
            "apply",
            "--server-side",
            "--field-manager=training-secret-bootstrap",
            "-f",
            "-",
        ],
        input=json.dumps(manifest).encode(),
        check=True,
    )


if __name__ == "__main__":
    main()
