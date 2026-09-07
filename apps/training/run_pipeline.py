"""Start the training state machine and propagate its final status to CI."""

import argparse
import json
import os
import re
import time
import uuid

import boto3


def wait_for_execution(client, arn, timeout=1900, interval=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = client.describe_execution(executionArn=arn)
        status = result["status"]
        if status == "SUCCEEDED":
            print(result.get("output", "{}"))
            return result
        if status != "RUNNING":
            raise RuntimeError(
                f"Training {status}: {result.get('error', '')} {result.get('cause', '')}"
            )
        time.sleep(interval)
    client.stop_execution(executionArn=arn, error="ClientTimeout", cause="CI wait limit exceeded")
    raise TimeoutError("Training execution exceeded the CI wait limit")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-sha", required=True)
    parser.add_argument("--dataset-version", default="iris-v1", choices=["iris-v1"])
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.git_sha):
        parser.error("--git-sha must be a full lowercase Git commit SHA")
    session = boto3.Session(region_name=os.getenv("AWS_REGION", "eu-central-1"))
    client = session.client("stepfunctions")
    account = session.client("sts").get_caller_identity()["Account"]
    arn = f"arn:aws:states:{session.region_name}:{account}:stateMachine:final-mlops-training"
    client.describe_state_machine(stateMachineArn=arn)
    result = client.start_execution(
        stateMachineArn=arn,
        name=f"train-{args.git_sha[:12]}-{uuid.uuid4().hex[:12]}",
        input=json.dumps(
            {
                "source": "github-actions",
                "git_sha": args.git_sha,
                "dataset_version": args.dataset_version,
            }
        ),
    )
    execution = result["executionArn"]
    print(f"execution_arn={execution}", flush=True)
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    try:
        wait_for_execution(client, execution)
    except Exception:
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as summary:
                summary.write(f"Training failed or could not be verified: `{execution}`\n")
        raise
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(f"Training SUCCEEDED: `{execution}`\n\nCommit: `{args.git_sha}`\n")


if __name__ == "__main__":
    main()
