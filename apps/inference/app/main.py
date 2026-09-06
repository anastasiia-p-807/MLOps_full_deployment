from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, Field, field_validator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("inference")
MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/model/model.joblib"))
MODEL_SHA256 = os.getenv("MODEL_SHA256", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
REQUEST_COUNT = Counter(
    "inference_requests_total", "Inference request count", ["endpoint", "status"]
)
REQUEST_LATENCY = Histogram("inference_latency_seconds", "Inference latency", ["endpoint"])
PREDICTION_COUNT = Counter("inference_predictions_total", "Prediction count", ["class_id"])
client_windows: dict[str, deque[float]] = defaultdict(deque)
model = None


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: list[float] = Field(..., min_length=4, max_length=4)

    @field_validator("features", mode="before")
    @classmethod
    def validate_features(cls, value):
        if not isinstance(value, list):
            raise ValueError("features must be a list")
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(item)
            or not 0 <= item <= 20
            for item in value
        ):
            raise ValueError("features must contain finite numbers in range 0..20")
        return value


class PredictResponse(BaseModel):
    prediction: int
    probabilities: list[float]
    model_version: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model():
    if not MODEL_PATH.exists():
        raise RuntimeError("model file not found")
    if len(MODEL_SHA256) != 64 or sha256_file(MODEL_PATH) != MODEL_SHA256.lower():
        raise RuntimeError("model checksum missing or mismatched")
    return joblib.load(MODEL_PATH)


@asynccontextmanager
async def lifespan(_app):
    global model
    model = load_model()
    logger.info(json.dumps({"event": "model_loaded", "sha256": MODEL_SHA256}))
    yield


app = FastAPI(title="Final MLOps Inference API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, _exc):
    return JSONResponse(
        status_code=400,
        content={"detail": "features must contain exactly four finite numbers in range 0..20"},
    )


@app.middleware("http")
async def rate_limit_and_metrics(request: Request, call_next):
    if request.url.path != "/predict":
        return await call_next(request)
    started = time.monotonic()
    client = request.client.host if request.client else "unknown"
    # Expire inactive clients; do not let probes consume inference rate limits.
    for key in list(client_windows):
        if not client_windows[key] or started - client_windows[key][-1] >= 60:
            del client_windows[key]
    window = client_windows[client]
    while window and started - window[0] >= 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        REQUEST_COUNT.labels(endpoint="/predict", status="429").inc()
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
    window.append(started)
    response = await call_next(request)
    REQUEST_LATENCY.labels(endpoint="/predict").observe(time.monotonic() - started)
    REQUEST_COUNT.labels(endpoint="/predict", status=str(response.status_code)).inc()
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest):
    try:
        data = np.array([payload.features])
        prediction = int(model.predict(data)[0])
        probabilities = model.predict_proba(data)[0].tolist()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid input") from exc
    version = os.getenv("MODEL_VERSION", "unknown")
    PREDICTION_COUNT.labels(class_id=str(prediction)).inc()
    logger.info(
        json.dumps(
            {
                "event": "prediction",
                "features": payload.features,
                "prediction": prediction,
                "probabilities": probabilities,
                "model_version": version,
            }
        )
    )
    return PredictResponse(
        prediction=prediction, probabilities=probabilities, model_version=version
    )


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
