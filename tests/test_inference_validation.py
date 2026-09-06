from pydantic import ValidationError

from apps.inference.app.main import PredictRequest


def test_predict_request_accepts_four_features():
    payload = PredictRequest(features=[5.1, 3.5, 1.4, 0.2])
    assert len(payload.features) == 4


def test_predict_request_rejects_wrong_feature_count():
    try:
        PredictRequest(features=[1.0, 2.0])
    except ValidationError:
        return
    raise AssertionError("ValidationError was not raised")
