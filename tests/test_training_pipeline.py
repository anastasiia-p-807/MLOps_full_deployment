from unittest.mock import Mock

import pytest

from apps.training.run_pipeline import wait_for_execution
from apps.training.validate_input import handler


def test_validate_training_input():
    output = handler({"git_sha": "a" * 40, "dataset_version": "iris-v1"}, None)
    assert output["git_sha"] == "a" * 40
    assert output["dataset_version"] == "iris-v1"
    assert output["job_name"].startswith("iris-train-")


@pytest.mark.parametrize("sha", ["main", "../main", "a" * 39, "x" * 40, None])
def test_reject_mutable_or_invalid_commit(sha):
    with pytest.raises(ValueError):
        handler({"git_sha": sha, "dataset_version": "iris-v1"}, None)


def test_reject_unknown_dataset():
    with pytest.raises(ValueError):
        handler({"git_sha": "a" * 40, "dataset_version": "other"}, None)


def test_wait_requires_success_not_just_started():
    client = Mock()
    client.describe_execution.side_effect = [{"status": "RUNNING"}, {"status": "SUCCEEDED"}]
    assert wait_for_execution(client, "arn", interval=0)["status"] == "SUCCEEDED"
    assert client.describe_execution.call_count == 2


@pytest.mark.parametrize("status", ["FAILED", "TIMED_OUT", "ABORTED"])
def test_failed_training_fails_ci(status):
    client = Mock()
    client.describe_execution.return_value = {"status": status, "error": "training error"}
    with pytest.raises(RuntimeError, match=status):
        wait_for_execution(client, "arn", interval=0)


def test_wait_timeout_stops_execution():
    client = Mock()
    with pytest.raises(TimeoutError):
        wait_for_execution(client, "arn", timeout=0)
    client.stop_execution.assert_called_once()
