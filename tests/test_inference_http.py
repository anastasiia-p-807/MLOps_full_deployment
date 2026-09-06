import pytest
from fastapi.testclient import TestClient

from apps.inference.app import main


@pytest.mark.parametrize(
    "payload",
    [
        {"features": [1, 2]},
        {"features": ["5.1", 3.5, 1.4, 0.2]},
        {"features": [True, 3.5, 1.4, 0.2]},
        {"features": [21, 3.5, 1.4, 0.2]},
        {"features": [5.1, 3.5, 1.4, 0.2], "extra": "not allowed"},
    ],
)
def test_invalid_requests_return_400_without_internal_details(payload):
    main.client_windows.clear()
    response = TestClient(main.app).post("/predict", json=payload)
    assert response.status_code == 400
    assert list(response.json()) == ["detail"]
    assert "Traceback" not in response.text


def test_rate_limit_does_not_count_health_checks(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MINUTE", 2)
    main.client_windows.clear()
    client = TestClient(main.app)
    for _ in range(5):
        assert client.get("/health").status_code == 200
    for _ in range(2):
        assert client.post("/predict", json={"features": []}).status_code == 400
    assert client.post("/predict", json={"features": []}).status_code == 429
    assert client.get("/health").status_code == 200
    main.client_windows.clear()
