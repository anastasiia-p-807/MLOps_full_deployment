"""Run trusted training sources from one immutable commit of this repository."""

import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


def main():
    sha = os.environ["TRAINING_GIT_SHA"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Expected an immutable Git commit SHA")
    base = "https://raw.githubusercontent.com/anastasiia-p-807/MLOps_full_deployment/"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for filename in ("requirements.txt", "train_register.py"):
            url = f"{base}{sha}/apps/training/{filename}"
            with urllib.request.urlopen(url, timeout=60) as response:
                (root / filename).write_bytes(response.read())
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"],
            cwd=root,
            check=True,
            timeout=600,
        )
        subprocess.run(
            [
                sys.executable,
                "train_register.py",
                "--git-sha",
                sha,
                "--dataset-version",
                os.environ["DATASET_VERSION"],
            ],
            cwd=root,
            check=True,
            timeout=600,
        )


if __name__ == "__main__":
    main()
