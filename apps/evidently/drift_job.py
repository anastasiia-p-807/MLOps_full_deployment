from prometheus_client import CollectorRegistry, Gauge, push_to_gateway


def main() -> None:
    registry = CollectorRegistry()
    drift_score = Gauge("model_drift_score", "Demo drift score from Evidently job", registry=registry)
    drift_score.set(0.03)
    push_to_gateway("pushgateway.monitoring.svc.cluster.local:9091", job="evidently_drift", registry=registry)


if __name__ == "__main__":
    main()
