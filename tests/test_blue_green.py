import copy

import pytest

from apps.deployment.switch_color import check_ready, select_color


def test_both_services_switch_and_preserve_load_balancer():
    docs = [
        {
            "kind": "Service",
            "metadata": {"name": n, "namespace": "production"},
            "spec": {
                "type": "LoadBalancer" if n.endswith("public") else "ClusterIP",
                "ports": [80],
            },
        }
        for n in ("inference", "inference-public")
    ]
    before = copy.deepcopy(docs)
    for color in ("green", "blue"):
        for doc in select_color(docs, color):
            assert doc["spec"]["selector"]["slot"] == color
    for i, doc in enumerate(docs):
        del doc["spec"]["selector"]
        assert doc == before[i]


def test_invalid_color_is_rejected():
    with pytest.raises(ValueError):
        select_color([], "other")


@pytest.mark.parametrize("ready", [0, 1, 2])
def test_readiness_gate(ready):
    d = {
        "metadata": {"generation": 2},
        "spec": {"replicas": 2, "template": {"metadata": {"labels": {"slot": "green"}}}},
        "status": {
            "observedGeneration": 2,
            "updatedReplicas": 2,
            "readyReplicas": ready,
            "availableReplicas": ready,
        },
    }
    if ready == 2:
        check_ready(d, "green")
    else:
        with pytest.raises(RuntimeError):
            check_ready(d, "green")
