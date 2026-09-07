import re
import uuid


def handler(event, context):
    sha = event.get("git_sha", "")
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("git_sha must be a full lowercase Git commit SHA")
    if event.get("dataset_version") != "iris-v1":
        raise ValueError("Only dataset_version=iris-v1 is supported")
    return {
        "git_sha": sha,
        "dataset_version": "iris-v1",
        "job_name": "iris-train-" + uuid.uuid4().hex,
    }
