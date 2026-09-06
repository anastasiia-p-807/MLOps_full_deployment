from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Deque

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field, field_validator

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("inference")

MODEL_PATH = Path(os.getenv("MODEL_PATH", "/app/model/model.joblib"))
MODEL_SHA256 = os.getenv("MODEL_SHA256", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

REQUEST_COUNT = Counter("inference_requests_total", "Inference request count", ["endpoint", "status"])
REQUEST_LATENCY = Histogram("inference_latency_seconds", "Inference latency", ["endpoint"])
PREDICTION_COUNT = Counter("inference_predictions_total", "Prediction count", ["class_id"])

client_windows: dict[str, Deque[float]] = defaultdict(deque)
model = None


class PredictRequest(BaseModel):
    features: list[float] = Field(..., min_length=4, max_length=4)

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: list[float]) -> list[float]:
        if any(item < 0 or item > 20 for item in value):
            raise ValueError("features must be in range 0..20")
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
        raise RuntimeError(f"model file not found: {MODEL_PATH}")
    if MODEL_SHA256:
        actual = sha256_file(MODEL_PATH)
        if actual != MODEL_SHA256:
            raise RuntimeError("model checksum mismatch")
    return joblib.load(MODEL_PATH)


app = FastAPI(title="Final MLOps Inference API")


@app.on_event("startup")
def startup() -> None:
    global model
    model = load_model()
    logger.info(json.dumps({"event": "model_loaded", "path": str(MODEL_PATH)}))


@app.middleware("http")
async def rate_limit_and_metrics(request: Request, call_next):
    started = time.time()
    client = request.client.host if request.client else "unknown"
    now = time.time()
    window = client_windows[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= RATE_LIMIT_PER_MINUTE:
        REQUEST_COUNT.labels(endpoint=request.url.path, status="429").inc()
        return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"})
    window.append(now)

    response = await call_next(request)
    REQUEST_LATENCY.labels(endpoint=request.url.path).observe(time.time() - started)
    REQUEST_COUNT.labels(endpoint=request.url.path, status=str(response.status_code)).inc()
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    try:
        data = np.array([payload.features])
        prediction = int(model.predict(data)[0])
        probabilities = model.predict_proba(data)[0].tolist()
        PREDICTION_COUNT.labels(class_id=str(prediction)).inc()
        logger.info(json.dumps({"event": "prediction", "prediction": prediction}))
        return PredictResponse(
            prediction=prediction,
            probabilities=probabilities,
            model_version=os.getenv("MODEL_VERSION", "unknown"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid input") from exc


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
